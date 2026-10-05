# SPDX-License-Identifier: Apache-2.0
"""数据洞察 · 经营归因与诊断中心。

只消费历史区间切片做归因；不重复营收预测 / 实时看板 KPI。
智能问数复用 ask_data_service；诊断卡动作只跳转，不改业务数据。
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from typing import Any, Iterator, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from analytics.ask_snapshot import (
    _channel_bucket,
    _mix_from_orders,
    _nights_in_window,
    _segment_bucket,
    build_business_snapshot,
)
from finance.finance_reports_service import resolve_period
from infra.commercial_pack import call as _ccall
from models import (
    Channel,
    InsightDiagnosisResult,
    NightAuditLog,
    Order,
    ProfitInsight,
    Review,
    Room,
    RoomType,
)

OTA_COMMISSION = 0.12
DIM_META = {
    "segment": {"key": "segment", "badge": "客", "title": "客群结构诊断", "path": "/b-data/cohort-list"},
    "channel": {
        "key": "channel",
        "badge": "渠",
        "title": "渠道转化诊断",
        "path": "/analytics?tab=insights&section=channel",
    },
    "review": {
        "key": "review",
        "badge": "评",
        "title": "差评归因",
        "path": "/a-ai-core/ai-negative-review-warning",
    },
    "profit": {"key": "profit", "badge": "利", "title": "利润诊断", "path": "/analytics?tab=profit"},
}

OLAP_DIMS = [
    {"key": "segment", "label": "客群"},
    {"key": "channel", "label": "渠道"},
    {"key": "weekday", "label": "时段"},
    {"key": "room_type", "label": "房型"},
    {"key": "price_band", "label": "价格段"},
    {"key": "member", "label": "会员等级"},
]

SEG_CN = {"leisure": "休闲客", "business": "商务客", "group": "团队", "member": "会员"}
CH_CN = {"ota": "OTA", "direct": "直订", "corp": "协议", "member": "会员/私域"}


def _money(n: float) -> float:
    return round(float(n or 0), 2)


def _pct(n: float, digits: int = 1) -> float:
    return round(float(n or 0), digits)


def _hash_snapshot(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _compare_window(d0: date, d1: date, compare: str) -> tuple[Optional[date], Optional[date], str]:
    days = (d1 - d0).days + 1
    c = (compare or "yoy").lower()
    if c == "none":
        return None, None, "不对比"
    if c == "mom":
        c1 = d0 - timedelta(days=1)
        c0 = c1 - timedelta(days=days - 1)
        return c0, c1, "环比上期"
    # yoy
    try:
        c0 = date(d0.year - 1, d0.month, d0.day)
        c1 = date(d1.year - 1, d1.month, d1.day)
    except ValueError:
        c0 = d0 - timedelta(days=365)
        c1 = d1 - timedelta(days=365)
    return c0, c1, "同比去年"


def _audit_agg(db: Session, hotel_id: int, d0: date, d1: date) -> dict[str, float]:
    row = (
        db.query(
            func.coalesce(func.sum(NightAuditLog.revenue), 0),
            func.coalesce(func.sum(NightAuditLog.room_nights), 0),
        )
        .filter(
            NightAuditLog.hotel_id == hotel_id,
            NightAuditLog.biz_date >= d0,
            NightAuditLog.biz_date <= d1,
        )
        .first()
    )
    rev = float(row[0] or 0) if row else 0.0
    nights = float(row[1] or 0) if row else 0.0
    rooms = max(1, db.query(Room).filter_by(hotel_id=hotel_id).count())
    days = max(1, (d1 - d0).days + 1)
    capacity = rooms * days
    occ = (nights / capacity * 100) if capacity else 0.0
    adr = (rev / nights) if nights > 0 else 0.0
    revpar = adr * occ / 100 if capacity else 0.0
    return {
        "revenue": _money(rev),
        "room_nights": _money(nights),
        "occ_pct": _pct(occ),
        "adr": _money(adr),
        "revpar": _money(revpar),
        "capacity": capacity,
    }


def _order_revenue(db: Session, hotel_id: int, d0: date, d1: date) -> float:
    """无夜审时用订单客房收入兜底（总额 − other_amount，按窗口间夜分摊）。"""
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= d1,
            Order.check_out > d0,
            Order.status.in_(["reserved", "confirmed", "checked_in", "checked_out", "pending"]),
        )
        .all()
    )
    total = 0.0
    for o in orders:
        n = _nights_in_window(o, d0, d1)
        if n <= 0:
            continue
        stay = max(1, (o.check_out - o.check_in).days) if o.check_out and o.check_in else 1
        room_amt = max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        total += room_amt * (n / stay)
    return _money(total)


def period_slice(db: Session, hotel_id: int, d0: date, d1: date) -> dict[str, Any]:
    # 优先走财务报表同源客房 KPI，避免 ADR 吃进非房
    try:
        from finance.finance_reports_service import period_ops_kpis

        ops = period_ops_kpis(db, hotel_id, d0, d1)
        kpi = {
            "revenue": ops["room_revenue"],
            "room_nights": float(ops["sold_nights"] or 0),
            "occ_pct": ops["occ_pct"],
            "adr": ops["adr"],
            "revpar": ops["revpar"],
            "capacity": ops["capacity"],
            "other_revenue": ops.get("other_revenue") or 0,
            "source": ops.get("source"),
        }
    except Exception:
        kpi = _audit_agg(db, hotel_id, d0, d1)
        if kpi["revenue"] <= 0:
            kpi["revenue"] = _order_revenue(db, hotel_id, d0, d1)
            nights = kpi["room_nights"]
            if nights <= 0:
                rooms = max(1, db.query(Room).filter_by(hotel_id=hotel_id).count())
                days = max(1, (d1 - d0).days + 1)
                orders = (
                    db.query(Order)
                    .filter(
                        Order.hotel_id == hotel_id,
                        Order.check_in.isnot(None),
                        Order.check_out.isnot(None),
                        Order.check_in <= d1,
                        Order.check_out > d0,
                        Order.status.in_(["reserved", "confirmed", "checked_in", "checked_out", "pending"]),
                    )
                    .all()
                )
                nights = float(sum(_nights_in_window(o, d0, d1) for o in orders))
                kpi["room_nights"] = _money(nights)
                capacity = rooms * days
                kpi["capacity"] = capacity
                kpi["occ_pct"] = _pct(nights / capacity * 100) if capacity else 0.0
                kpi["adr"] = _money(kpi["revenue"] / nights) if nights > 0 else 0.0
                kpi["revpar"] = _money(kpi["revenue"] / capacity) if capacity and kpi["revenue"] else 0.0
            else:
                kpi["adr"] = _money(kpi["revenue"] / nights) if nights > 0 else 0.0
                kpi["revpar"] = (
                    _money(kpi["revenue"] / kpi["capacity"]) if kpi.get("capacity") and kpi["revenue"] else 0.0
                )

    ch_mix, seg_mix = _mix_from_orders(db, hotel_id, d0, d1)
    reviews = (
        db.query(Review)
        .filter(Review.hotel_id == hotel_id, Review.created_at.isnot(None))
        .filter(Review.created_at >= datetime.combine(d0, datetime.min.time()))
        .filter(Review.created_at < datetime.combine(d1 + timedelta(days=1), datetime.min.time()))
        .all()
    )
    ratings = [float(r.rating or 0) for r in reviews if r.rating is not None]
    avg_rating = _pct(sum(ratings) / len(ratings), 2) if ratings else None
    replied = sum(1 for r in reviews if r.replied)
    reply_rate = _pct(replied / len(reviews) * 100) if reviews else None
    # 简易 NPS 代理：评分≥4 为推荐，≤2 为贬损
    promoters = sum(1 for x in ratings if x >= 4)
    detractors = sum(1 for x in ratings if x <= 2)
    nps = round((promoters - detractors) / len(ratings) * 100) if ratings else None

    insights = (
        db.query(ProfitInsight)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(ProfitInsight.id.desc())
        .limit(5)
        .all()
    )
    profit_hints = [
        {
            "title": x.title or "利润线索",
            "detail": (x.recommendation or "")[:160],
            "impact": float(x.impact_amount or 0),
        }
        for x in insights
    ]

    return {
        "kpi": kpi,
        "channel_mix": ch_mix,
        "segment_mix": seg_mix,
        "review": {
            "count": len(reviews),
            "avg_rating": avg_rating,
            "reply_rate": reply_rate,
            "nps": nps,
        },
        "profit_hints": profit_hints,
    }


def _delta_pt(cur: float, base: Optional[float]) -> Optional[float]:
    if base is None:
        return None
    return _pct((cur - base) * 100, 1)


def _sev_from_gap(gap_pt: Optional[float], warn: float, crit: float) -> str:
    if gap_pt is None:
        return "P3"
    if abs(gap_pt) >= crit:
        return "P1"
    if abs(gap_pt) >= warn:
        return "P2"
    return "P3"


def _card(
    dim: str,
    *,
    severity: str,
    finding: str,
    action: str,
    action_label: str,
    path: str,
    evidence: dict[str, Any],
    revenue_impact: str = "unknown",
    confidence: str = "中",
) -> dict[str, Any]:
    meta = DIM_META[dim]
    return {
        "dimension": dim,
        "badge": meta["badge"],
        "title": meta["title"],
        "severity": severity,
        "finding": finding,
        "suggested_action": action,
        "action_label": action_label,
        "action_path": path,
        "evidence": evidence,
        "revenue_impact": revenue_impact,
        "confidence": confidence,
    }


def build_diagnosis_cards(
    cur: dict[str, Any],
    base: Optional[dict[str, Any]],
    *,
    compare_label: str,
) -> list[dict[str, Any]]:
    """诊断总览瘦卡：一句话结论 + 单一跳转，不堆排行/瀑布/策略列表。"""
    seg = cur.get("segment_mix") or {}
    seg_b = (base or {}).get("segment_mix") or {}
    biz = float(seg.get("business_pct") or 0)
    biz_b = float(seg_b.get("business_pct") or 0) if base else None
    mem = float(seg.get("member_pct") or 0)
    mem_b = float(seg_b.get("member_pct") or 0) if base else None
    biz_gap = _delta_pt(biz, biz_b)
    mem_gap = _delta_pt(mem, mem_b)
    if biz_gap is not None and biz_gap < -3:
        seg_find = (
            f"商务客 {biz * 100:.1f}%（{compare_label} {biz_gap:+.1f}pt），"
            f"会员 {mem * 100:.1f}%" + (f"（{mem_gap:+.1f}pt）" if mem_gap is not None else "") + "，结构走弱。"
        )
        seg_sev = _sev_from_gap(biz_gap, 3, 6)
    elif biz > 0 or mem > 0:
        seg_find = f"商务客 {biz * 100:.1f}%、会员 {mem * 100:.1f}%，结构平稳。"
        seg_sev = "P3"
    else:
        seg_find = "客群样本不足，暂无法判断。"
        seg_sev = "P3"

    cards = [
        _card(
            "segment",
            severity=seg_sev,
            finding=seg_find,
            action="去客群列表查看分群结构与运营动作",
            action_label="客群列表",
            path="/b-data/cohort-list",
            evidence={"business_pct": biz, "member_pct": mem, "business_delta_pt": biz_gap},
        )
    ]

    ch = cur.get("channel_mix") or {}
    ota = float(ch.get("ota_pct") or 0)
    direct = float(ch.get("direct_pct") or 0)
    kpi = cur.get("kpi") or {}
    if ota >= 0.55:
        ch_find = f"OTA 占比 {ota * 100:.0f}%（警戒线 55%），直订 {direct * 100:.0f}%。"
        ch_sev = "P1" if ota >= 0.60 else "P2"
    elif ota > 0:
        ch_find = f"OTA 占比 {ota * 100:.0f}%，直订 {direct * 100:.0f}%，结构尚可。"
        ch_sev = "P3"
    else:
        ch_find = "渠道样本不足。"
        ch_sev = "P3"
    cards.append(
        _card(
            "channel",
            severity=ch_sev,
            finding=ch_find,
            action="去专题洞察看转化排行与质量分档",
            action_label="专题洞察 · 渠道",
            path="/analytics?tab=insights&section=channel",
            evidence={"ota_pct": ota, "direct_pct": direct},
        )
    )

    rev = cur.get("review") or {}
    nps = rev.get("nps")
    avg_r = rev.get("avg_rating")
    cnt = int(rev.get("count") or 0)
    if cnt == 0:
        rev_find = "本期无点评样本。"
        rev_sev = "P3"
    else:
        bits = [f"点评 {cnt} 条"]
        if nps is not None:
            bits.append(f"NPS {nps}")
        if avg_r is not None:
            bits.append(f"均分 {avg_r}")
        rev_find = "；".join(bits) + "。"
        rev_sev = "P2" if (nps is not None and nps < 40) or (avg_r is not None and avg_r < 4.2) else "P3"
    cards.append(
        _card(
            "review",
            severity=rev_sev,
            finding=rev_find,
            action="去 AI 差评预警查看归因与处置",
            action_label="AI 差评预警",
            path="/a-ai-core/ai-negative-review-warning",
            evidence=rev,
            confidence="中" if cnt else "低",
        )
    )

    goppar = _money(float(kpi.get("revpar") or 0) * 0.45)
    hints = cur.get("profit_hints") or []
    if hints:
        profit_find = f"GOPPAR 代理约 ¥{goppar}；有开放利润线索，详情见利润优化。"
        profit_sev = "P2"
    else:
        profit_find = f"GOPPAR 代理约 ¥{goppar}；成本与净利动作见利润优化。"
        profit_sev = "P3"
    cards.append(
        _card(
            "profit",
            severity=profit_sev,
            finding=profit_find,
            action="去利润优化查看瀑布与策略",
            action_label="利润优化",
            path="/analytics?tab=profit",
            evidence={"goppar_proxy": goppar},
            confidence="低" if not hints else "中",
        )
    )
    return cards


def _persist_cards(
    db: Session,
    hotel_id: int,
    *,
    biz_range: str,
    compare_baseline: str,
    cards: list[dict[str, Any]],
    snapshot_hash: str,
) -> None:
    try:
        for c in cards:
            db.add(
                InsightDiagnosisResult(
                    hotel_id=hotel_id,
                    biz_range=biz_range,
                    compare_baseline=compare_baseline,
                    dimension=c["dimension"],
                    severity=c["severity"],
                    evidence_json=json.dumps(c.get("evidence") or {}, ensure_ascii=False),
                    revenue_impact=str(c.get("revenue_impact") or "unknown")[:80],
                    suggested_action=str(c.get("suggested_action") or "")[:240],
                    confidence=str(c.get("confidence") or "中")[:8],
                    snapshot_hash=snapshot_hash,
                    created_by="ai_agent",
                )
            )
        db.commit()
    except Exception:
        db.rollback()


def build_olap(
    db: Session,
    hotel_id: int,
    d0: date,
    d1: date,
    *,
    dim: str = "channel",
) -> dict[str, Any]:
    dim = dim if dim in {x["key"] for x in OLAP_DIMS} else "channel"
    channels = {c.id: c for c in db.query(Channel).all()}
    types = {t.id: t for t in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= d1,
            Order.check_out > d0,
            Order.status.in_(["reserved", "confirmed", "checked_in", "checked_out", "pending"]),
        )
        .all()
    )
    buckets: dict[str, dict[str, float]] = {}

    def bump(key: str, nights: int, amount: float):
        row = buckets.setdefault(key, {"nights": 0.0, "revenue": 0.0})
        row["nights"] += nights
        row["revenue"] += amount

    for o in orders:
        n = _nights_in_window(o, d0, d1)
        if n <= 0:
            continue
        stay = max(1, (o.check_out - o.check_in).days) if o.check_out and o.check_in else 1
        # OLAP 营收/价格段用客房收入，避免非房抬高 ADR 段
        room_amt = max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        amt = room_amt * (n / stay)
        ch = channels.get(o.channel_id)
        code = ch.code if ch else None
        ctype = ch.type if ch else None

        if dim == "segment":
            key = SEG_CN.get(_segment_bucket(o, code), "其他")
        elif dim == "channel":
            key = CH_CN.get(_channel_bucket(code, ctype), "其他")
        elif dim == "weekday":
            # 按入住日是否周末粗分
            weekend = 0
            cur = max(o.check_in, d0)
            last = min(o.check_out - timedelta(days=1), d1)
            while cur <= last:
                if cur.weekday() >= 5:
                    weekend += 1
                cur += timedelta(days=1)
            key = "周末" if weekend >= max(1, n) / 2 else "平日"
        elif dim == "room_type":
            rt = types.get(o.room_type_id) if getattr(o, "room_type_id", None) else None
            key = (rt.name if rt else None) or "未分房型"
        elif dim == "price_band":
            unit = amt / max(1, n)
            if unit < 300:
                key = "<¥300"
            elif unit < 500:
                key = "¥300-500"
            elif unit < 800:
                key = "¥500-800"
            else:
                key = "≥¥800"
        else:  # member
            key = (
                "会员相关"
                if _segment_bucket(o, code) == "member" or _channel_bucket(code, ctype) == "member"
                else "非会员"
            )

        bump(key, n, amt)

    items = sorted(buckets.items(), key=lambda x: x[1]["revenue"], reverse=True)
    total_n = sum(v["nights"] for _, v in items) or 1
    total_r = sum(v["revenue"] for _, v in items) or 1
    series = [
        {
            "label": k,
            "nights": int(v["nights"]),
            "revenue": _money(v["revenue"]),
            "share_pct": _pct(v["nights"] / total_n * 100),
            "rev_share_pct": _pct(v["revenue"] / total_r * 100),
            "bar_pct": _pct(v["revenue"] / total_r * 100),
        }
        for k, v in items
    ]
    return {
        "dim": dim,
        "dims": OLAP_DIMS,
        "series": series,
        "total_nights": int(total_n if items else 0),
        "total_revenue": _money(total_r if items else 0),
    }


def build_reports(d0: date, d1: date, cur: dict[str, Any], cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    week = d1.isocalendar()
    week_label = f"W{week[1]:02d}"
    p1 = sum(1 for c in cards if c.get("severity") == "P1")
    rev = (cur.get("kpi") or {}).get("revenue") or 0
    return [
        {
            "id": "weekly",
            "title": f"经营周报（{week_label}）",
            "meta": f"区间摘要 · P1 异常 {p1} 条 · 营收 ¥{rev:,.0f}",
            "status": "ready",
            "status_label": "已生成",
            "exportable": True,
        },
        {
            "id": "monthly",
            "title": f"经营月报（{d1.strftime('%Y-%m')}）",
            "meta": "USALI 口径摘要 · 可导出",
            "status": "ready",
            "status_label": "已生成",
            "exportable": True,
        },
        {
            "id": "channel_profit",
            "title": "渠道盈利月报",
            "meta": "含净收益对比 · 待生成",
            "status": "pending",
            "status_label": "待生成",
            "exportable": False,
        },
        {
            "id": "segment_value",
            "title": "客群价值季报",
            "meta": "本季末 · 排程中",
            "status": "scheduled",
            "status_label": "排程中",
            "exportable": False,
        },
    ]


def build_workspace(
    db: Session,
    hotel_id: int,
    *,
    period: str = "month",
    compare: str = "yoy",
    start: Optional[str] = None,
    end: Optional[str] = None,
    olap_dim: str = "channel",
) -> dict[str, Any]:
    # 洞察页时间：本周/本月/本季/自定义（映射 resolve_period）
    p = (period or "month").lower()
    if p == "quarter":
        today = date.today()
        q = (today.month - 1) // 3
        d0 = date(today.year, q * 3 + 1, 1)
        d1 = today
        label = f"{d0.isoformat()} ~ {d1.isoformat()}"
    else:
        map_p = {"week": "week", "month": "month", "custom": "custom"}.get(p, "month")
        d0, d1, label = resolve_period(map_p, start=start, end=end)

    c0, c1, compare_label = _compare_window(d0, d1, compare)
    cur = period_slice(db, hotel_id, d0, d1)
    base = period_slice(db, hotel_id, c0, c1) if c0 and c1 else None
    cards = build_diagnosis_cards(cur, base, compare_label=compare_label)
    snap = {
        "range": {"start": d0.isoformat(), "end": d1.isoformat(), "label": label},
        "compare": compare,
        "kpi": cur.get("kpi"),
        "channel_mix": cur.get("channel_mix"),
        "segment_mix": cur.get("segment_mix"),
        "review": cur.get("review"),
    }
    snap_hash = _hash_snapshot(snap)
    olap = build_olap(db, hotel_id, d0, d1, dim=olap_dim)
    reports = build_reports(d0, d1, cur, cards)

    ask_examples = [
        "本月哪些渠道在亏钱？",
        "商务客是不是在流失？",
        "OTA 占比是否过高？",
        "会员复购有没有变差？",
    ]

    return {
        "period": p,
        "compare": compare,
        "compare_label": compare_label,
        "range": {"start": d0.isoformat(), "end": d1.isoformat(), "label": label},
        "compare_range": ({"start": c0.isoformat(), "end": c1.isoformat()} if c0 and c1 else None),
        "cards": cards,
        "olap": olap,
        "reports": reports,
        "ask_examples": ask_examples,
        "snapshot_hash": snap_hash,
        "note": "需要更细的渠道、订单或利润分析，可切换上方专题或进入 AI 问数。",
    }


def run_ask(
    db: Session,
    hotel_id: int,
    *,
    question: str = "",
    growth_factor: float = 1.0,
    period: str = "month",
    compare: str = "yoy",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict[str, Any]:
    """智能问数：复用四板斧，附带用户问题（只读建议）。"""
    result = _ccall(
        "commercial.analytics.ask_data_service", "generate_ask_data", db, hotel_id, growth_factor=growth_factor
    )
    result["question"] = (question or "").strip()[:200]
    for it in result.get("issues") or []:
        it["action_path"] = it.get("pricing_path") or "/pricing"
        it["action_label"] = "价格助手"

    # 同步刷新四维卡并留痕
    ws = build_workspace(db, hotel_id, period=period, compare=compare, start=start, end=end)
    _persist_cards(
        db,
        hotel_id,
        biz_range=f"{ws['range']['start']}~{ws['range']['end']}",
        compare_baseline=compare,
        cards=ws["cards"],
        snapshot_hash=ws["snapshot_hash"],
    )
    result["cards"] = ws["cards"]
    result["snapshot_hash"] = ws["snapshot_hash"]
    return result


def stream_ask(
    db: Session,
    hotel_id: int,
    *,
    question: str = "",
    growth_factor: float = 1.0,
    period: str = "month",
    compare: str = "yoy",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Iterator[dict[str, Any]]:
    q = (question or "").strip()[:200]
    if q:
        yield {"type": "meta", "data": {"question": q}}
    final: dict[str, Any] | None = None
    for evt in _ccall(
        "commercial.analytics.ask_data_service", "stream_ask_data", db, hotel_id, growth_factor=growth_factor
    ):
        if evt.get("type") == "done" and isinstance(evt.get("data"), dict):
            data = evt["data"]
            data["question"] = q
            for it in data.get("issues") or []:
                it["action_path"] = it.get("pricing_path") or "/pricing"
                it["action_label"] = "价格助手"
            ws = build_workspace(db, hotel_id, period=period, compare=compare, start=start, end=end)
            _persist_cards(
                db,
                hotel_id,
                biz_range=f"{ws['range']['start']}~{ws['range']['end']}",
                compare_baseline=compare,
                cards=ws["cards"],
                snapshot_hash=ws["snapshot_hash"],
            )
            data["cards"] = ws["cards"]
            data["snapshot_hash"] = ws["snapshot_hash"]
            final = data
            yield {"type": "done", "data": data}
        else:
            yield evt
    if final is None:
        return


def chat_reply(
    db: Session,
    hotel_id: int,
    *,
    message: str,
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """对话式问数：底层仍走智能问数快照 + 简短答复。"""
    msg = (message or "").strip()[:300]
    if not msg:
        return {"reply": "请先输入想了解的经营问题。", "issues": []}

    snap = build_business_snapshot(db, hotel_id)
    ask = _ccall("commercial.analytics.ask_data_service", "generate_ask_data", db, hotel_id)
    issues = ask.get("issues") or []

    # 优先用规则快照拼可读答复，避免再开一轮自由对话模型
    ch = snap.get("channel_mix") or {}
    seg = snap.get("segment_mix") or {}
    ota = float(ch.get("ota_pct") or 0)
    biz = float(seg.get("business_pct") or 0)
    lines = []
    if "ota" in msg.lower() or "渠道" in msg:
        lines.append(f"当前窗口 OTA 占比约 {ota * 100:.0f}%，直订约 {float(ch.get('direct_pct') or 0) * 100:.0f}%。")
    if "商务" in msg or "客群" in msg:
        lines.append(f"商务客占比约 {biz * 100:.0f}%，会员约 {float(seg.get('member_pct') or 0) * 100:.0f}%。")
    if issues:
        top = issues[0]
        lines.append(
            f"优先关注：{top.get('dimension')}（{top.get('severity')}）。"
            f"{top.get('evidence')} → 建议「{top.get('suggested_action')}」（跳转价格助手确认）。"
        )
    elif not lines:
        lines.append("当前规则预检未发现高优异常。可换个维度再问，例如渠道占比或商务客结构。")

    hist = history or []
    return {
        "reply": " ".join(lines),
        "issues": issues[:3],
        "history_len": len(hist) + 1,
        "created_by": ask.get("ai_source") or "ai_agent",
    }
