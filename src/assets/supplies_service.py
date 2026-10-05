# SPDX-License-Identifier: Apache-2.0
"""Domain service extracted from thick API handlers."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models as _models
from api_common import row_to_dict
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from models import (
    DamageTicket,
    Linen,
    LinenSnapshot,
    RestockItem,
    RestockOrder,
    StockMovement,
    Supply,
    SupplyAlert,
    SupplyCategory,
    SupplyInsight,
    SupplyRequisition,
)

# models.__all__ 未覆盖全部 ORM（如 SupplyAlert）；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})


def build_supplies_board(db: Session, hotel_id: int, line: Optional[str] = None):
    """⑧ 物资双线聚合：布草周转 / 易耗库存·补货·领用·报损。"""
    LINEN_CATS = {"布草"}
    cats = {c.id: c.name for c in db.query(SupplyCategory).filter_by(hotel_id=hotel_id).all()}
    supplies = db.query(Supply).filter_by(hotel_id=hotel_id).all()
    supply_rows = []
    low_count = 0
    for s in supplies:
        cname = cats.get(s.category_id, "") or ""
        if line == "linen" and cname not in LINEN_CATS:
            continue
        if line == "amenity" and cname in LINEN_CATS:
            continue
        cur = float(s.current_stock or 0)
        safe = float(s.safety_stock or 0)
        low = cur < safe
        if low:
            low_count += 1
        supply_rows.append(
            {
                **row_to_dict(s),
                "category": cname,
                "low": low,
                "gap": round(max(0, safe - cur), 2),
            }
        )
    supply_rows.sort(key=lambda x: (not x["low"], x["name"]))

    # 分类汇总 KPI
    cat_kpi = {}
    for r in supply_rows:
        cname = r["category"] or "其他"
        bucket = cat_kpi.setdefault(cname, {"name": cname, "sku": 0, "stock": 0.0, "low": 0})
        bucket["sku"] += 1
        bucket["stock"] += float(r["current_stock"] or 0)
        if r["low"]:
            bucket["low"] += 1

    alerts_q = db.query(SupplyAlert).filter_by(hotel_id=hotel_id, status="open")
    if line in ("linen", "amenity"):
        alerts_q = alerts_q.filter_by(line=line)
    alerts = [row_to_dict(a) for a in alerts_q.order_by(SupplyAlert.id.desc()).limit(30).all()]

    # 楼层消耗热力（由 alerts 推导）
    floors_map = {}
    for a in alerts:
        if a.get("line") != "amenity" and line == "linen":
            continue
        fl = a.get("floor") or "其他"
        floors_map.setdefault(fl, {"name": fl, "rooms": []})
        sev = a.get("severity") or "mid"
        status = "abnormal" if sev == "high" else ("high" if sev == "mid" else "normal")
        floors_map[fl]["rooms"].append(
            {
                "id": a.get("id"),
                "room": a.get("room_no") or "-",
                "status": status,
                "note": a.get("message") or a.get("supply_name") or "",
                "supply_name": a.get("supply_name"),
                "severity": sev,
                "line": a.get("line"),
            }
        )
    floors = list(floors_map.values())

    snap_date = db.query(func.max(LinenSnapshot.biz_date)).filter_by(hotel_id=hotel_id).scalar()
    snaps = []
    if snap_date:
        snaps = [row_to_dict(s) for s in db.query(LinenSnapshot).filter_by(hotel_id=hotel_id, biz_date=snap_date).all()]
    linen_trend = []
    for (d,) in (
        db.query(LinenSnapshot.biz_date)
        .filter_by(hotel_id=hotel_id)
        .distinct()
        .order_by(LinenSnapshot.biz_date.desc())
        .limit(7)
        .all()
    ):
        rows = db.query(LinenSnapshot).filter_by(hotel_id=hotel_id, biz_date=d).all()
        linen_trend.append(
            {
                "biz_date": d.isoformat(),
                "pending_wash": sum(int(r.pending_wash or 0) for r in rows),
                "in_wash": sum(int(r.in_wash or 0) for r in rows),
                "in_storage": sum(int(r.in_storage or 0) for r in rows),
            }
        )
    linen_trend.reverse()

    # 实物 linen 寿命统计
    linen_items = db.query(Linen).filter_by(hotel_id=hotel_id).all()
    stage_count = {}
    for ln in linen_items:
        st = ln.lifecycle_stage or "良好"
        stage_count[st] = stage_count.get(st, 0) + 1
    high_wash = sorted(
        [row_to_dict(x) for x in linen_items if int(x.wash_count or 0) >= 60],
        key=lambda x: -int(x.get("wash_count") or 0),
    )[:12]
    linen_avg_wash = 0.0
    if linen_items:
        linen_avg_wash = round(
            sum(int(x.wash_count or 0) for x in linen_items) / max(1, len(linen_items)),
            1,
        )

    orders = db.query(RestockOrder).filter_by(hotel_id=hotel_id).order_by(RestockOrder.id.desc()).limit(10).all()
    amenity_ids = {r["id"] for r in supply_rows} if line in ("linen", "amenity") else None
    restock = []
    for o in orders:
        items = [row_to_dict(i) for i in db.query(RestockItem).filter_by(order_id=o.id).all()]
        if amenity_ids is not None:
            items = [
                i
                for i in items
                if (i.get("supply_id") in amenity_ids)
                or (
                    not i.get("supply_id")
                    and line == "amenity"
                    and not any(k in (i.get("name") or "") for k in ("床单", "浴巾", "枕套", "面巾", "布草"))
                )
            ]
        if line in ("linen", "amenity") and not items:
            continue
        restock.append({**row_to_dict(o), "items": items})

    reqs = [
        row_to_dict(r)
        for r in db.query(SupplyRequisition)
        .filter_by(hotel_id=hotel_id)
        .order_by(SupplyRequisition.id.desc())
        .limit(80)
        .all()
    ]

    damages_q = db.query(DamageTicket).filter_by(hotel_id=hotel_id)
    if line in ("linen", "amenity"):
        damages_q = damages_q.filter_by(line=line)
    damages = [row_to_dict(d) for d in damages_q.order_by(DamageTicket.id.desc()).limit(40).all()]
    fee_open = sum(float(d["fee"] or 0) for d in damages if d.get("status") in ("open", "repairing"))
    fee_done = sum(float(d["fee"] or 0) for d in damages if d.get("status") in ("replaced", "scrapped", "closed"))

    insights_q = db.query(SupplyInsight).filter_by(hotel_id=hotel_id)
    if line in ("linen", "amenity"):
        insights_q = insights_q.filter_by(line=line)
    insights = [row_to_dict(i) for i in insights_q.order_by(SupplyInsight.id.desc()).limit(40).all()]

    movements = [
        row_to_dict(m)
        for m in db.query(StockMovement).filter_by(hotel_id=hotel_id).order_by(StockMovement.id.desc()).limit(60).all()
    ]

    # —— RCA 盘点异常 / 人效（看板聚合字段，页面已下线）——
    physical_value = round(
        sum(float(s.get("current_stock") or 0) * float(s.get("unit_cost") or 0) for s in supply_rows), 2
    )
    book_value = round(
        sum(
            max(float(s.get("current_stock") or 0), float(s.get("safety_stock") or 0)) * float(s.get("unit_cost") or 0)
            for s in supply_rows
        ),
        2,
    )
    # 报损待核、盘亏洞察计入账面侧差异
    loss_impact = sum(
        float(i.get("impact_amount") or 0)
        for i in insights
        if i.get("category") in ("loss", "rca") and i.get("status") == "open"
    )
    book_value = round(max(book_value, physical_value + fee_open + loss_impact * 0.35), 2)
    gap_value = round(max(0.0, book_value - physical_value), 2)
    diff_rate = round((gap_value / book_value * 100) if book_value > 0 else 0.0, 1)

    # 上期差异：用布草快照报废占比作代理
    prev_diff_rate = None
    if linen_trend and len(linen_trend) >= 2:
        early = linen_trend[0]
        tot = (
            float(early.get("pending_wash") or 0)
            + float(early.get("in_wash") or 0)
            + float(early.get("in_storage") or 0)
        )
        # 用趋势波动估算
        last = linen_trend[-1]
        tot_last = (
            float(last.get("pending_wash") or 0) + float(last.get("in_wash") or 0) + float(last.get("in_storage") or 0)
        )
        if tot_last > 0:
            prev_diff_rate = round(max(0.5, min(8.0, abs(tot - tot_last) / tot_last * 100 * 0.15)), 1)
    if prev_diff_rate is None:
        prev_diff_rate = round(max(0.5, diff_rate - 0.8), 1)
    rate_delta = round(diff_rate - prev_diff_rate, 1)

    # 三类根因：未登记领用 / 盘点错误 / 自然损耗报废
    unreg = 0
    for a in alerts:
        msg = f"{a.get('message') or ''}{a.get('supply_name') or ''}"
        if any(k in msg for k in ("领用", "消耗", "加换", "多领", "补货频繁", "偏高")):
            unreg += 2 if a.get("severity") == "high" else 1
    unreg += sum(1 for i in insights if i.get("category") == "rca")
    unreg += sum(1 for m in movements if m.get("movement_type") == "issue")

    count_err = sum(1 for m in movements if m.get("movement_type") == "adjust")
    count_err += sum(
        1
        for i in insights
        if i.get("category") == "loss" and "盘" in f"{i.get('title') or ''}{i.get('recommendation') or ''}"
    )
    count_err += low_count

    natural = sum(1 for d in damages if d.get("status") in ("open", "repairing", "scrapped", "replaced", "closed"))
    natural += sum(1 for m in movements if m.get("movement_type") == "damage")
    natural += sum(1 for i in insights if i.get("category") in ("loss", "replace"))

    cause_total = max(1, unreg + count_err + natural)
    causes = [
        {
            "key": "unregistered",
            "label": "未登记领用",
            "sub": "未记录用量",
            "pct": round(unreg / cause_total * 100),
            "cls": "bg-tertiary-container",
        },
        {
            "key": "count_error",
            "label": "盘点错误",
            "sub": "计数错误",
            "pct": round(count_err / cause_total * 100),
            "cls": "bg-secondary-container",
        },
        {
            "key": "natural_loss",
            "label": "自然损耗/报废",
            "sub": "损坏",
            "pct": round(natural / cause_total * 100),
            "cls": "bg-error-container",
        },
    ]
    # 修正四舍五入使合计 100
    drift = 100 - sum(c["pct"] for c in causes)
    if causes:
        causes[0]["pct"] = max(0, causes[0]["pct"] + drift)
    for c in causes:
        c["h"] = max(36, int(round(c["pct"] / 100 * 160)))

    # 员工人效：按领用人聚合
    by_req: dict = {}
    for r in reqs:
        if r.get("status") == "void":
            continue
        name = (r.get("requester") or "未具名").strip() or "未具名"
        bucket = by_req.setdefault(name, {"name": name, "dept": r.get("dept") or "客房部", "qty": 0.0, "n": 0})
        bucket["qty"] += float(r.get("qty") or 0)
        bucket["n"] += 1
        if r.get("dept"):
            bucket["dept"] = r.get("dept")
    staff_rows = []
    if by_req:
        avg_qty = sum(v["qty"] for v in by_req.values()) / max(1, len(by_req))
        for v in by_req.values():
            if avg_qty > 0:
                dev_pct = round((v["qty"] / avg_qty - 1) * 100)
            else:
                dev_pct = 0
            score = int(max(55, min(99, round(98 - max(0, dev_pct) * 1.6 + min(0, abs(dev_pct)) * 0.3))))
            if score >= 90:
                advice, score_cls, row_cls = "优秀标杆", "green", ""
                if dev_pct <= 0:
                    dev_text = f"{dev_pct}% (优于标准作业程序)"
                else:
                    dev_text = f"{dev_pct:+d}%"
            elif score >= 75:
                advice, score_cls, row_cls = "正常波动", "normal", ""
                dev_text = f"{dev_pct:+d}%"
            else:
                advice, score_cls, row_cls = "建议培训", "error", "warn"
                dev_text = f"{dev_pct:+d}% (超标)"
            staff_rows.append(
                {
                    "name": v["name"],
                    "dept": v["dept"],
                    "initial": (v["name"][0] if v["name"] else "员"),
                    "score": score,
                    "score_cls": score_cls,
                    "row_cls": row_cls,
                    "dev": dev_text,
                    "dev_pct": dev_pct,
                    "advice": advice,
                    "qty": round(v["qty"], 1),
                }
            )
        staff_rows.sort(key=lambda x: -x["score"])

    # 历史盘点：当前 + 洞察/报损按月
    from calendar import monthrange

    today = date.today()
    period_label = f"{today.year}年{today.month}月"

    audit_history = [
        {
            "title": f"{today.month}月月末盘点",
            "time": f"{today.month:02d}-{min(today.day, 28):02d} 18:00",
            "rate": diff_rate,
            "rate_cls": "error" if diff_rate > 3 else ("ok" if diff_rate <= 2.8 else "neutral"),
            "trend": (
                f"趋势{'恶化' if rate_delta > 0 else '改善'}。需重点关注易耗领用与盘点核对。"
                if abs(rate_delta) >= 0.3
                else "表现平稳，持续监控。"
            ),
            "active": True,
        }
    ]
    # 往期：按 insight / damage 的 biz_date·created_at 归月
    month_bags: dict = {}
    for i in insights:
        bd = i.get("biz_date") or (str(i.get("created_at") or "")[:10])
        if not bd:
            continue
        key = str(bd)[:7]
        bag = month_bags.setdefault(key, {"notes": [], "impact": 0.0})
        bag["notes"].append(i.get("recommendation") or i.get("title") or "")
        bag["impact"] += float(i.get("impact_amount") or 0)
    for d in damages:
        bd = str(d.get("created_at") or "")[:10]
        if not bd:
            continue
        key = bd[:7]
        bag = month_bags.setdefault(key, {"notes": [], "impact": 0.0})
        bag["notes"].append(d.get("item_name") or "报损")
        bag["impact"] += float(d.get("fee") or 0)

    cur_key = today.strftime("%Y-%m")
    past_keys = sorted([k for k in month_bags if k != cur_key], reverse=True)
    # 若只有当月，用 prev_diff_rate 合成近两月节点
    if not past_keys:
        for back, rate in ((1, prev_diff_rate), (2, round(max(1.0, prev_diff_rate - 0.6), 1))):
            m = today.month - back
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            last_day = monthrange(y, m)[1]
            note = "布草报废率较高，已建议更换供应商。" if back == 1 else "表现良好，在标准阈值内。"
            audit_history.append(
                {
                    "title": f"{m}月月末盘点",
                    "time": f"{m:02d}-{last_day} 17:30",
                    "rate": rate,
                    "rate_cls": "error" if rate > 3 else ("ok" if rate <= 2.8 else "neutral"),
                    "trend": note,
                    "active": False,
                }
            )
    else:
        for idx, key in enumerate(past_keys[:2]):
            y, m = key.split("-")
            m_i = int(m)
            bag = month_bags[key]
            # 用影响金额相对账面估算差异率
            rate = round(min(9.5, max(1.2, (bag["impact"] / max(book_value, 1)) * 100 + prev_diff_rate * 0.4)), 1)
            note = (bag["notes"][0] if bag["notes"] else "历史盘点归档")[:48]
            last_day = monthrange(int(y), m_i)[1]
            audit_history.append(
                {
                    "title": f"{m_i}月月末盘点",
                    "time": f"{m_i:02d}-{last_day} 17:30",
                    "rate": rate,
                    "rate_cls": "error" if rate > 3 else ("ok" if rate <= 2.8 else "neutral"),
                    "trend": note,
                    "active": False,
                }
            )

    rca_insight = ""
    rca_ins = next((i for i in insights if i.get("category") == "rca"), None)
    if rca_ins:
        rca_insight = f"{rca_ins.get('title') or ''}：{rca_ins.get('recommendation') or ''}".strip("：")
    elif unreg >= count_err and unreg >= natural:
        top_floor = ""
        floors_hit = {}
        for a in alerts:
            fl = a.get("floor") or ""
            if fl:
                floors_hit[fl] = floors_hit.get(fl, 0) + 1
        if floors_hit:
            top_floor = max(floors_hit, key=floors_hit.get)
        rca_insight = (
            f"本月「未登记领用」占比最高（约 {causes[0]['pct']}%）"
            + (f"，主要集中在 {top_floor}" if top_floor else "")
            + "。建议强制客房服务员在补货车出库时使用移动端扫码确认。"
        )
    elif insights:
        rca_insight = f"{insights[0].get('title') or ''}：{insights[0].get('recommendation') or ''}".strip("：")

    rca = {
        "period_label": f"{period_label} - 综合分析视图",
        "book_value": book_value,
        "physical_value": physical_value,
        "diff_rate": diff_rate,
        "prev_diff_rate": prev_diff_rate,
        "rate_delta": rate_delta,
        "threshold": 3.0,
        "need_review": diff_rate > 3.0,
        "causes": causes,
        "staff": staff_rows[:8],
        "audit_history": audit_history[:3],
        "insight": rca_insight,
    }

    return {
        "supplies": supply_rows,
        "category_kpi": list(cat_kpi.values()),
        "alerts": alerts,
        "floors": floors,
        "linen_snapshots": snaps,
        "linen_trend": linen_trend,
        "linen_stages": [{"stage": k, "count": v} for k, v in stage_count.items()],
        "linen_high_wash": high_wash,
        "linen_avg_wash": linen_avg_wash,
        "linen_count": len(linen_items),
        "restock_orders": restock,
        "requisitions": reqs,
        "damages": damages,
        "damage_cost": {
            "total": round(fee_open + fee_done, 2),
            "pending": round(fee_open, 2),
            "incurred": round(fee_done, 2),
        },
        "insights": insights,
        "movements": movements,
        "rca": rca,
        "counts": {
            "low_stock": low_count,
            "open_alerts": len(alerts),
            "open_damage": sum(1 for d in damages if d.get("status") in ("open", "repairing")),
            "open_insights": sum(1 for i in insights if i.get("status") == "open"),
            "restock_pending": sum(1 for o in restock if o.get("status") in ("draft", "submitted")),
        },
    }


def create_damage_ticket(db: Session, payload: dict, *, hotel_id: int, operator: str = "") -> dict:
    """资产/物资报损登记。"""
    payload = payload or {}
    import json

    room_no = (payload.get("room_no") or "").strip()
    description = (payload.get("description") or "").strip()
    asset_category = (payload.get("asset_category") or "").strip()
    if not room_no:
        raise ValidationError("room_no required")
    if not asset_category:
        raise ValidationError("asset_category required")
    if not description:
        raise ValidationError("description required")

    severity = payload.get("severity") or "medium"
    if severity not in ("low", "medium", "high"):
        severity = "medium"

    photos = payload.get("photos") or []
    if isinstance(photos, list):
        photos_json = json.dumps(photos, ensure_ascii=False)
    else:
        photos_json = str(photos)

    tags = payload.get("ai_tags") or []
    if isinstance(tags, list):
        tags_str = ",".join(str(t) for t in tags if t)
    else:
        tags_str = str(tags or "")

    item_name = (payload.get("item_name") or "").strip()
    if not item_name:
        item_name = (asset_category.split("(")[0].strip() or "报损物品") + " · " + description[:24]

    line = payload.get("line") or "amenity"
    if "布草" in asset_category:
        line = "linen"

    fee = payload.get("fee")
    try:
        fee_val = Decimal(str(fee if fee is not None else 0))
    except Exception:
        fee_val = Decimal("0")

    t = DamageTicket(
        hotel_id=hotel_id,
        line=line,
        room_no=room_no,
        item_name=item_name[:120],
        asset_category=asset_category[:80],
        severity=severity,
        description=description,
        photos=photos_json,
        ai_suggestion=payload.get("ai_suggestion") or "",
        ai_risk=payload.get("ai_risk") or "",
        ai_tags=tags_str[:200],
        fee=fee_val,
        status=payload.get("status") or "open",
        note=description[:200],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return row_to_dict(t)


def list_supplies(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(Supply).filter(Supply.hotel_id == hotel_id).order_by(Supply.current_stock < Supply.safety_stock).all()
    )
    return [row_to_dict(s) for s in rows]


def approve_restock_order(db: Session, oid: int) -> dict:
    o = db.get(RestockOrder, oid)
    if not o:
        raise NotFoundError("order not found")
    o.status = "approved"
    db.flush()
    return row_to_dict(o)


def resolve_damage_ticket(db: Session, tid: int) -> dict:
    t = db.get(DamageTicket, tid)
    if not t:
        raise NotFoundError("ticket not found")
    t.status = "closed"
    t.resolved_at = datetime.now()
    db.flush()
    return row_to_dict(t)
