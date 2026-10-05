# SPDX-License-Identifier: Apache-2.0
"""券批次 CRUD 与模板。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from mkt._mkt_utils import _dt, _jdumps
from models import MktCoupon, MktCouponGrant

COUPON_TYPES = ("CASH_ROOM", "CASH_ALL", "DISCOUNT", "BENEFIT")
# 旧类型仍可写入，创建时归一化
COUPON_TYPES_LEGACY = ("discount", "reduction", "night_up", "room_up", "time_window")
COUPON_STATUSES = ("draft", "active", "paused", "expired")


def _coupon_label(c: MktCoupon) -> str:
    from mkt.mkt_coupon_engine import resolve_batch_benefit_fields

    return resolve_batch_benefit_fields(c)["face_text"]


def _next_coupon_batch_no(db: Session) -> str:
    ymd = datetime.now().strftime("%Y%m%d")
    prefix = f"COUPON-{ymd}-"
    rows = db.query(MktCoupon.batch_no).filter(MktCoupon.batch_no.like(f"{prefix}%")).all()
    seq = 1
    for (bno,) in rows:
        try:
            seq = max(seq, int(str(bno).split("-")[-1]) + 1)
        except Exception:
            pass
    return f"{prefix}{seq:03d}"


def coupon_to_dict(c: MktCoupon, db: Optional[Session] = None) -> dict:
    from mkt.mkt_coupon_engine import batch_to_dict

    return batch_to_dict(c, db)


def list_coupons(db: Session, hotel_id: int, status: Optional[str] = None) -> list[dict]:
    q = db.query(MktCoupon).filter_by(hotel_id=hotel_id)
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(MktCoupon.id.desc()).all()
    return [coupon_to_dict(c, db) for c in rows]


def create_coupon(db: Session, hotel_id: int, payload: dict) -> dict:
    from mkt.mkt_coupon_engine import (
        build_face_text,
        normalize_coupon_type,
    )

    raw_type = str(payload.get("coupon_type") or payload.get("type") or "DISCOUNT")
    threshold = float(payload.get("threshold") or 0)
    typ = normalize_coupon_type(raw_type, threshold=threshold)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise InvalidStateError('"请填写券名称"')
    batch = str(payload.get("batch_no") or "").strip()
    if not batch:
        batch = _next_coupon_batch_no(db)
    if db.query(MktCoupon).filter_by(batch_no=batch).first():
        raise InvalidStateError('"批次号已存在"')
    status = str(payload.get("status") or "draft")
    if status not in COUPON_STATUSES:
        status = "draft"

    scope = dict(payload.get("scope") or payload.get("scope_json") or {})
    scope_rooms = payload.get("scope_rooms") or scope.get("rooms") or []
    if isinstance(scope_rooms, str):
        scope_rooms = [scope_rooms]
    scope_type = str(payload.get("scope_type") or ("ROOM_SPECIFIED" if typ == "CASH_ROOM" else "ALL"))
    if typ == "CASH_ROOM" and not scope_rooms:
        raise InvalidStateError('"CASH_ROOM 必须指定 scope_rooms"')
    if typ == "CASH_ALL":
        threshold = 0
        scope_type = "ALL"

    reduce_amount = payload.get("reduce_amount")
    discount_rate = payload.get("discount_rate")
    max_discount = payload.get("max_discount")
    benefit_key = payload.get("benefit_key")
    benefit_value = payload.get("benefit_value")
    face_value = payload.get("face_value")

    if typ in ("CASH_ROOM", "CASH_ALL"):
        if reduce_amount is None or reduce_amount == "":
            reduce_amount = face_value
        if reduce_amount is None or float(reduce_amount) <= 0:
            raise InvalidStateError('f"{typ} 必须填写 reduce_amount（减免金额）"')
        reduce_amount = float(reduce_amount)
        face_value = reduce_amount
    elif typ == "DISCOUNT":
        if discount_rate is None or discount_rate == "":
            discount_rate = face_value
        discount_rate = float(discount_rate or 0)
        if not (0.01 <= discount_rate <= 1.0):
            raise InvalidStateError('"DISCOUNT.discount_rate 须在 0.01~1.00"')
        face_value = discount_rate
        if max_discount is not None and max_discount != "":
            max_discount = float(max_discount)
        else:
            max_discount = None
    else:  # BENEFIT
        benefit_key = str(benefit_key or "CUSTOM").upper()
        if benefit_key not in ("BREAKFAST", "LATE_CHECKOUT", "ROOM_UPGRADE", "FREE_NIGHT", "CUSTOM"):
            benefit_key = "CUSTOM"
        benefit_value = str(benefit_value or payload.get("face_text") or "").strip() or None
        if not benefit_value and not payload.get("face_text"):
            raise InvalidStateError('"BENEFIT 须填写 benefit_key / benefit_value 或 face_text"')
        face_value = float(face_value or 0)

    face_text = build_face_text(
        typ,
        reduce_amount=float(reduce_amount) if reduce_amount is not None else None,
        threshold=threshold,
        discount_rate=float(discount_rate) if discount_rate is not None else None,
        max_discount=float(max_discount) if max_discount is not None else None,
        benefit_key=benefit_key,
        benefit_value=benefit_value,
        face_text=str(payload.get("face_text") or "").strip() or None,
    )
    scope["face_text"] = face_text
    if scope_rooms:
        scope["rooms"] = list(scope_rooms)

    validity_mode = str(payload.get("validity_mode") or "FIXED").upper()
    if validity_mode not in ("FIXED", "RELATIVE"):
        validity_mode = "FIXED"
    validity_days = payload.get("validity_days")
    vf = _dt(payload.get("batch_valid_from") or payload.get("valid_from"))
    vt = _dt(payload.get("batch_valid_to") or payload.get("valid_to"))
    if validity_mode == "FIXED":
        if not vf or not vt:
            raise InvalidStateError('"FIXED 模式必须设置 valid_from / valid_to"')
        if vt <= vf:
            raise InvalidStateError('"valid_to 必须晚于 valid_from"')
    else:
        validity_days = int(validity_days or 0)
        if validity_days <= 0:
            raise InvalidStateError('"RELATIVE 模式必须设置 validity_days>0"')
        # 批次模板仍可空；实例领取时写入。为满足列表展示，用占位窗口
        if not vf:
            vf = datetime.now()
        if not vt:
            vt = vf + timedelta(days=validity_days)

    row = MktCoupon(
        hotel_id=hotel_id,
        batch_no=batch,
        name=name,
        type=typ,
        coupon_type=typ,
        face_value=float(face_value or 0),
        reduce_amount=float(reduce_amount) if reduce_amount is not None else None,
        threshold=threshold,
        discount_rate=float(discount_rate) if discount_rate is not None else None,
        max_discount=float(max_discount) if max_discount is not None else None,
        benefit_key=benefit_key,
        benefit_value=benefit_value,
        face_text=face_text,
        scope_type=scope_type,
        scope_rooms=_jdumps(scope_rooms) if scope_rooms else None,
        total_qty=int(payload.get("total_qty") or 1000),
        granted_qty=0,
        per_user_qty=int(payload.get("per_user_qty") or 1),
        validity_mode=validity_mode,
        validity_days=int(validity_days) if validity_days else None,
        batch_valid_from=vf,
        batch_valid_to=vt,
        valid_from=vf,
        valid_to=vt,
        scope_json=_jdumps(scope),
        status=status,
        created_by=str(payload.get("created_by") or "")[:32] or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return coupon_to_dict(row, db)


def update_coupon_batch(db: Session, hotel_id: int, coupon_id: int, payload: dict) -> dict:
    """编辑批次：已发放后禁止改面额类字段。"""
    row = db.query(MktCoupon).filter_by(id=coupon_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"券批次不存在"')
    granted = (
        int(getattr(row, "granted_qty", None) or 0) or db.query(MktCouponGrant).filter_by(coupon_id=row.id).count()
    )
    locked = {
        "coupon_type",
        "type",
        "reduce_amount",
        "threshold",
        "discount_rate",
        "max_discount",
        "benefit_key",
        "benefit_value",
        "face_value",
    }
    payload = payload or {}
    if granted > 0:
        for k in locked:
            if k in payload and payload[k] is not None:
                raise InvalidStateError('f"已发放券不可修改字段：{k}"')
    if "name" in payload and payload["name"]:
        row.name = str(payload["name"]).strip()[:128]
    if "total_qty" in payload and payload["total_qty"] is not None:
        row.total_qty = int(payload["total_qty"])
    if "per_user_qty" in payload and payload["per_user_qty"] is not None:
        row.per_user_qty = int(payload["per_user_qty"])
    if "status" in payload and payload["status"] in COUPON_STATUSES:
        row.status = payload["status"]
    if granted == 0:
        # 允许改面额等（未发放）
        for attr in (
            "reduce_amount",
            "threshold",
            "discount_rate",
            "max_discount",
            "benefit_key",
            "benefit_value",
            "face_text",
            "validity_mode",
            "validity_days",
            "scope_type",
        ):
            if attr in payload and payload[attr] is not None:
                setattr(row, attr, payload[attr])
        if "valid_from" in payload or "batch_valid_from" in payload:
            vf = _dt(payload.get("batch_valid_from") or payload.get("valid_from"))
            if vf:
                row.batch_valid_from = vf
                row.valid_from = vf
        if "valid_to" in payload or "batch_valid_to" in payload:
            vt = _dt(payload.get("batch_valid_to") or payload.get("valid_to"))
            if vt:
                row.batch_valid_to = vt
                row.valid_to = vt
    db.commit()
    db.refresh(row)
    return coupon_to_dict(row, db)


def update_coupon_status(db: Session, hotel_id: int, coupon_id: int, status: str) -> dict:
    row = db.query(MktCoupon).filter_by(id=coupon_id, hotel_id=hotel_id).first()
    if not row:
        raise NotFoundError('"券批次不存在"')
    if status not in COUPON_STATUSES:
        raise InvalidStateError('"状态无效"')
    row.status = status
    db.commit()
    return coupon_to_dict(row, db)


COUPON_TEMPLATES = [
    {
        "id": "new_guest_70",
        "name": "新客首单 7 折",
        "type": "DISCOUNT",
        "coupon_type": "DISCOUNT",
        "ico": "💸",
        "desc": "拉新专用，限新客，有效期 90 天。",
        "defaults": {"discount_rate": 0.7, "face_value": 0.7, "total_qty": 500, "per_user_qty": 1},
    },
    {
        "id": "reduce_500_120",
        "name": "豪华房立减 ¥120（满 500）",
        "type": "CASH_ROOM",
        "coupon_type": "CASH_ROOM",
        "ico": "💰",
        "desc": "指定房型满减。",
        "defaults": {
            "reduce_amount": 120,
            "face_value": 120,
            "threshold": 500,
            "total_qty": 300,
            "scope_type": "ROOM_SPECIFIED",
        },
    },
    {
        "id": "cash_all_50",
        "name": "通用立减 ¥50（无门槛）",
        "type": "CASH_ALL",
        "coupon_type": "CASH_ALL",
        "ico": "🪙",
        "desc": "全房型无门槛立减。",
        "defaults": {"reduce_amount": 50, "face_value": 50, "threshold": 0, "total_qty": 500},
    },
    {
        "id": "breakfast",
        "name": "免费双早",
        "type": "BENEFIT",
        "coupon_type": "BENEFIT",
        "ico": "🍳",
        "desc": "权益券 · 早餐。",
        "defaults": {"benefit_key": "BREAKFAST", "benefit_value": "双早", "face_text": "免费双早", "total_qty": 200},
    },
    {
        "id": "late_checkout",
        "name": "延迟退房至 14:00",
        "type": "BENEFIT",
        "coupon_type": "BENEFIT",
        "ico": "⏰",
        "desc": "权益券 · 延迟退房。",
        "defaults": {
            "benefit_key": "LATE_CHECKOUT",
            "benefit_value": "14:00",
            "face_text": "延迟退房至 14:00",
            "total_qty": 200,
        },
    },
    {
        "id": "birthday_80",
        "name": "生日月 8 折",
        "type": "DISCOUNT",
        "coupon_type": "DISCOUNT",
        "ico": "🎂",
        "desc": "事件触发 · 生日。",
        "defaults": {"discount_rate": 0.8, "face_value": 0.8, "total_qty": 1000},
    },
]


def list_coupon_templates() -> list[dict]:
    from copy import deepcopy

    from infra.i18n import t as _t

    out = []
    for row in COUPON_TEMPLATES:
        item = deepcopy(row)
        if item.get("name"):
            item["name"] = _t(str(item["name"]))
        if item.get("desc"):
            item["desc"] = _t(str(item["desc"]))
        out.append(item)
    return out
