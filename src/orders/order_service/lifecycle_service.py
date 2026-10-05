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


def _upsert_guest(db: Session, name: str, phone: Optional[str]) -> Guest:
    g = db.query(Guest).filter_by(phone=phone).first() if phone else None
    if g:
        if name and name not in ("散客", "团购客人") and (g.name in ("散客", "团购客人", "")):
            g.name = name
        return g
    import uuid

    g = Guest(
        one_id=f"ONE{int(datetime.now().timestamp() * 1000)}{uuid.uuid4().hex[:6]}",
        name=name or "散客",
        phone=phone,
        vip_level="normal",
    )
    db.add(g)
    db.flush()
    return g


def _calc_total(
    db: Session,
    rt: RoomType,
    nights: int,
    rooms: int,
    ch: Optional[Channel],
    extra: float = 0,
    *,
    hotel_id: Optional[int] = None,
    room_type_id: Optional[int] = None,
    on_date: Optional[date] = None,
) -> float:
    from finance.ota_commission_service import rate_for_channel, resolve_commission_rate

    comm = 0.0
    if ch and ch.code and hotel_id:
        try:
            comm = float(
                resolve_commission_rate(
                    db, int(hotel_id), ch.code, room_type_id=room_type_id or (rt.id if rt else None), on_date=on_date
                )
                or 0
            )
        except Exception:
            comm = rate_for_channel(db, ch)
    elif ch:
        comm = rate_for_channel(db, ch)
    rate = float(rt.base_price or 0) * (1 - comm * 0.5)
    return round(rate * max(1, nights) * max(1, rooms) + extra, 2)


def _gen_order_no(prefix: str, ci: date) -> str:
    import uuid

    return f"ORD-{prefix}-{ci.strftime('%Y%m%d')}-{int(datetime.now().timestamp() * 1000) % 100000000:08d}{uuid.uuid4().hex[:4].upper()}"


def _payment_defaults(ch: Optional[Channel], source_group: str, scenario: str) -> str:
    if scenario == "voucher" or source_group == "voucher":
        return "paid"
    if scenario == "ota" or source_group == "ota":
        return "paid"
    if ch and ch.code == "agreement":
        return "on_account"
    return "unpaid"


def create_order_record(
    db: Session,
    *,
    hotel_id: int,
    guest_name: str,
    phone: Optional[str],
    room_type_id: int,
    channel_id: Optional[int],
    check_in: date,
    check_out: date,
    rooms: int = 1,
    adults: int = 1,
    children: int = 0,
    note: str = "",
    external_order_no: Optional[str] = None,
    voucher_code: Optional[str] = None,
    payment_status: Optional[str] = None,
    status: str = "pending",
    extra_amount: float = 0,
    created_by: Optional[int] = None,
) -> Order:
    rt = db.get(RoomType, room_type_id)
    if not rt:
        raise InvalidStateError("房型不存在")
    ch = db.get(Channel, channel_id) if channel_id else None
    sg = source_group_for(ch, (check_out - check_in).days)
    if external_order_no:
        dup = db.query(Order).filter_by(external_order_no=external_order_no).first()
        if dup:
            raise ConflictError(f"外部单号已存在：{external_order_no}")
    if voucher_code:
        dup = db.query(Order).filter_by(voucher_code=voucher_code).first()
        if dup:
            raise ConflictError("该券码已核销")
    g = _upsert_guest(db, guest_name, phone)
    nights = max(1, (check_out - check_in).days)
    scenario = "voucher" if voucher_code else "ota" if external_order_no else "direct"
    pay = payment_status or _payment_defaults(ch, sg, scenario)
    total = _calc_total(
        db, rt, nights, rooms, ch, extra_amount, hotel_id=hotel_id, room_type_id=rt.id, on_date=check_in
    )
    prefix = "OTA" if external_order_no else "VCH" if voucher_code else "DIR"
    o = Order(
        hotel_id=hotel_id,
        order_no=_gen_order_no(prefix, check_in),
        guest_id=g.id,
        channel_id=channel_id,
        room_type_id=rt.id,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        rooms=rooms,
        adults=adults,
        children=children,
        total_amount=total,
        status=status,
        payment_status=pay,
        note=note,
        external_order_no=external_order_no,
        voucher_code=voucher_code,
        created_by=created_by,
        one_id=g.one_id,
        guest_phone=g.phone,
    )
    apply_order_domain_defaults(o, sg, ch.code if ch else None)
    db.add(o)
    db.flush()
    db.add(
        OrderItem(
            order_id=o.id,
            item_type="room",
            description=f"{rt.name} ×{nights}晚×{rooms}间",
            qty=nights * rooms,
            unit_price=round(total / max(1, nights * rooms), 2),
            amount=total,
        )
    )
    if extra_amount > 0:
        db.add(
            OrderItem(
                order_id=o.id,
                item_type="surcharge",
                description="团购升房/补差价",
                qty=1,
                unit_price=Decimal(str(extra_amount)),
                amount=Decimal(str(extra_amount)),
            )
        )
    from events import emit

    emit("order.created", {"order_id": o.id, "hotel_id": o.hotel_id, "order_no": o.order_no})
    return o


def checkin_order(
    db: Session,
    order_id: int,
    room_id: Optional[int] = None,
    *,
    guest_name: Optional[str] = None,
    id_doc_type: Optional[str] = None,
    id_doc_no: Optional[str] = None,
) -> Order:
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if not o.can_checkin():
        raise InvalidStateError(f"当前状态「{o.status}」不可办理入住")
    room = db.get(Room, room_id) if room_id else None
    if room and room.room_type_id != o.room_type_id:
        raise InvalidStateError("所选房间与订单房型不一致")
    if not room:
        room = (
            db.query(Room)
            .filter(
                Room.hotel_id == o.hotel_id,
                Room.room_type_id == o.room_type_id,
                Room.status.in_(["VC", "vacant", "clean", "inspected", "EA"]),
            )
            .first()
        )
    if not room:
        raise InvalidStateError("无可用房间，请先调整房态或选择其他房型")
    from rooms.room_ops import assert_checkin_room
    from rooms.room_status import OCC, transition

    assert_checkin_room(room)
    transition(db, room, OCC, reason="办理入住")
    res = db.query(Reservation).filter_by(order_id=o.id).first()
    if res:
        res.room_id = room.id
    else:
        res = Reservation(order_id=o.id, room_id=room.id)
        db.add(res)
        db.flush()
    o.checkin()
    if o.payment_status == "unpaid":
        o.payment_status = "partial"
    open_checkin_and_folio(
        db, o, room=room, reservation=res, guest_name=guest_name, id_doc_type=id_doc_type, id_doc_no=id_doc_no
    )
    from models import PmsCheckin, PmsRoomAssignment

    ci = db.query(PmsCheckin).filter_by(order_id=o.id, status="inhouse").order_by(PmsCheckin.id.desc()).first()
    db.add(
        PmsRoomAssignment(
            hotel_id=o.hotel_id,
            order_id=o.id,
            checkin_id=ci.id if ci else None,
            from_room_id=None,
            to_room_id=room.id,
            assign_type="checkin",
            reason="办理入住分房",
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
        },
    )
    return o


def checkout_order(
    db: Session, order_id: int, *, payment_mode: str = "auto", method: str = "wechat", pos_slip_no: Optional[str] = None
) -> Order:
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if not o.can_checkout():
        raise InvalidStateError("仅在住订单可退房")
    ch = db.get(Channel, o.channel_id) if o.channel_id else None
    sg = source_group_for(ch, int(o.nights or 0))
    from finance.payment import PaymentSettleContext, get_payment_provider, resolve_checkout_mode

    payment_mode = resolve_checkout_mode(o, source_group=sg, payment_mode=payment_mode)
    from hk.housekeeping_service import ensure_checkout_clean_task
    from rooms.room_status import DO, EA, OCC, VD, normalize, transition

    released: set[int] = set()

    def _release_room(rm: Room, reason: str) -> None:
        if rm.id in released:
            return
        st = normalize(rm.status)
        if st not in (OCC, DO, EA):
            return
        transition(db, rm, VD, reason=reason, force=st == EA)
        ensure_checkout_clean_task(db, hotel_id=o.hotel_id, room_id=rm.id)
        released.add(rm.id)

    res = db.query(Reservation).filter_by(order_id=o.id).first()
    if res and res.room_id:
        rm = db.get(Room, res.room_id)
        if rm:
            _release_room(rm, "退房")
    from models import PmsCheckin

    for line in db.query(PmsGroupRoomLine).filter_by(order_id=o.id).all():
        if line.can_checkout():
            line.checkout()
        if line.room_id:
            rm = db.get(Room, line.room_id)
            if rm:
                _release_room(rm, "团体退房")
    for ci in db.query(PmsCheckin).filter_by(order_id=o.id, status="inhouse").all():
        if ci.room_id:
            rm = db.get(Room, ci.room_id)
            if rm:
                _release_room(rm, "退房")
    get_payment_provider(payment_mode).settle(
        db,
        o,
        PaymentSettleContext(method=method, pos_slip_no=pos_slip_no),
    )
    close_checkin(db, o)
    o.checkout()
    db.flush()
    from events import emit

    emit(
        "payment.settled",
        {
            "order_id": o.id,
            "hotel_id": o.hotel_id,
            "guest_id": o.guest_id,
            "payment_mode": payment_mode,
            "method": method,
            "amount": float(o.total_amount or 0),
            "payment_status": o.payment_status,
        },
    )
    emit(
        "guest.checked_out",
        {
            "order_id": o.id,
            "hotel_id": o.hotel_id,
            "guest_id": o.guest_id,
            "payment_mode": payment_mode,
        },
    )
    return o


def cancel_order(db: Session, order_id: int, reason: str = "") -> Order:
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    o.cancel(reason=reason)
    for line in db.query(PmsGroupRoomLine).filter_by(order_id=o.id).all():
        line.cancel()
    db.flush()
    from events import emit

    emit(
        "order.cancelled",
        {
            "order_id": o.id,
            "hotel_id": o.hotel_id,
            "guest_id": o.guest_id,
            "reason": reason or "",
            "status": o.status,
        },
    )
    return o


def _room_charge(db: Session, order_id: int, total_amount: float) -> float:
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id, OrderItem.item_type == "room").all()
    if items:
        return round(sum(float(i.amount or 0) for i in items), 2)
    return float(total_amount or 0)


def _stay_type(source_group: str, nights: int) -> str:
    if source_group == "group":
        return "group"
    if source_group == "longstay" or nights >= 28:
        return "longstay"
    if source_group == "agreement":
        return "agreement"
    if source_group == "voucher":
        return "voucher"
    if source_group == "ota":
        return "ota"
    if source_group == "wechat":
        return "wechat"
    return "daily"


def row_to_dict(db: Session, o: Order) -> dict:
    from models import PmsCheckin

    g = db.get(Guest, o.guest_id) if o.guest_id else None
    rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
    ch = db.get(Channel, o.channel_id) if o.channel_id else None
    res = db.query(Reservation).filter_by(order_id=o.id).first()
    pre_room = db.get(Room, res.room_id) if res and res.room_id else None
    stay_ci = db.query(PmsCheckin).filter_by(order_id=o.id, status="inhouse").order_by(PmsCheckin.id.desc()).first()
    if not stay_ci:
        stay_ci = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.desc()).first()
    st = str(o.status or "")
    pre_room_id = pre_room.id if pre_room else None
    pre_room_no = pre_room.room_no if pre_room else ""
    stay_room_id = stay_ci.room_id if stay_ci and stay_ci.room_id else None
    stay_room_no = (stay_ci.room_no if stay_ci and stay_ci.room_no else "") or ""
    if stay_room_id and (not stay_room_no):
        sr = db.get(Room, stay_room_id)
        stay_room_no = sr.room_no if sr else ""
    if st == "no_show":
        assign_status = "no_show"
    elif st == "cancelled":
        assign_status = "cancelled"
    elif st == "checked_out":
        assign_status = "checked_out"
    elif st == "checked_in":
        assign_status = "in_house"
    elif st in ("pending", "confirmed"):
        assign_status = "pre_assigned" if pre_room_id else "unassigned"
    else:
        assign_status = st or "unassigned"
    is_group = int(getattr(o, "order_type", None) or 0) == 5 or bool(getattr(o, "group_name", None))
    group_lines = []
    pre_assign_status = "pre_assigned" if pre_room_id else "none"
    if is_group:
        group_lines = (
            db.query(PmsGroupRoomLine)
            .filter_by(order_id=o.id)
            .order_by(PmsGroupRoomLine.line_no.asc(), PmsGroupRoomLine.id.asc())
            .all()
        )
        held = sum(1 for x in group_lines if x.status == "held")
        assigned_n = sum(1 for x in group_lines if x.status == "assigned")
        inhouse_n = sum(1 for x in group_lines if x.status == "checked_in")
        if st not in ("cancelled", "no_show", "checked_out"):
            if inhouse_n:
                assign_status = "in_house"
            elif held:
                assign_status = "unassigned"
            elif assigned_n:
                assign_status = "pre_assigned"
        if assigned_n or inhouse_n:
            pre_assign_status = "pre_assigned"
            first_assigned = next((x for x in group_lines if x.room_id), None)
            if first_assigned and first_assigned.room_id:
                pr = db.get(Room, first_assigned.room_id)
                pre_room_id = first_assigned.room_id
                pre_room_no = pr.room_no if pr else ""
        else:
            pre_assign_status = "none"
    d = {
        "id": o.id,
        "hotel_id": o.hotel_id,
        "order_no": o.order_no,
        "guest_id": o.guest_id,
        "channel_id": o.channel_id,
        "room_type_id": o.room_type_id,
        "check_in": o.check_in.isoformat() if o.check_in else None,
        "check_out": o.check_out.isoformat() if o.check_out else None,
        "nights": int(o.nights or 0),
        "rooms": int(o.rooms or 1),
        "adults": int(o.adults or 1),
        "children": int(o.children or 0),
        "total_amount": float(o.total_amount or 0),
        "status": o.status,
        "payment_status": o.payment_status,
        "arrival_time": o.arrival_time,
        "note": o.note,
        "external_order_no": o.external_order_no or "",
        "voucher_code": o.voucher_code or "",
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }
    d["guest_name"] = g.name if g else "散客"
    d["phone"] = g.phone if g else ""
    d["room_type_name"] = rt.name if rt else ""
    d["channel_name"] = ch.name if ch else "散客"
    d["channel_code"] = ch.code if ch else "direct"
    d["channel_type"] = ch.type if ch else "direct"
    d["source_group"] = "group" if is_group else source_group_for(ch, int(o.nights or 0))
    d["group_name"] = getattr(o, "group_name", None) or ""
    d["group_type"] = getattr(o, "group_type", None) or ""
    d["settle_mode"] = getattr(o, "settle_mode", None) or "unified"
    d["settle_party"] = getattr(o, "settle_party", None) or ""
    d["sales_name"] = getattr(o, "sales_name", None) or ""
    d["other_amount"] = float(getattr(o, "other_amount", None) or 0)
    d["is_group"] = is_group
    d["group_line_count"] = len(group_lines) if is_group else 0
    d["group_held_count"] = sum(1 for x in group_lines if x.status == "held") if is_group else 0
    d["group_checked_in_count"] = sum(1 for x in group_lines if x.status == "checked_in") if is_group else 0
    d["assign_status"] = assign_status
    d["pre_assign_status"] = pre_assign_status
    d["pre_room_id"] = pre_room_id
    d["pre_room_no"] = pre_room_no
    d["pre_assigned_at"] = res.assigned_at.isoformat() if res and res.assigned_at else None
    d["pre_assigned_by"] = res.assigned_by if res else None
    d["stay_room_id"] = stay_room_id
    d["stay_room_no"] = stay_room_no
    d["room_no"] = ""
    d["room_id"] = None
    d["reception_no"] = f"JDD{res.id:08d}" if res and res.id else ""
    d["stay_type"] = _stay_type(d["source_group"], int(o.nights or 0))
    d["room_charge"] = _room_charge(db, o.id, float(o.total_amount or 0))
    d["order_type"] = int(getattr(o, "order_type", None) or 1)
    d["agreement_id"] = o.agreement_id
    if o.agreement_id:
        corp = db.get(CorpAccount, o.agreement_id)
        d["agreement_name"] = corp.name if corp else ""
    else:
        d["agreement_name"] = ""
    d["rate_strategy"] = getattr(o, "rate_strategy", None) or "daily"
    d["deposit_amount"] = float(getattr(o, "deposit_amount", None) or 0)
    d["allow_on_account"] = bool(getattr(o, "allow_on_account", False))
    d["channel_prepaid"] = bool(getattr(o, "channel_prepaid", False))
    d["skip_daily_room_charge"] = bool(getattr(o, "skip_daily_room_charge", False))
    d["monthly_rent"] = float(o.monthly_rent) if getattr(o, "monthly_rent", None) is not None else None
    d["longstay_cycle"] = getattr(o, "longstay_cycle", None)
    from models import PmsFolio

    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if folio:
        d["folio_id"] = folio.id
        d["folio_no"] = folio.folio_no
        d["folio_balance"] = float(folio.balance or 0)
        d["folio_status"] = folio.status
    else:
        d["folio_id"] = None
        d["folio_no"] = ""
        d["folio_balance"] = None
        d["folio_status"] = None
    return d


def order_detail_dict(db: Session, o: Order) -> dict:
    from models import PmsCheckin, PmsRoomAssignment, User
    from orders.pms_domain import checkin_public_dict

    d = row_to_dict(db, o)
    d["folio"] = folio_snapshot(db, o.id)
    checkins = db.query(PmsCheckin).filter_by(order_id=o.id).order_by(PmsCheckin.id.asc()).all()
    d["checkins"] = [checkin_public_dict(c) for c in checkins]
    d["checkin"] = checkin_public_dict(checkins[-1]) if checkins else None
    res = db.query(Reservation).filter_by(order_id=o.id).first()
    pre_room = db.get(Room, res.room_id) if res and res.room_id else None
    assignee = db.get(User, res.assigned_by) if res and res.assigned_by else None
    d["pre_assignment"] = {
        "status": d["pre_assign_status"],
        "room_id": d["pre_room_id"],
        "room_no": d["pre_room_no"],
        "room_type_name": None,
        "assigned_at": d["pre_assigned_at"],
        "assigned_by": d["pre_assigned_by"],
        "assigned_by_name": assignee.full_name or assignee.username if assignee else None,
        "reservation_id": res.id if res else None,
    }
    if pre_room and pre_room.room_type_id:
        rt = db.get(RoomType, pre_room.room_type_id)
        d["pre_assignment"]["room_type_name"] = rt.name if rt else None
    assigns = db.query(PmsRoomAssignment).filter_by(order_id=o.id).order_by(PmsRoomAssignment.id.desc()).limit(50).all()
    hist = []
    for a in assigns:
        fr = db.get(Room, a.from_room_id) if a.from_room_id else None
        tr = db.get(Room, a.to_room_id) if a.to_room_id else None
        op = db.get(User, a.operator_id) if a.operator_id else None
        hist.append(
            {
                "id": a.id,
                "assign_type": a.assign_type,
                "from_room_id": a.from_room_id,
                "from_room_no": fr.room_no if fr else None,
                "to_room_id": a.to_room_id,
                "to_room_no": tr.room_no if tr else None,
                "checkin_id": a.checkin_id,
                "operator_id": a.operator_id,
                "operator_name": op.full_name or op.username if op else None,
                "reason": a.reason or "",
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    d["room_assignments"] = hist
    if int(getattr(o, "order_type", None) or 0) == 5 or getattr(o, "group_name", None):
        lines = (
            db.query(PmsGroupRoomLine)
            .filter_by(order_id=o.id)
            .order_by(PmsGroupRoomLine.line_no.asc(), PmsGroupRoomLine.id.asc())
            .all()
        )
        blocks = db.query(PmsGroupRoomBlock).filter_by(order_id=o.id).order_by(PmsGroupRoomBlock.id.asc()).all()
        nights = max(1, int(o.nights or 1))
        d["group_lines"] = [_group_line_dict(db, x) for x in lines]
        d["group_blocks"] = [_group_block_dict(db, b, nights) for b in blocks]
        d["group_name"] = o.group_name or ""
        d["group_type"] = getattr(o, "group_type", None) or ""
        d["settle_mode"] = getattr(o, "settle_mode", None) or "unified"
        d["settle_party"] = getattr(o, "settle_party", None) or ""
        d["sales_name"] = getattr(o, "sales_name", None) or ""
        d["other_amount"] = float(getattr(o, "other_amount", None) or 0)
        room_fee = sum(float(b["subtotal"]) for b in d["group_blocks"])
        if not room_fee:
            room_fee = float(o.total_amount or 0) - d["other_amount"]
        d["room_fee_total"] = round(room_fee, 2)
        d["grand_total"] = round(d["room_fee_total"] + d["other_amount"], 2)
        d["balance_due"] = round(max(0, d["grand_total"] - float(getattr(o, "deposit_amount", None) or 0)), 2)
    else:
        d["group_lines"] = []
        d["group_blocks"] = []
    try:
        from finance.deposit_service import deposits_for_order

        d["deposits"] = deposits_for_order(db, int(o.hotel_id), int(o.id))
    except Exception:
        d["deposits"] = {"count": 0, "held_count": 0, "held_yuan": 0, "all_cleared": True, "items": []}
    return d
