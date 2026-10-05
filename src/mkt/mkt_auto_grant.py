# SPDX-License-Identifier: Apache-2.0
"""自动发券规则（产品层）：规则引擎条件 + 调度扫描 + 预览命中。

所有规则强制通道建联（H5/私域 IM），由 mkt_rule_engine 门禁保证。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.i18n import TranslatingMap
from mkt.mkt_rule_engine import (
    build_guest_context,
    condition_to_text,
    ensure_h5_gate,
    eval_condition,
    is_channel_bound,
    legacy_to_condition,
    list_field_catalog,
    match_guests,
)
from models import Guest, MktCoupon, MktCouponGrantLog, MktCouponTrigger

SCENE_LABELS = TranslatingMap(
    {
        "NEW_WECHAT_MEMBER": "新用户",
        "REG_DAYS": "新用户",
        "CHECKOUT_DAYS": "复购",
        "RULE_ENGINE": "规则引擎",
        "BIRTHDAY": "关怀",
        "HOLIDAY": "节日",
        "CUSTOM": "自定义",
        "DAILY": "日扫",
    }
)


def _params(raw: Any) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _rule_condition(t: MktCouponTrigger) -> dict:
    params = _params(t.event_params)
    if params.get("condition"):
        return ensure_h5_gate(params["condition"])
    return legacy_to_condition(t.event_type or "", params)


def _rule_when(t: MktCouponTrigger, params: Optional[dict] = None) -> str:
    """daily | event:NEW_WECHAT_MEMBER"""
    params = params if params is not None else _params(t.event_params)
    if params.get("when"):
        return str(params["when"])
    et = (t.event_type or "").upper()
    if et == "NEW_WECHAT_MEMBER":
        return "event:NEW_WECHAT_MEMBER"
    if et in ("REG_DAYS", "CHECKOUT_DAYS", "DAILY", "RULE_ENGINE"):
        return "daily"
    if et.startswith("EVENT:"):
        return et.lower() if False else f"event:{et}"
    return "daily"


TEMPLATES = [
    {
        "key": "new_member_discount",
        "scene": "新用户",
        "name": "新客欢迎礼 · 房价7折",
        "when": "event:NEW_WECHAT_MEMBER",
        "condition": {
            "all": [
                {"field": "h5_scanned", "op": "eq", "value": True},
                {"field": "wecom_bound", "op": "eq", "value": True},
            ]
        },
        "hint": "加企微成功后立刻发欢迎礼",
    },
    {
        "key": "reg_30_cash10",
        "scene": "新用户",
        "name": "注册满30天 · 立减¥10",
        "when": "daily",
        "condition": {
            "all": [
                {"field": "h5_scanned", "op": "eq", "value": True},
                {"field": "reg_days", "op": "eq", "value": 30},
            ]
        },
        "hint": "注册刚好满 30 天时自动发",
    },
    {
        "key": "reg_100_cash20",
        "scene": "新用户",
        "name": "注册满100天 · 立减¥20",
        "when": "daily",
        "condition": {
            "all": [
                {"field": "h5_scanned", "op": "eq", "value": True},
                {"field": "reg_days", "op": "eq", "value": 100},
            ]
        },
        "hint": "注册刚好满 100 天时自动发",
    },
    {
        "key": "checkout_7_reduce",
        "scene": "复购",
        "name": "退房后7天 · 满减券",
        "when": "daily",
        "condition": {
            "all": [
                {"field": "h5_scanned", "op": "eq", "value": True},
                {"field": "days_since_checkout", "op": "eq", "value": 7},
            ]
        },
        "hint": "退房满 7 天时召回复购",
    },
]


def rule_to_dict(db: Session, t: MktCouponTrigger) -> dict:
    params = _params(t.event_params)
    condition = _rule_condition(t)
    when = _rule_when(t, params)
    batch = db.get(MktCoupon, t.batch_id)
    granted_log = db.query(MktCouponGrantLog).filter_by(trigger_id=t.id).count()
    # 兼容旧 days 展示
    days = None
    for node in condition.get("all") or []:
        if isinstance(node, dict) and node.get("field") in ("reg_days", "days_since_checkout"):
            days = node.get("value")
    return {
        "id": t.id,
        "name": t.name or condition_to_text(condition),
        "scene": SCENE_LABELS.get(t.event_type) or SCENE_LABELS["RULE_ENGINE"],
        "event_type": t.event_type,
        "when": when,
        "condition": condition,
        "condition_text": condition_to_text(condition),
        "event_params": params,
        "days": days,
        "batch_id": t.batch_id,
        "batch_no": batch.batch_no if batch else None,
        "batch_name": batch.name if batch else None,
        "face_text": getattr(batch, "face_text", None) if batch else None,
        "is_enabled": bool(t.is_enabled),
        "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
        "granted_total": int(t.granted_total or 0) or granted_log,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "h5_gate": True,
    }


def list_templates() -> list[dict]:
    return [{**t, "condition": ensure_h5_gate(t.get("condition"))} for t in TEMPLATES]


def list_rules(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(MktCouponTrigger).filter_by(property_id=hotel_id).order_by(MktCouponTrigger.id.desc()).all()
    return [rule_to_dict(db, r) for r in rows]


def upsert_rule(db: Session, hotel_id: int, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    batch_id = int(payload.get("batch_id") or payload.get("coupon_id") or 0)
    if not name:
        raise InvalidStateError("请填写规则名称")
    batch = db.query(MktCoupon).filter_by(id=batch_id, hotel_id=hotel_id).first()
    if not batch:
        raise NotFoundError("关联券批次不存在")
    if batch.status != "active":
        raise InvalidStateError("请选择 status=active 的券批次")

    when = str(payload.get("when") or "").strip() or "daily"
    event_type = str(payload.get("event_type") or "").strip().upper()

    # 优先用 condition；否则从旧字段拼
    if payload.get("condition"):
        condition = ensure_h5_gate(payload.get("condition"))
    elif event_type in ("REG_DAYS", "CHECKOUT_DAYS", "NEW_WECHAT_MEMBER"):
        days = payload.get("days")
        params_legacy = {}
        if event_type == "REG_DAYS":
            params_legacy["reg_days"] = int(days or 30)
            when = "daily"
        elif event_type == "CHECKOUT_DAYS":
            params_legacy["days_after_checkout"] = int(days or 7)
            when = "daily"
        elif event_type == "NEW_WECHAT_MEMBER":
            when = "event:NEW_WECHAT_MEMBER"
        condition = legacy_to_condition(event_type, params_legacy)
    else:
        condition = ensure_h5_gate(payload.get("condition") or {"all": []})

    # 从 when 推导 event_type 存储
    if when.startswith("event:"):
        event_type = when.split(":", 1)[1].upper() or "CUSTOM"
    elif event_type not in (
        "NEW_WECHAT_MEMBER",
        "REG_DAYS",
        "CHECKOUT_DAYS",
        "RULE_ENGINE",
        "DAILY",
        "CUSTOM",
    ):
        event_type = "RULE_ENGINE"

    # 校验：条件里必须能解析且含 H5（ensure 已注入）
    if not any(
        isinstance(n, dict) and n.get("field") == "h5_scanned" and n.get("value") is True
        for n in (condition.get("all") or [])
    ):
        raise InvalidStateError("规则受众须为已加企微的客人")

    params = {
        "when": when,
        "condition": condition,
    }

    row = None
    if payload.get("id"):
        row = db.query(MktCouponTrigger).filter_by(id=int(payload["id"]), property_id=hotel_id).first()
        if not row:
            raise NotFoundError("规则不存在")
    if not row:
        row = MktCouponTrigger(property_id=hotel_id)
        db.add(row)

    row.name = name[:128]
    row.batch_id = batch_id
    row.event_type = event_type
    row.event_params = json.dumps(params, ensure_ascii=False)
    if "is_enabled" in payload:
        row.is_enabled = 1 if payload.get("is_enabled") else 0
    elif getattr(row, "id", None) is None:
        row.is_enabled = 1 if payload.get("is_enabled", True) else 0

    db.commit()
    db.refresh(row)
    return rule_to_dict(db, row)


def set_rule_enabled(db: Session, hotel_id: int, rule_id: int, enabled: bool) -> dict:
    row = db.query(MktCouponTrigger).filter_by(id=rule_id, property_id=hotel_id).first()
    if not row:
        raise NotFoundError("规则不存在")
    row.is_enabled = 1 if enabled else 0
    db.commit()
    return rule_to_dict(db, row)


def delete_rule(db: Session, hotel_id: int, rule_id: int) -> dict:
    row = db.query(MktCouponTrigger).filter_by(id=rule_id, property_id=hotel_id).first()
    if not row:
        raise NotFoundError("规则不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


def preview_audience(db: Session, hotel_id: int, payload: dict) -> dict:
    """预览命中人数：传 rule_id 或 condition。"""
    today = None
    if payload.get("today"):
        try:
            today = date.fromisoformat(str(payload["today"])[:10])
        except Exception:
            today = None
    if payload.get("rule_id"):
        t = db.query(MktCouponTrigger).filter_by(id=int(payload["rule_id"]), property_id=hotel_id).first()
        if not t:
            raise NotFoundError("规则不存在")
        condition = _rule_condition(t)
    else:
        condition = ensure_h5_gate(payload.get("condition") or {"all": []})
    result = match_guests(db, hotel_id, condition, today=today)
    result["h5_required"] = True
    return result


def _issue_for_guest(db: Session, trigger: MktCouponTrigger, guest_id: int) -> Optional[str]:
    from mkt.mkt_coupon_engine import issue_instance

    # 硬门禁：非 H5 扫码建联绝不发
    if not is_channel_bound(db, trigger.property_id, guest_id):
        return None

    coupon = db.get(MktCoupon, trigger.batch_id)
    if not coupon or coupon.status != "active":
        return None
    if (
        db.query(MktCouponGrantLog)
        .filter_by(trigger_id=trigger.id, customer_id=guest_id, batch_id=trigger.batch_id)
        .first()
    ):
        return None
    try:
        inst = issue_instance(
            db,
            coupon,
            guest_id,
            grant_event=trigger.event_type or "RULE_ENGINE",
            grant_channel="trigger",
            auto_claim=True,
            trigger_id=trigger.id,
        )
        trigger.granted_total = int(trigger.granted_total or 0) + 1
        return inst.code
    except HTTPException:
        return None


def run_rule_scan(
    db: Session,
    hotel_id: int,
    *,
    rule_id: Optional[int] = None,
    today: Optional[date] = None,
) -> dict:
    """日扫：对 when=daily 的规则用条件引擎求值后发放。"""
    today = today or date.today()
    q = db.query(MktCouponTrigger).filter_by(property_id=hotel_id, is_enabled=1)
    if rule_id:
        q = q.filter_by(id=rule_id)
    rules = q.all()
    summary = []
    total_granted = 0
    for t in rules:
        when = _rule_when(t)
        if when.startswith("event:"):
            summary.append(
                {
                    "rule_id": t.id,
                    "name": t.name,
                    "when": when,
                    "matched": 0,
                    "granted": 0,
                    "note": "事件触发规则，由建联回调执行，不参与日扫",
                }
            )
            t.last_run_at = datetime.now()
            continue

        condition = _rule_condition(t)
        matched = match_guests(db, hotel_id, condition, today=today)
        codes = []
        for gid in matched["guest_ids"]:
            code = _issue_for_guest(db, t, gid)
            if code:
                codes.append(code)
        t.last_run_at = datetime.now()
        total_granted += len(codes)
        summary.append(
            {
                "rule_id": t.id,
                "name": t.name,
                "when": when,
                "condition_text": matched["condition_text"],
                "matched": matched["matched"],
                "granted": len(codes),
                "codes": codes[:20],
                "samples": matched["samples"][:5],
            }
        )
    db.commit()
    return {
        "ok": True,
        "today": today.isoformat(),
        "granted": total_granted,
        "rules": summary,
    }


def try_run_for_guest(db: Session, hotel_id: int, rule_id: int, guest_id: int) -> dict:
    """试跑：对指定客人求值；未命中则说明原因；命中则发券。"""
    t = db.query(MktCouponTrigger).filter_by(id=rule_id, property_id=hotel_id).first()
    if not t:
        raise NotFoundError("规则不存在")
    if not t.is_enabled:
        raise InvalidStateError("规则未启用")
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")

    condition = _rule_condition(t)
    ctx = build_guest_context(db, hotel_id, guest)
    ok, reasons = eval_condition(condition, ctx)
    if not ok:
        return {
            "ok": False,
            "matched": False,
            "reason": "；".join(reasons) or "条件未命中",
            "reasons": reasons,
            "context": ctx,
            "condition_text": condition_to_text(condition),
            "rule_id": rule_id,
            "guest_id": guest_id,
        }

    code = _issue_for_guest(db, t, guest_id)
    t.last_run_at = datetime.now()
    db.commit()
    if not code:
        return {
            "ok": False,
            "matched": True,
            "reason": "条件已命中，但未发放（可能已发过或库存不足）",
            "context": ctx,
            "rule_id": rule_id,
            "guest_id": guest_id,
        }
    return {
        "ok": True,
        "matched": True,
        "code": code,
        "context": ctx,
        "condition_text": condition_to_text(condition),
        "rule_id": rule_id,
        "guest_id": guest_id,
    }


def fire_event_rules(db: Session, hotel_id: int, event_key: str, guest_id: int) -> dict:
    """事件总线：建联等 → 匹配 when=event:XXX 且条件命中的规则。"""
    event_key = str(event_key or "").strip().upper()
    when_need = f"event:{event_key}"
    if not is_channel_bound(db, hotel_id, guest_id):
        return {"event": event_key, "granted": 0, "skipped": "not_h5_scanned", "instances": []}

    guest = db.get(Guest, guest_id)
    if not guest:
        return {"event": event_key, "granted": 0, "skipped": "no_guest", "instances": []}

    ctx = build_guest_context(db, hotel_id, guest)
    granted = []
    for t in db.query(MktCouponTrigger).filter_by(property_id=hotel_id, is_enabled=1).all():
        if _rule_when(t) != when_need and (t.event_type or "").upper() != event_key:
            continue
        ok, _ = eval_condition(_rule_condition(t), ctx)
        if not ok:
            continue
        code = _issue_for_guest(db, t, guest_id)
        if code:
            granted.append({"rule_id": t.id, "name": t.name, "code": code})
    db.commit()
    return {"event": event_key, "granted": len(granted), "instances": granted}


def run_all_hotels_scan(db: Session) -> dict:
    from models import Hotel

    hotels = db.query(Hotel.id).all()
    out = []
    for (hid,) in hotels:
        out.append({"hotel_id": hid, **run_rule_scan(db, hid)})
    return {"ok": True, "hotels": out}
