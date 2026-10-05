# SPDX-License-Identifier: Apache-2.0
"""orders.order_service 子模块 — auto-split by AST.

本文件由 src/orders/order_service.py 按业务子域拆分而成。
外部调用 `from orders.order_service import xxx` 仍兼容（见 __init__.py）。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
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
from models import (
    Channel,
    CorpAccount,
    Guest,
    Invoice,
    LedgerEntry,
    Order,
    OrderItem,
    Payment,
    PmsGroupRoomBlock,
    PmsGroupRoomLine,
    Reservation,
    Room,
    RoomStatusLog,
    RoomType,
)
from orders.channel_config import source_group_for
from orders.pms_domain import (
    apply_order_domain_defaults,
    close_checkin,
    folio_snapshot,
    open_checkin_and_folio,
    post_ar_charge,
    post_payment,
)

VOUCHER_CHANNEL_CODES = {"douyin", "meituan_voucher"}

OTA_CHANNEL_CODES = frozenset({"ota", "ctrip", "meituan", "fliggy"})


def detect_voucher_platform(code: str) -> tuple[str, str]:
    u = (code or "").upper()
    if u.startswith("MT") or "MEITUAN" in u:
        return ("meituan_voucher", "美团团购")
    return ("douyin", "抖音团购")


def _voucher_package_extras(rt: Optional[RoomType]) -> list[str]:
    extras: list[str] = []
    if not rt:
        return extras
    if rt.breakfast_included:
        extras.append("含早餐")
    raw = (rt.amenities or "").strip()
    if raw:
        try:
            import json

            items = json.loads(raw) if raw.startswith("[") else [x.strip() for x in raw.split(",") if x.strip()]
            for it in items:
                s = str(it).strip()
                if s and s not in extras:
                    extras.append(s)
        except Exception:
            pass
    if rt.bed_type:
        extras.append(f"{rt.bed_type}")
    return extras[:6]


def lookup_voucher(db: Session, hotel_id: int, code: str) -> dict:
    code = (code or "").strip()
    if len(code) < 4:
        raise InvalidStateError("券码格式无效")
    if db.query(Order).filter_by(voucher_code=code).first():
        raise ConflictError("该券码已核销")
    ch_code, platform = detect_voucher_platform(code)
    ch = db.query(Channel).filter_by(code=ch_code).first()
    rt = db.query(RoomType).filter_by(hotel_id=hotel_id, is_active=True).order_by(RoomType.base_price.asc()).first()
    vacant_q = db.query(Room).filter(Room.hotel_id == hotel_id, Room.status.in_(["vacant", "clean", "inspected"]))
    vacant_total = vacant_q.count()
    vacant_type = vacant_q.filter(Room.room_type_id == rt.id).count() if rt else vacant_total
    sample = (
        db.query(Room)
        .filter(Room.hotel_id == hotel_id, Room.status.in_(["vacant", "clean", "inspected"]))
        .order_by(Room.floor.asc(), Room.room_no.asc())
        .first()
    )
    if rt:
        sample = (
            db.query(Room)
            .filter(
                Room.hotel_id == hotel_id,
                Room.room_type_id == rt.id,
                Room.status.in_(["VC", "vacant", "clean", "inspected"]),
            )
            .order_by(Room.floor.asc(), Room.room_no.asc())
            .first()
            or sample
        )
    return {
        "valid": True,
        "voucher_code": code,
        "platform": platform,
        "channel_code": ch_code,
        "channel_id": ch.id if ch else None,
        "room_type_id": rt.id if rt else None,
        "room_type_name": rt.name if rt else "标准房",
        "face_value": float(rt.base_price or 0) if rt else 0,
        "nights": 1,
        "extras": _voucher_package_extras(rt),
        "vacant_rooms": vacant_type,
        "vacant_total": vacant_total,
        "floor_tag": str(sample.floor) if sample and sample.floor is not None else "—",
        "expires_at": f"{date.today().year}-12-31",
        "rule_note": "周末及法定节假日可能需补差价",
    }


def verify_voucher_and_order(db: Session, payload: dict, created_by: Optional[int] = None) -> dict:
    code = (payload.get("voucher_code") or "").strip()
    info = lookup_voucher(db, payload["hotel_id"], code)
    ci = date.today()
    co = ci + timedelta(days=int(payload.get("nights", 1)))
    extra = float(payload.get("surcharge", 0) or 0)
    o = create_order_record(
        db,
        hotel_id=payload["hotel_id"],
        guest_name=payload.get("guest_name") or "团购客人",
        phone=payload.get("phone"),
        room_type_id=int(payload.get("room_type_id") or info["room_type_id"]),
        channel_id=int(payload.get("channel_id") or info["channel_id"] or 0) or None,
        check_in=ci,
        check_out=co,
        rooms=int(payload.get("rooms", 1)),
        note=f"团购核销 · {info['platform']} · {code}",
        voucher_code=code,
        payment_status="paid",
        extra_amount=extra,
        created_by=created_by,
    )
    room_id = payload.get("room_id")
    auto_checkin = payload.get("auto_checkin", True)
    if auto_checkin:
        checkin_order(db, o.id, room_id)
        db.refresh(o)
    return {"order": row_to_dict(db, o), "voucher": info}


def walk_in_checkin(db: Session, payload: dict, created_by: Optional[int] = None) -> dict:
    ch = db.query(Channel).filter_by(code="direct").first()
    if payload.get("channel_id"):
        ch = db.get(Channel, payload["channel_id"]) or ch
    ci = date.today()
    co = ci + timedelta(days=int(payload.get("nights", 1)))
    deposit = float(payload.get("deposit_amount") or 0)
    room_type_id = int(payload["room_type_id"])
    room_id = payload.get("room_id")
    if room_id:
        picked = db.get(Room, int(room_id))
        if not picked:
            raise InvalidStateError("房间不存在")
        if picked.hotel_id != int(payload["hotel_id"]):
            raise InvalidStateError("房间不属于本酒店")
        if picked.room_type_id != room_type_id:
            raise InvalidStateError("所选房间与房型不一致")
        from rooms.room_ops import assert_checkin_room

        assert_checkin_room(picked)
    o = create_order_record(
        db,
        hotel_id=payload["hotel_id"],
        guest_name=payload.get("guest_name") or "散客",
        phone=payload.get("phone"),
        room_type_id=room_type_id,
        channel_id=ch.id if ch else None,
        check_in=ci,
        check_out=co,
        rooms=int(payload.get("rooms", 1)),
        note=payload.get("note") or "散客即时入住",
        payment_status=payload.get("payment_status") or "unpaid",
        created_by=created_by,
    )
    if deposit > 0:
        o.deposit_amount = Decimal(str(deposit))
        db.flush()
    checkin_order(
        db,
        o.id,
        payload.get("room_id"),
        guest_name=payload.get("guest_name"),
        id_doc_type=payload.get("id_doc_type") or "id_card",
        id_doc_no=payload.get("id_doc_no") or payload.get("id_number"),
    )
    db.refresh(o)
    return order_detail_dict(db, o)


def sync_ota_order(db: Session, payload: dict, created_by: Optional[int] = None) -> dict:
    ext = (payload.get("external_order_no") or "").strip()
    if not ext:
        raise InvalidStateError("缺少 OTA 外部单号")
    platform = (payload.get("platform") or "ota").lower()
    ch = db.query(Channel).filter_by(code=platform).first()
    if not ch:
        ch = db.query(Channel).filter_by(code="ota").first()
    ci = datetime.strptime(payload["check_in"], "%Y-%m-%d").date()
    co = datetime.strptime(payload["check_out"], "%Y-%m-%d").date()
    o = create_order_record(
        db,
        hotel_id=payload["hotel_id"],
        guest_name=payload.get("guest_name") or "OTA客人",
        phone=payload.get("phone"),
        room_type_id=int(payload["room_type_id"]),
        channel_id=ch.id if ch else None,
        check_in=ci,
        check_out=co,
        rooms=int(payload.get("rooms", 1)),
        note=payload.get("note") or f"OTA同步 · {platform.upper()} · {ext}",
        external_order_no=ext,
        payment_status="paid",
        status=payload.get("status") or "confirmed",
        created_by=created_by,
    )
    return row_to_dict(db, o)
