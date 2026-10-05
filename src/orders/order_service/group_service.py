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


def _group_block_dict(db: Session, block: PmsGroupRoomBlock, nights: int = 1) -> dict:
    rt = db.get(RoomType, block.room_type_id) if block.room_type_id else None
    qty = int(block.qty or 1)
    unit = float(block.unit_price or 0)
    n = max(1, nights)
    return {
        "id": block.id,
        "order_id": block.order_id,
        "room_type_id": block.room_type_id,
        "room_type_name": rt.name if rt else "",
        "qty": qty,
        "unit_price": unit,
        "subtotal": round(unit * qty * n, 2),
    }


def _group_line_dict(db: Session, line: PmsGroupRoomLine) -> dict:
    rt = db.get(RoomType, line.room_type_id) if line.room_type_id else None
    rm = db.get(Room, line.room_id) if line.room_id else None
    return {
        "id": line.id,
        "order_id": line.order_id,
        "line_no": int(line.line_no or 1),
        "room_type_id": line.room_type_id,
        "room_type_name": rt.name if rt else "",
        "guest_name": line.guest_name or "",
        "guest_phone": line.guest_phone or "",
        "id_last4": getattr(line, "id_last4", None) or "",
        "room_id": line.room_id,
        "room_no": rm.room_no if rm else "",
        "checkin_id": line.checkin_id,
        "stay_check_in": line.stay_check_in.isoformat() if getattr(line, "stay_check_in", None) else None,
        "stay_check_out": line.stay_check_out.isoformat() if getattr(line, "stay_check_out", None) else None,
        "status": line.status or "held",
        "note": line.note or "",
    }


def _parse_date(val, fallback: date) -> date:
    if not val:
        return fallback
    if isinstance(val, date) and (not isinstance(val, datetime)):
        return val
    return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()


def create_group_order(db: Session, payload: dict, created_by: Optional[int] = None) -> dict:
    """创建团体主单：房量块 + 分房清单（对齐原型字段）。"""
    hotel_id = int(payload["hotel_id"])
    group_name = (payload.get("group_name") or "").strip()
    if not group_name:
        raise InvalidStateError("请填写团体名称")
    contact = (payload.get("contact_name") or payload.get("guest_name") or "").strip() or "团体联系人"
    phone = payload.get("phone") or payload.get("contact_phone")
    ci = datetime.strptime(payload["check_in"], "%Y-%m-%d").date()
    co = datetime.strptime(payload["check_out"], "%Y-%m-%d").date()
    if co <= ci:
        raise InvalidStateError("离店日期须晚于入住日期")
    nights = max(1, (co - ci).days)
    blocks_in = payload.get("blocks") or []
    lines_in = payload.get("lines") or []
    default_rt = payload.get("room_type_id")
    room_count = int(payload.get("rooms") or 0)
    if not blocks_in and (not lines_in):
        if not default_rt or room_count < 1:
            raise InvalidStateError("请填写房量或分房清单")
        blocks_in = [{"room_type_id": int(default_rt), "qty": room_count}]
    normalized_blocks = []
    for i, raw in enumerate(blocks_in):
        rt_id = int(raw.get("room_type_id") or default_rt or 0)
        rt = db.get(RoomType, rt_id)
        if not rt:
            raise InvalidStateError(f"房量第 {i + 1} 行房型无效")
        qty = max(1, int(raw.get("qty") or 1))
        unit = float(raw.get("unit_price") if raw.get("unit_price") is not None else rt.base_price or 0)
        normalized_blocks.append({"room_type_id": rt_id, "qty": qty, "unit_price": unit})
    if not lines_in and normalized_blocks:
        for b in normalized_blocks:
            for j in range(b["qty"]):
                lines_in.append(
                    {
                        "room_type_id": b["room_type_id"],
                        "guest_name": "",
                        "check_in": ci.isoformat(),
                        "check_out": co.isoformat(),
                    }
                )
    normalized_lines = []
    for i, raw in enumerate(lines_in):
        rt_id = int(raw.get("room_type_id") or (normalized_blocks[0]["room_type_id"] if normalized_blocks else 0) or 0)
        rt = db.get(RoomType, rt_id)
        if not rt:
            raise InvalidStateError(f"分房清单第 {i + 1} 行房型无效")
        normalized_lines.append(
            {
                "room_type_id": rt_id,
                "guest_name": (raw.get("guest_name") or "").strip(),
                "guest_phone": (raw.get("guest_phone") or phone or "") or None,
                "id_last4": str(raw.get("id_last4") or "").strip()[-4:] or None,
                "note": (raw.get("note") or "")[:200],
                "stay_check_in": _parse_date(raw.get("check_in") or raw.get("stay_check_in"), ci),
                "stay_check_out": _parse_date(raw.get("check_out") or raw.get("stay_check_out"), co),
                "room_id": int(raw["room_id"]) if raw.get("room_id") else None,
            }
        )
    if not normalized_blocks and normalized_lines:
        by_rt: dict[int, int] = {}
        for ln in normalized_lines:
            by_rt[ln["room_type_id"]] = by_rt.get(ln["room_type_id"], 0) + 1
        for rt_id, qty in by_rt.items():
            rt = db.get(RoomType, rt_id)
            normalized_blocks.append(
                {"room_type_id": rt_id, "qty": qty, "unit_price": float(rt.base_price or 0) if rt else 0}
            )
    room_total = round(sum(b["unit_price"] * b["qty"] * nights for b in normalized_blocks), 2)
    other = float(payload.get("other_amount") or 0)
    deposit = float(payload.get("deposit_amount") or 0)
    grand = round(room_total + other, 2)
    ch = None
    if payload.get("channel_id"):
        ch = db.get(Channel, int(payload["channel_id"]))
    if not ch:
        ch = db.query(Channel).filter_by(code="direct").first()
    primary_rt = normalized_blocks[0]["room_type_id"]
    total_rooms = sum(b["qty"] for b in normalized_blocks) or len(normalized_lines)
    o = create_order_record(
        db,
        hotel_id=hotel_id,
        guest_name=contact,
        phone=phone,
        room_type_id=primary_rt,
        channel_id=ch.id if ch else None,
        check_in=ci,
        check_out=co,
        rooms=total_rooms,
        note=payload.get("note") or f"团体预订 · {group_name}",
        payment_status=payload.get("payment_status") or "unpaid",
        status=payload.get("status") or "confirmed",
        created_by=created_by,
    )
    o.order_type = 5
    o.group_name = group_name
    o.group_type = (payload.get("group_type") or "旅游团").strip() or "旅游团"
    o.settle_mode = (payload.get("settle_mode") or "unified").strip() or "unified"
    o.settle_party = (payload.get("settle_party") or "").strip() or None
    o.sales_name = (payload.get("sales_name") or "").strip() or None
    o.other_amount = Decimal(str(other))
    o.deposit_amount = Decimal(str(deposit))
    o.total_amount = Decimal(str(grand))
    o.rate_strategy = "daily"
    for it in db.query(OrderItem).filter_by(order_id=o.id).all():
        db.delete(it)
    for b in normalized_blocks:
        rt = db.get(RoomType, b["room_type_id"])
        amt = round(b["unit_price"] * b["qty"] * nights, 2)
        db.add(
            OrderItem(
                order_id=o.id,
                item_type="room",
                description=f"团体·{(rt.name if rt else '房型')} ×{nights}晚×{b['qty']}间",
                qty=nights * b["qty"],
                unit_price=b["unit_price"],
                amount=amt,
            )
        )
    if other > 0:
        db.add(
            OrderItem(
                order_id=o.id,
                item_type="other",
                description="其他费用(餐饮/会议)",
                qty=1,
                unit_price=other,
                amount=other,
            )
        )
    db.flush()
    for b in normalized_blocks:
        db.add(
            PmsGroupRoomBlock(
                hotel_id=hotel_id,
                order_id=o.id,
                room_type_id=b["room_type_id"],
                qty=b["qty"],
                unit_price=b["unit_price"],
            )
        )
    out_lines = []
    for i, ln in enumerate(normalized_lines):
        row = PmsGroupRoomLine(
            hotel_id=hotel_id,
            order_id=o.id,
            line_no=i + 1,
            room_type_id=ln["room_type_id"],
            guest_name=ln["guest_name"] or None,
            guest_phone=ln["guest_phone"],
            id_last4=ln["id_last4"],
            stay_check_in=ln["stay_check_in"],
            stay_check_out=ln["stay_check_out"],
            room_id=ln["room_id"],
            status="assigned" if ln["room_id"] else "held",
            note=ln["note"],
        )
        db.add(row)
        db.flush()
        out_lines.append(_group_line_dict(db, row))
    db.flush()
    d = order_detail_dict(db, o)
    d["group_lines"] = out_lines
    return d


def assign_group_line(
    db: Session, order_id: int, line_id: int, room_id: int, *, operator_id: Optional[int] = None
) -> dict:
    o = db.get(Order, order_id)
    if not o or int(getattr(o, "order_type", None) or 0) != 5:
        raise NotFoundError("团体订单不存在")
    line = db.get(PmsGroupRoomLine, line_id)
    if not line or line.order_id != order_id:
        raise NotFoundError("房间行不存在")
    if line.status in ("checked_in", "checked_out", "cancelled"):
        raise InvalidStateError(f"当前行状态「{line.status}」不可排房")
    room = db.get(Room, room_id)
    if not room or room.hotel_id != o.hotel_id:
        raise InvalidStateError("房间无效")
    from rooms.room_ops import mark_expected_arrival
    from rooms.room_status import is_sellable, label

    if not is_sellable(room.status):
        raise InvalidStateError(f"房间 {room.room_no} 当前不可排（{label(room.status)}），需空净房")
    if line.room_type_id and room.room_type_id != line.room_type_id:
        raise InvalidStateError("房间与该行房型不一致")
    clash = (
        db.query(PmsGroupRoomLine)
        .filter(
            PmsGroupRoomLine.hotel_id == o.hotel_id,
            PmsGroupRoomLine.room_id == room_id,
            PmsGroupRoomLine.id != line_id,
            PmsGroupRoomLine.status.in_(("assigned", "checked_in")),
        )
        .first()
    )
    if clash:
        raise InvalidStateError(f"房间已被团体行 #{clash.id} 占用")
    from models import PmsRoomAssignment

    prev = line.room_id
    line.room_id = room.id
    line.room_no = room.room_no
    line.assign()
    mark_expected_arrival(db, room, operator_id=operator_id, reason="团体预分房·预抵")
    db.add(
        PmsRoomAssignment(
            hotel_id=o.hotel_id,
            order_id=o.id,
            checkin_id=None,
            from_room_id=prev,
            to_room_id=room.id,
            assign_type="pre_assign",
            operator_id=operator_id,
            reason=f"团体预分 · 行{line.line_no}",
        )
    )
    db.flush()
    return {"order": row_to_dict(db, o), "line": _group_line_dict(db, line), "room_status": room.status}


def checkin_group_line(
    db: Session,
    order_id: int,
    line_id: int,
    *,
    room_id: Optional[int] = None,
    guest_name: Optional[str] = None,
    id_doc_type: Optional[str] = None,
    id_doc_no: Optional[str] = None,
) -> dict:
    o = db.get(Order, order_id)
    if not o or int(getattr(o, "order_type", None) or 0) != 5:
        raise NotFoundError("团体订单不存在")
    if not o.can_assign_room():
        raise InvalidStateError(f"订单状态「{o.status}」不可入住")
    line = db.get(PmsGroupRoomLine, line_id)
    if not line or line.order_id != order_id:
        raise NotFoundError("房间行不存在")
    if line.status == "checked_in":
        raise InvalidStateError("该行已入住")
    if line.status == "cancelled":
        raise InvalidStateError("该行已取消")
    if not line.can_checkin():
        raise InvalidStateError(f"团体行状态「{line.status}」不可入住")
    rid = room_id or line.room_id
    room = db.get(Room, rid) if rid else None
    if not room:
        room = (
            db.query(Room)
            .filter(
                Room.hotel_id == o.hotel_id,
                Room.room_type_id == line.room_type_id,
                Room.status.in_(["VC", "vacant", "clean", "inspected", "EA"]),
            )
            .first()
        )
    if not room:
        raise InvalidStateError("无可用房间，请先排房")
    if line.room_type_id and room.room_type_id != line.room_type_id:
        raise InvalidStateError("房间与该行房型不一致")
    from rooms.room_ops import assert_checkin_room
    from rooms.room_status import OCC, transition

    assert_checkin_room(room)
    transition(db, room, OCC, reason="团体入住")
    line.room_id = room.id
    name = (guest_name or line.guest_name or "").strip() or None
    ci, _folio = open_checkin_and_folio(
        db, o, room=room, reservation=None, guest_name=name, id_doc_type=id_doc_type, id_doc_no=id_doc_no
    )
    line.checkin_id = ci.id
    line.checkin()
    if o.can_checkin():
        o.checkin()
    if o.payment_status == "unpaid":
        o.payment_status = "partial"
    from models import PmsRoomAssignment

    db.add(
        PmsRoomAssignment(
            hotel_id=o.hotel_id,
            order_id=o.id,
            checkin_id=ci.id,
            from_room_id=None,
            to_room_id=room.id,
            assign_type="checkin",
            reason=f"团体入住 · 行{line.line_no}",
        )
    )
    db.flush()
    from events import emit

    emit(
        "guest.checked_in",
        {
            "order_id": o.id,
            "hotel_id": o.hotel_id,
            "room_id": room.id,
            "guest_id": o.guest_id,
            "group_line_id": line.id,
        },
    )
    return {"order": order_detail_dict(db, o), "line": _group_line_dict(db, line)}
