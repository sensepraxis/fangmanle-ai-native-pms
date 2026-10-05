# SPDX-License-Identifier: Apache-2.0
"""营销自动化规则。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from mkt._mkt_utils import _jdumps, _jloads
from models import MktAutomation, Order

TRIGGER_TYPES = ("birthday", "checkin_pre", "stay_post", "festival", "level_expiry")
ACTION_TYPES = ("send_coupon", "send_msg", "add_tag", "create_task")


def list_automations(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(MktAutomation).filter_by(hotel_id=hotel_id).order_by(MktAutomation.id.asc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "trigger_type": r.trigger_type,
            "trigger": _jloads(r.trigger_json, {}),
            "action_type": r.action_type,
            "action": _jloads(r.action_json, {}),
            "frequency_cap_days": r.frequency_cap_days,
            "is_enabled": bool(r.is_enabled),
            "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def upsert_automation(db: Session, hotel_id: int, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    ttype = str(payload.get("trigger_type") or "").strip()
    if not name:
        raise InvalidStateError('"请填写规则名称"')
    if ttype not in TRIGGER_TYPES:
        raise InvalidStateError('f"触发类型无效：{ttype}"')
    atype = str(payload.get("action_type") or "send_msg")
    if atype not in ACTION_TYPES:
        raise InvalidStateError('f"动作类型无效：{atype}"')
    row = None
    if payload.get("id"):
        row = db.query(MktAutomation).filter_by(id=int(payload["id"]), hotel_id=hotel_id).first()
    if not row:
        row = MktAutomation(hotel_id=hotel_id, name=name, trigger_type=ttype)
        db.add(row)
    row.name = name
    row.trigger_type = ttype
    row.trigger_json = _jdumps(payload.get("trigger") or {})
    row.action_type = atype
    row.action_json = _jdumps(payload.get("action") or {})
    row.frequency_cap_days = int(payload.get("frequency_cap_days") or 30)
    if "is_enabled" in payload:
        row.is_enabled = bool(payload.get("is_enabled"))
    db.commit()
    db.refresh(row)
    return next(x for x in list_automations(db, hotel_id) if x["id"] == row.id)


def set_automation_enabled(db: Session, hotel_id: int, auto_id: int, enabled: bool) -> dict:
    row = db.query(MktAutomation).filter_by(id=auto_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"规则不存在"')
    row.is_enabled = bool(enabled)
    db.commit()
    return next(x for x in list_automations(db, hotel_id) if x["id"] == auto_id)


def delete_automation(db: Session, hotel_id: int, auto_id: int) -> dict:
    row = db.query(MktAutomation).filter_by(id=auto_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"规则不存在"')
    db.delete(row)
    db.commit()
    return {"ok": True}


def preview_automation(db: Session, hotel_id: int, auto_id: int) -> dict:
    """干跑：估算今日命中人数（规则化估算，不真正触达）。"""
    row = db.query(MktAutomation).filter_by(id=auto_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"规则不存在"')
    from bootstrap.ensure_member_crm import _hotel_guest_ids

    gids = _hotel_guest_ids(db, hotel_id)
    n = len(gids)
    tj = _jloads(row.trigger_json, {})
    if row.trigger_type == "birthday":
        hit = max(1, n // 30) if n else 0
    elif row.trigger_type == "checkin_pre":
        days = int(tj.get("days_before") or 3)
        hit = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.check_in >= date.today(),
                Order.check_in <= date.today() + timedelta(days=days),
            )
            .count()
        )
    elif row.trigger_type == "stay_post":
        days = int(tj.get("days_after") or 7)
        hit = (
            db.query(Order)
            .filter(
                Order.hotel_id == hotel_id,
                Order.check_out >= date.today() - timedelta(days=days),
                Order.check_out <= date.today(),
            )
            .count()
        )
    else:
        hit = max(0, n // 20)
    row.last_run_at = datetime.now()
    db.commit()
    return {
        "automation_id": auto_id,
        "trigger_type": row.trigger_type,
        "estimated_hits": hit,
        "guest_pool": n,
        "frequency_cap_days": row.frequency_cap_days,
        "dry_run": True,
        "message": f"预估命中 {hit} 人（未真实发送，频控 {row.frequency_cap_days} 天）",
    }
