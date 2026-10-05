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
from infra.i18n import t as _t
from models import Asset, AssetAlert, AssetAuditItem, AssetEvent, AssetInsight, AssetMaintenance, RoomIotMetric

# models.__all__ 未覆盖全部 ORM（如 SupplyAlert）；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})


def build_assets_board(db: Session, hotel_id: int):
    """设备设施聚合：台账 / 告警 / 洞察 / 维保 / 盘点 / 生命周期事件。"""
    assets = db.query(Asset).filter_by(hotel_id=hotel_id).order_by(Asset.id.asc()).all()
    asset_rows = []
    total_value = 0.0
    health_sum = 0
    health_n = 0
    maint_due = 0
    abnormal = 0
    for a in assets:
        d = row_to_dict(a)
        if not d.get("asset_no"):
            d["asset_no"] = a.sn or f"EQ-{a.id:05d}"
        score = int(a.health_score or 0)
        if a.health_score is not None:
            health_sum += score
            health_n += 1
        total_value += float(a.current_value or a.purchase_value or 0)
        if a.status in ("maintenance", "abnormal") or score and score < 70:
            maint_due += 1
        if a.status == "abnormal" or (score and score < 55):
            abnormal += 1
        d["health_label"] = (
            "异常"
            if a.status == "abnormal" or score < 55
            else ("待维保" if a.status == "maintenance" or score < 75 else "良好")
        )
        asset_rows.append(d)

    avg_health = round(health_sum / health_n, 1) if health_n else 0

    cat_kpi = {}
    for r in asset_rows:
        cname = r.get("category") or "其他"
        b = cat_kpi.setdefault(cname, {"name": cname, "count": 0, "value": 0.0, "low": 0})
        b["count"] += 1
        b["value"] += float(r.get("current_value") or 0)
        if (r.get("health_score") or 100) < 70 or r.get("status") in ("maintenance", "abnormal"):
            b["low"] += 1

    # 折旧分析：按类别汇总原值 / 净值 / 平均账龄（年）
    today_d = date.today()
    dep_cats: dict = {}
    for a in assets:
        cname = (a.category or "其他").strip() or "其他"
        bag = dep_cats.setdefault(
            cname,
            {
                "label": cname,
                "purchase": 0.0,
                "current": 0.0,
                "count": 0,
                "age_sum": 0.0,
            },
        )
        pv = float(a.purchase_value or 0)
        cv = float(a.current_value if a.current_value is not None else pv)
        bag["purchase"] += pv
        bag["current"] += cv
        bag["count"] += 1
        if a.purchase_date:
            bag["age_sum"] += max(0.0, (today_d - a.purchase_date).days / 365.25)
        else:
            bag["age_sum"] += 3.0
    depreciation_chart = []
    for bag in dep_cats.values():
        n = max(bag["count"], 1)
        purchase = round(bag["purchase"], 2)
        current = round(bag["current"], 2)
        age_avg = round(bag["age_sum"] / n, 1)
        residual_pct = round(100 * current / purchase, 1) if purchase > 0 else 0
        depreciation_chart.append(
            {
                "label": bag["label"],
                "purchase": purchase,
                "current": current,
                "count": bag["count"],
                "age_years": age_avg,
                "residual_pct": residual_pct,
            }
        )
    depreciation_chart.sort(key=lambda x: x["purchase"], reverse=True)

    alerts = [
        row_to_dict(a)
        for a in db.query(AssetAlert)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(AssetAlert.id.desc())
        .limit(30)
        .all()
    ]
    insights = [
        row_to_dict(i)
        for i in db.query(AssetInsight).filter_by(hotel_id=hotel_id).order_by(AssetInsight.id.desc()).limit(20).all()
    ]
    maint = [
        row_to_dict(m)
        for m in db.query(AssetMaintenance)
        .filter_by(hotel_id=hotel_id)
        .order_by(AssetMaintenance.id.desc())
        .limit(40)
        .all()
    ]
    audits = [
        row_to_dict(x)
        for x in db.query(AssetAuditItem)
        .filter_by(hotel_id=hotel_id)
        .order_by(AssetAuditItem.id.desc())
        .limit(30)
        .all()
    ]
    events = [
        row_to_dict(e)
        for e in db.query(AssetEvent)
        .filter_by(hotel_id=hotel_id)
        .order_by(AssetEvent.happened_at.desc())
        .limit(80)
        .all()
    ]

    # IoT 趋势：默认取 1F 当日时序；无则回退任意楼层
    iot_q = (
        db.query(RoomIotMetric).filter_by(hotel_id=hotel_id, floor="1F").order_by(RoomIotMetric.recorded_at.asc()).all()
    )
    if not iot_q:
        iot_q = (
            db.query(RoomIotMetric)
            .filter_by(hotel_id=hotel_id)
            .order_by(RoomIotMetric.recorded_at.asc())
            .limit(24)
            .all()
        )
    iot_trend = []
    for m in iot_q:
        ts = m.recorded_at
        iot_trend.append(
            {
                "hour": ts.strftime("%H:%M") if ts else "",
                "energy_kw": float(m.energy_kw or 0),
                "temp_c": float(m.temp_c or 0),
                "humidity_pct": float(m.humidity_pct or 0),
                "floor": m.floor,
            }
        )

    # 按资产分组事件，便于履历页
    events_by_asset = {}
    for e in events:
        aid = e.get("asset_id")
        events_by_asset.setdefault(aid, []).append(e)

    open_audit = sum(
        1
        for x in audits
        if x.get("status") == "open" and int(x.get("theoretical_qty") or 0) != int(x.get("actual_qty") or 0)
    )
    open_maint = sum(1 for m in maint if m.get("status") in ("scheduled", "overdue", "doing"))

    return {
        "assets": asset_rows,
        "category_kpi": list(cat_kpi.values()),
        "depreciation_chart": depreciation_chart,
        "iot_trend": iot_trend,
        "alerts": alerts,
        "insights": insights,
        "maintenance": maint,
        "audit_items": audits,
        "events": events,
        "events_by_asset": events_by_asset,
        "summary": {
            "total_value": round(total_value, 2),
            "avg_health": avg_health,
            "maint_due": maint_due,
            "abnormal": abnormal,
            "asset_count": len(asset_rows),
            "total_purchase": round(sum(float(a.purchase_value or 0) for a in assets), 2),
        },
        "counts": {
            "open_alerts": len(alerts),
            "open_insights": sum(1 for i in insights if i.get("status") == "open"),
            "open_audit": open_audit,
            "open_maint": open_maint,
        },
    }


def _parse_asset_budget(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace("¥", "")
    if not s:
        return None
    try:
        return max(0.0, float(s))
    except ValueError:
        return None


def _parse_asset_room_fields(room: Optional[str]) -> tuple[Optional[str], str]:
    r = (room or "").strip()
    if not r:
        return None, "待安装"
    m = re.search(r"(\d{3,4})", r)
    room_no = m.group(1) if m else None
    if room_no and not re.search(r"房|F|层|楼|机房|区", r):
        return room_no, f"{room_no} 房"
    return room_no, r


def _reason_label(reason: str) -> str:
    return {"new": "新店/新增", "replace": "更换旧设备", "expand": "扩容增购"}.get(reason, reason)


def register_asset(db: Session, hotel_id: int, payload: dict):
    """登记新资产：写入 assets 表并记录生命周期事件。"""
    name = (payload.name or "").strip()
    if not name:
        raise InvalidStateError("设备名称不能为空")

    asset_no = (payload.asset_no or "").strip()
    if asset_no:
        dup = db.query(Asset).filter_by(hotel_id=hotel_id, asset_no=asset_no).first()
        if dup:
            raise InvalidStateError(f"设备编号 {asset_no} 已存在")

    room_no, location = _parse_asset_room_fields(payload.room)
    budget = _parse_asset_budget(payload.budget)
    today = date.today()
    qty = max(1, int(payload.qty or 1))

    asset = Asset(
        hotel_id=hotel_id,
        name=name,
        category=(payload.category or "其他").strip() or "其他",
        asset_no=asset_no or None,
        brand_model=(payload.spec or "").strip() or None,
        room_no=room_no,
        location=location,
        supplier=(payload.supplier or "").strip() or None,
        purchase_date=today,
        purchase_value=budget,
        current_value=budget,
        repair_cost_total=0,
        health_score=92,
        insight=(payload.note or "").strip() or "新登记资产，待完善台账",
        dept="工程维保部",
        status="active",
    )
    db.add(asset)
    db.flush()

    if not asset.asset_no:
        asset.asset_no = f"EQ-{asset.id:05d}"
        asset.sn = f"MFG-{asset.id:04d}"

    reason = payload.reason if payload.reason in ("new", "replace", "expand") else "new"
    note_parts = [f"申请类型：{_reason_label(reason)}"]
    if qty > 1:
        note_parts.append(f"数量：{qty}")
    if budget is not None:
        note_parts.append(f"预算：¥{budget:,.0f}")
    if payload.supplier:
        note_parts.append(f"建议供应商：{payload.supplier.strip()}")
    if payload.replace_asset_id:
        note_parts.append(f"更换原设备 ID：{payload.replace_asset_id}")
    if payload.note:
        note_parts.append(payload.note.strip())

    event = AssetEvent(
        hotel_id=hotel_id,
        asset_id=asset.id,
        event_type="purchase" if reason == "new" else reason,
        title="资产登记入库",
        happened_at=datetime.now(),
        note="；".join(note_parts),
    )
    db.add(event)
    db.commit()
    db.refresh(asset)

    d = row_to_dict(asset)
    if not d.get("asset_no"):
        d["asset_no"] = asset.asset_no
    d["health_label"] = _t("良好")
    return d


def _maint_status_label(st: str) -> str:
    return {
        "done": _t("已完成"),
        "overdue": _t("逾期"),
        "doing": _t("处理中"),
        "scheduled": _t("计划中"),
    }.get(st or "scheduled", _t("计划中"))


def _maint_progress_step(st: str) -> int:
    return {"scheduled": 1, "overdue": 1, "doing": 3, "done": 4}.get(st or "scheduled", 1)


def _maintenance_detail_dict(m: AssetMaintenance, asset: Asset) -> dict:
    st = m.status or "scheduled"
    today = date.today()
    due = m.due_date
    is_overdue = st != "done" and ((due is not None and due < today) or st == "overdue")
    days_until = (due - today).days if due and st != "done" else None

    created = m.created_at
    completed = m.completed_at
    d = row_to_dict(m)
    d["wo_no"] = f"WO-{m.id}"
    d["status_label"] = _maint_status_label(st)
    d["is_overdue"] = is_overdue
    d["days_until_due"] = days_until
    d["progress_step"] = _maint_progress_step(st)
    d["progress_steps"] = [_t("已创建"), _t("已派工"), _t("维修中"), _t("已完成")]
    d["asset"] = {
        "id": asset.id,
        "name": asset.name,
        "asset_no": asset.asset_no or asset.sn or f"EQ-{asset.id:05d}",
        "room_no": asset.room_no,
        "location": asset.location,
        "category": asset.category,
    }
    d["timeline"] = [
        {"label": _t("工单创建"), "time": created.isoformat() if created else None, "done": True},
        {
            "label": _t("派工指派"),
            "time": created.isoformat() if created and m.owner else None,
            "done": st in ("doing", "done") or bool(m.owner),
        },
        {"label": _t("现场维修"), "time": None, "done": st in ("doing", "done")},
        {
            "label": _t("验收关单"),
            "time": completed.isoformat() if completed else None,
            "done": st == "done",
        },
    ]
    return d


def list_asset_maintenance(db: Session, hotel_id: int, asset_id: int):
    """单设备关联维保/维修工单（含历史与待办，不限条数）。"""
    asset = db.query(Asset).filter_by(id=asset_id, hotel_id=hotel_id).first()
    if not asset:
        raise NotFoundError("asset not found")
    rows = db.query(AssetMaintenance).filter_by(hotel_id=hotel_id, asset_id=asset_id).all()
    ordered = _sort_asset_maintenance(rows)
    return [row_to_dict(m) for m in ordered]


def get_asset_maintenance_detail(db: Session, hotel_id: int, asset_id: int, maint_id: int):
    """单条维保/维修工单详情（含设备上下文与进度时间轴）。"""
    asset = db.query(Asset).filter_by(id=asset_id, hotel_id=hotel_id).first()
    if not asset:
        raise NotFoundError("asset not found")
    m = db.query(AssetMaintenance).filter_by(id=maint_id, hotel_id=hotel_id, asset_id=asset_id).first()
    if not m:
        raise NotFoundError("maintenance not found")
    return _maintenance_detail_dict(m, asset)


def _sort_asset_maintenance(rows: list) -> list:
    """待办优先（逾期→处理中→计划中），同类按到期日升序；已完成按到期日降序。"""
    pending: list = []
    done: list = []
    for m in rows:
        if (m.status or "scheduled") == "done":
            done.append(m)
        else:
            pending.append(m)

    def pending_key(m):
        st = m.status or "scheduled"
        pri = {"overdue": 0, "doing": 1, "scheduled": 2}.get(st, 3)
        due = m.due_date or date.max
        return (pri, due)

    pending.sort(key=pending_key)
    done.sort(key=lambda m: m.due_date or date.min, reverse=True)
    return pending + done
