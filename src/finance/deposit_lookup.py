# SPDX-License-Identifier: Apache-2.0
"""押金查找：电话 / 客人 / 房号（从 deposit_service 绞杀抽出）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from finance.deposit_common import (
    VALID_ORDER_STATUSES,
    _digits,
    _mask_guest_name,
    _serialize_order_for_collect,
    credit_preview,
)
from models import Deposit, Guest, Order, PmsCheckin


def lookup_by_phone(db: Session, hotel_id: int, phone: str) -> dict[str, Any]:
    """
    收押主路径：手机号 → 定位客户(OneID) → 有效订单列表。
    输入满 3 位起匹配；满 11 位精确优先。
    """
    from datetime import date

    from guests.phone_utils import find_guests_by_phone_exact
    from infra.id_doc_crypto import hash_phone, mask_phone

    digits = _digits(phone)
    if len(digits) < 3:
        return {
            "matched": False,
            "need_more": True,
            "hint": "请继续输入预订手机号（满 3 位开始关联）",
            "guest": None,
            "candidates": [],
            "orders": [],
            "order_count": 0,
        }

    guest_ids: set[int] = set()
    guests_map: dict[int, Guest] = {}

    def _remember(g: Guest | None) -> None:
        if g and g.id:
            guest_ids.add(g.id)
            guests_map[g.id] = g

    # 1) 精确：完整号 / 较长号 → hash / wecom
    if len(digits) >= 8:
        for g in find_guests_by_phone_exact(db, digits):
            _remember(g)
        ph = hash_phone(digits, hotel_id)
        if ph:
            for g in db.query(Guest).filter(Guest.phone_hash == ph).limit(20).all():
                _remember(g)

    # 2) 本酒店订单 guest_phone 反查（主路径，避免全表扫 Guest）
    order_q = (
        db.query(Order)
        .filter(Order.hotel_id == hotel_id, Order.guest_phone.isnot(None))
        .order_by(Order.id.desc())
        .limit(3000)
    )
    for o in order_q.all():
        raw = str(o.guest_phone or "")
        op = _digits(raw)
        hit = False
        if op and (op.startswith(digits) or digits.startswith(op)):
            hit = True
        elif "*" in raw and len(digits) >= 3:
            head = raw.split("*")[0]
            if head and digits.startswith(head):
                hit = True
            if len(digits) == 11 and head == digits[:3]:
                tail = raw.split("*")[-1]
                if tail and digits.endswith(tail):
                    hit = True
        if hit and o.guest_id:
            if o.guest_id not in guests_map:
                _remember(db.get(Guest, o.guest_id))
            else:
                guest_ids.add(o.guest_id)

    # 3) 短号补充：仅按 phone_mask 前缀查少量 Guest（脱敏号形如 197****5241）
    if len(digits) <= 7 and len(guest_ids) < 8:
        like_prefix = f"{digits[:3]}%"
        for g in db.query(Guest).filter(Guest.phone_mask.like(like_prefix)).limit(40).all():
            mask = str(g.phone_mask or "")
            if mask.startswith(digits[:3]):
                if len(digits) == 11 and "*" in mask:
                    head, _, tail = mask.partition("****")
                    if head == digits[:3] and tail and digits.endswith(tail[-4:]):
                        _remember(g)
                elif len(digits) < 11:
                    _remember(g)

    if not guest_ids:
        return {
            "matched": False,
            "need_more": len(digits) < 11,
            "hint": "未找到该手机号关联客人" if len(digits) >= 11 else "继续输入以缩小匹配…",
            "guest": None,
            "candidates": [],
            "orders": [],
            "order_count": 0,
            "phone_mask": mask_phone(digits) if len(digits) >= 7 else None,
        }

    # 多候选：满号优先唯一；否则返回候选人列表
    candidates = []
    for gid in list(guest_ids)[:8]:
        g = guests_map.get(gid) or db.get(Guest, gid)
        if not g:
            continue
        candidates.append(
            {
                "guest_id": g.id,
                "one_id": g.one_id,
                "name": g.name,
                "name_masked": _mask_guest_name(g.name),
                "phone_mask": g.phone_mask or mask_phone(g.phone) or "—",
                "vip_level": g.vip_level,
            }
        )

    primary: Guest | None = None
    if len(candidates) == 1:
        primary = guests_map.get(candidates[0]["guest_id"])
    elif len(digits) >= 11 and candidates:
        # 多命中时优先脱敏尾号完全吻合者
        for c in candidates:
            pm = str(c.get("phone_mask") or "")
            if "*" in pm:
                head, _, tail = pm.partition("****")
                if head == digits[:3] and tail and digits.endswith(tail[-4:]):
                    primary = guests_map.get(c["guest_id"])
                    break
        if not primary:
            primary = guests_map.get(candidates[0]["guest_id"])

    if not primary:
        return {
            "matched": False,
            "need_more": False,
            "hint": "匹配到多位客人，请继续输入完整手机号或口头核验后选择",
            "guest": None,
            "candidates": candidates,
            "orders": [],
            "order_count": 0,
        }

    preview = credit_preview(db, hotel_id=hotel_id, guest_id=primary.id, nights=1)
    guest_card = {
        "guest_id": primary.id,
        "one_id": primary.one_id,
        "name": primary.name,
        "name_masked": _mask_guest_name(primary.name),
        "phone_mask": primary.phone_mask or mask_phone(primary.phone) or mask_phone(digits),
        "vip_level": primary.vip_level or "normal",
        "credit_score": preview.get("credit_score"),
        "risk_tags": preview.get("risk_tags") or [],
        "stay_frequency": preview.get("stay_frequency") or 0,
        "preview": preview,
        "confirm_hint": f"口头核验：您是{_mask_guest_name(primary.name).replace('**', '')}先生/女士吗？",
    }

    today = date.today()
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.guest_id == primary.id,
            Order.status.in_(list(VALID_ORDER_STATUSES)),
        )
        .order_by(Order.check_in.desc(), Order.id.desc())
        .limit(40)
        .all()
    )
    # 排除已结历史：checkout 早于今天且非在住
    valid_rows = []
    for o in orders:
        if o.status == "checked_in":
            valid_rows.append(_serialize_order_for_collect(db, hotel_id, o))
            continue
        if o.check_out and o.check_out < today:
            continue
        valid_rows.append(_serialize_order_for_collect(db, hotel_id, o))
        if len(valid_rows) >= 15:
            break

    auto_select = valid_rows[0]["order_id"] if len(valid_rows) == 1 else None
    return {
        "matched": True,
        "need_more": False,
        "hint": None,
        "guest": guest_card,
        "candidates": candidates if len(candidates) > 1 else [],
        "orders": valid_rows,
        "order_count": len(valid_rows),
        "auto_select_order_id": auto_select,
        "empty_action": None
        if valid_rows
        else {
            "message": "该手机号下暂无有效订单（已确认/待入住/在住）",
            "actions": [
                {"label": "+ 新建预订", "path": "/orders"},
                {"label": "查看历史客档", "path": "/b-data/global-guest-directory"},
            ],
        },
    }


def lookup_by_guest(db: Session, hotel_id: int, guest_id: int) -> dict[str, Any]:
    """候选人点选：直接按 guest_id 拉 360 + 有效订单。"""
    from datetime import date

    from infra.id_doc_crypto import mask_phone

    primary = db.get(Guest, guest_id)
    if not primary:
        return {"matched": False, "hint": "客人不存在", "guest": None, "orders": [], "order_count": 0}

    preview = credit_preview(db, hotel_id=hotel_id, guest_id=primary.id, nights=1)
    guest_card = {
        "guest_id": primary.id,
        "one_id": primary.one_id,
        "name": primary.name,
        "name_masked": _mask_guest_name(primary.name),
        "phone_mask": primary.phone_mask or mask_phone(primary.phone) or "—",
        "vip_level": primary.vip_level or "normal",
        "credit_score": preview.get("credit_score"),
        "risk_tags": preview.get("risk_tags") or [],
        "stay_frequency": preview.get("stay_frequency") or 0,
        "preview": preview,
        "confirm_hint": f"口头核验：您是{_mask_guest_name(primary.name).replace('**', '')}先生/女士吗？",
    }
    today = date.today()
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.guest_id == primary.id,
            Order.status.in_(list(VALID_ORDER_STATUSES)),
        )
        .order_by(Order.check_in.desc(), Order.id.desc())
        .limit(40)
        .all()
    )
    valid_rows = []
    for o in orders:
        if o.status == "checked_in":
            valid_rows.append(_serialize_order_for_collect(db, hotel_id, o))
            continue
        if o.check_out and o.check_out < today:
            continue
        valid_rows.append(_serialize_order_for_collect(db, hotel_id, o))
        if len(valid_rows) >= 15:
            break
    auto_select = valid_rows[0]["order_id"] if len(valid_rows) == 1 else None
    return {
        "matched": True,
        "guest": guest_card,
        "candidates": [],
        "orders": valid_rows,
        "order_count": len(valid_rows),
        "auto_select_order_id": auto_select,
        "empty_action": None
        if valid_rows
        else {
            "message": "该客人暂无有效订单（已确认/待入住/在住）",
            "actions": [
                {"label": "+ 新建预订", "path": "/orders"},
                {"label": "查看历史客档", "path": "/b-data/global-guest-directory"},
            ],
        },
    }


def lookup_by_room(db: Session, hotel_id: int, room_no: str) -> dict[str, Any]:
    """边角：房号快捷入口。"""
    rn = (room_no or "").strip()
    if not rn:
        return {"matched": False, "orders": [], "guest": None}
    ck = (
        db.query(PmsCheckin)
        .filter(PmsCheckin.hotel_id == hotel_id, PmsCheckin.room_no == rn, PmsCheckin.status == "inhouse")
        .order_by(PmsCheckin.id.desc())
        .first()
    )
    if not ck or not ck.order_id:
        return {"matched": False, "hint": f"未找到房号 {rn} 的在住单", "orders": [], "guest": None}
    o = db.get(Order, ck.order_id)
    if not o:
        return {"matched": False, "orders": [], "guest": None}
    g = db.get(Guest, o.guest_id) if o.guest_id else None
    phone = o.guest_phone or (g.phone if g else "") or ""
    # 尽量走手机主路径
    dig = _digits(phone)
    if len(dig) >= 8:
        return lookup_by_phone(db, hotel_id, dig)
    row = _serialize_order_for_collect(db, hotel_id, o)
    preview = row.get("preview") or {}
    guest_card = {
        "guest_id": o.guest_id,
        "one_id": g.one_id if g else None,
        "name": g.name if g else ck.guest_name,
        "name_masked": _mask_guest_name(g.name if g else ck.guest_name),
        "phone_mask": (g.phone_mask if g else None) or "—",
        "vip_level": (g.vip_level if g else None) or "normal",
        "credit_score": preview.get("credit_score"),
        "risk_tags": preview.get("risk_tags") or [],
        "stay_frequency": preview.get("stay_frequency") or 0,
        "preview": preview,
    }
    return {
        "matched": True,
        "guest": guest_card,
        "orders": [row],
        "order_count": 1,
        "auto_select_order_id": row["order_id"],
        "via": "room_no",
    }
