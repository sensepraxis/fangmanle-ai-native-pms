# SPDX-License-Identifier: Apache-2.0
"""
PMS 前台运维：排房/换房/续住/同住/加收/收款/夜审日租/长住月租/No-show/RC。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

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
    Guest,
    Order,
    OrderItem,
    PmsCheckin,
    PmsFolio,
    PmsFolioEntry,
    PmsRoomAssignment,
    Reservation,
    Room,
    RoomStatusLog,
    RoomType,
)
from orders.pms_domain import (
    checkin_public_dict,
    folio_snapshot,
    open_checkin_and_folio,
    post_payment,
    recalc_folio,
)


def _active_checkin(db: Session, order_id: int) -> Optional[PmsCheckin]:
    return db.query(PmsCheckin).filter_by(order_id=order_id, status="inhouse").order_by(PmsCheckin.id.desc()).first()


def _vacant_ok(room: Room) -> bool:
    from rooms.room_status import is_sellable

    return is_sellable(room.status)


def record_room_assignment(
    db: Session,
    *,
    hotel_id: int,
    order_id: int,
    to_room_id: Optional[int],
    assign_type: str,
    from_room_id: Optional[int] = None,
    checkin_id: Optional[int] = None,
    operator_id: Optional[int] = None,
    reason: str = "",
) -> PmsRoomAssignment:
    row = PmsRoomAssignment(
        hotel_id=hotel_id,
        order_id=order_id,
        checkin_id=checkin_id,
        from_room_id=from_room_id,
        to_room_id=to_room_id,
        assign_type=assign_type,
        operator_id=operator_id,
        reason=(reason or "")[:200] or None,
    )
    db.add(row)
    db.flush()
    return row


def assign_room_only(db: Session, order_id: int, room_id: int, *, assigned_by: Optional[int] = None) -> dict:
    """仅预分房占房，不办理入住。房态-05：空净房 → 预抵房。"""
    from rooms.room_ops import mark_expected_arrival, release_preassign_room
    from rooms.room_status import EA, normalize

    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if o.status not in ("pending", "confirmed"):
        raise InvalidStateError(f"当前状态「{o.status}」不可排房")
    room = db.get(Room, room_id)
    if not room or room.hotel_id != o.hotel_id:
        raise NotFoundError("房间不存在")
    if room.room_type_id != o.room_type_id:
        raise InvalidStateError("房型与订单不一致")
    if not _vacant_ok(room) and normalize(room.status) != EA:
        raise InvalidStateError(f"房间状态「{room.status}」不可排房，需空净房")

    res = db.query(Reservation).filter_by(order_id=o.id).first()
    from_room_id = res.room_id if res and res.room_id else None

    # 换预分：释放原预抵房
    if from_room_id and from_room_id != room.id:
        old = db.get(Room, from_room_id)
        if old and normalize(old.status) == EA:
            release_preassign_room(db, old, reason="改预分·释放原房", operator_id=assigned_by)

    if res:
        res.room_id = room.id
        res.assigned_by = assigned_by
        res.assigned_at = datetime.now()
    else:
        res = Reservation(order_id=o.id, room_id=room.id, assigned_by=assigned_by)
        db.add(res)
    if o.status == "pending":
        o.confirm()

    mark_expected_arrival(db, room, operator_id=assigned_by)

    record_room_assignment(
        db,
        hotel_id=o.hotel_id,
        order_id=o.id,
        from_room_id=from_room_id,
        to_room_id=room.id,
        assign_type="pre_assign",
        operator_id=assigned_by,
        reason="预分房",
    )
    db.flush()
    return {
        "order_id": o.id,
        "pre_room_id": room.id,
        "pre_room_no": room.room_no,
        "assign_status": "pre_assigned",
        "room_status": room.status,
        "status": o.status,
    }


def change_room(
    db: Session,
    order_id: int,
    new_room_id: int,
    *,
    reason: str = "",
) -> dict:
    """在住换房：旧房 dirty，新房 occupied，更新 reservation + checkin。"""
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if o.status != "checked_in":
        raise InvalidStateError("仅在住订单可换房")
    new_room = db.get(Room, new_room_id)
    if not new_room or new_room.hotel_id != o.hotel_id:
        raise NotFoundError("目标房间不存在")
    if not _vacant_ok(new_room):
        raise InvalidStateError(f"目标房状态「{new_room.status}」不可换入")

    ci = _active_checkin(db, o.id)
    old_room_id = ci.room_id if ci else None
    res = db.query(Reservation).filter_by(order_id=o.id).first()
    if res and res.room_id:
        old_room_id = old_room_id or res.room_id

    if old_room_id == new_room.id:
        raise InvalidStateError("已在该房间")

    if old_room_id:
        old = db.get(Room, old_room_id)
        if old:
            from hk.housekeeping_service import ensure_checkout_clean_task
            from rooms.room_status import VD, transition

            transition(db, old, VD, reason=f"换房转出 · {reason or '前台换房'}", force=True)
            ensure_checkout_clean_task(db, hotel_id=o.hotel_id, room_id=old.id)

    from rooms.room_status import OCC
    from rooms.room_status import transition as rs_transition

    rs_transition(db, new_room, OCC, reason=f"换房转入 · {reason or '前台换房'}", force=True)

    if res:
        res.room_id = new_room.id
    else:
        res = Reservation(order_id=o.id, room_id=new_room.id)
        db.add(res)

    if ci:
        if ci.status == "inhouse":
            # 保留同住人：只改主入住房；简单做法：当前 checkin 换房
            ci.room_id = new_room.id
            ci.room_no = new_room.room_no
            ci.floor = new_room.floor
    else:
        open_checkin_and_folio(db, o, room=new_room, reservation=res)
        ci = _active_checkin(db, o.id)

    record_room_assignment(
        db,
        hotel_id=o.hotel_id,
        order_id=o.id,
        checkin_id=ci.id if ci else None,
        from_room_id=old_room_id,
        to_room_id=new_room.id,
        assign_type="change",
        reason=reason or "前台换房",
    )

    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if folio:
        db.add(
            PmsFolioEntry(
                folio_id=folio.id,
                entry_type="misc",
                biz_date=date.today(),
                description=f"换房记录 {new_room.room_no}" + (f" · {reason}" if reason else ""),
                amount=Decimal("0"),
                source="front_desk",
            )
        )
        recalc_folio(db, folio)

    db.flush()
    return {
        "order_id": o.id,
        "from_room_id": old_room_id,
        "to_room_id": new_room.id,
        "to_room_no": new_room.room_no,
        "stay_room_no": new_room.room_no,
        "checkin": checkin_public_dict(ci),
    }


def extend_stay(db: Session, order_id: int, extra_nights: int = 1, *, daily_rate: Optional[float] = None) -> dict:
    """续住：延长离店日，追加房费分录与订单金额。"""
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if o.status != "checked_in":
        raise InvalidStateError("仅在住订单可续住")
    n = max(1, int(extra_nights or 1))
    if not o.check_out:
        raise InvalidStateError("订单缺少离店日")

    rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
    rate = Decimal(str(daily_rate if daily_rate is not None else (rt.base_price if rt else 0) or 0))
    if rate <= 0 and o.nights and o.total_amount:
        rate = Decimal(str(o.total_amount)) / Decimal(str(max(1, int(o.nights))))

    o.check_out = o.check_out + timedelta(days=n)
    o.nights = int(o.nights or 0) + n

    is_longstay = getattr(o, "skip_daily_room_charge", False) or int(getattr(o, "order_type", 1) or 1) == 4
    add_amt = Decimal("0") if is_longstay else (rate * n)
    if add_amt > 0:
        o.total_amount = Decimal(str(o.total_amount or 0)) + add_amt
        db.add(
            OrderItem(
                order_id=o.id,
                item_type="room",
                description=f"续住房费 ×{n}晚",
                qty=n,
                unit_price=rate,
                amount=add_amt,
            )
        )

    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if not folio:
        res = db.query(Reservation).filter_by(order_id=o.id).first()
        room = db.get(Room, res.room_id) if res and res.room_id else None
        _, folio = open_checkin_and_folio(db, o, room=room, reservation=res)

    if is_longstay:
        desc = f"长住续住延期 {n} 天 · 至 {o.check_out.isoformat()}（月租另计）"
        et = "misc"
    else:
        desc = f"续住 {n} 晚 · 至 {o.check_out.isoformat()}"
        et = "room_charge"

    db.add(
        PmsFolioEntry(
            folio_id=folio.id,
            entry_type=et,
            biz_date=date.today(),
            description=desc,
            amount=add_amt,
            qty=n,
            unit_price=rate if add_amt else None,
            source="front_desk",
        )
    )
    recalc_folio(db, folio)
    db.flush()
    return {
        "order_id": o.id,
        "check_out": o.check_out.isoformat(),
        "nights": int(o.nights or 0),
        "added_amount": float(add_amt),
        "folio": folio_snapshot(db, o.id),
    }


def add_roommate(
    db: Session,
    order_id: int,
    *,
    guest_name: str,
    phone: Optional[str] = None,
    id_doc_type: str = "id_card",
    id_doc_no: Optional[str] = None,
) -> dict:
    """增加同住人：新建 checkin，挂 master_checkin_id。"""
    from infra.id_doc_crypto import pack_id_doc_fields

    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if o.status != "checked_in":
        raise InvalidStateError("仅在住订单可添加同住人")
    master = _active_checkin(db, o.id)
    if not master:
        raise InvalidStateError("缺少主入住登记")

    name = (guest_name or "").strip()
    if not name:
        raise InvalidStateError("请填写同住人姓名")

    g = None
    if phone:
        from infra.id_doc_crypto import pack_phone_fields

        packed_phone = pack_phone_fields(phone, hotel_id=o.hotel_id)
        g = db.query(Guest).filter_by(phone_hash=packed_phone["phone_hash"]).first()
        if not g:
            g = db.query(Guest).filter_by(phone=phone).first()
    if not g:
        import uuid

        from infra.id_doc_crypto import pack_phone_fields

        packed_phone = pack_phone_fields(phone, hotel_id=o.hotel_id) if phone else {}
        g = Guest(
            one_id=f"ONE{int(datetime.now().timestamp() * 1000)}{uuid.uuid4().hex[:6]}",
            name=name,
            phone=packed_phone.get("phone") or phone,
            phone_cipher=packed_phone.get("phone_cipher"),
            phone_mask=packed_phone.get("phone_mask"),
            phone_hash=packed_phone.get("phone_hash"),
            vip_level="normal",
        )
        db.add(g)
        db.flush()

    packed = pack_id_doc_fields(id_doc_no, hotel_id=o.hotel_id)
    ci = PmsCheckin(
        hotel_id=o.hotel_id,
        order_id=o.id,
        reservation_id=master.reservation_id,
        room_id=master.room_id,
        guest_id=g.id,
        guest_name=name,
        status="inhouse",
        actual_checkin_at=datetime.now(),
        id_doc_type=id_doc_type if packed["id_doc_cipher"] else (id_doc_type or None),
        id_doc_cipher=packed["id_doc_cipher"],
        id_doc_mask=packed["id_doc_mask"],
        id_doc_hash=packed["id_doc_hash"],
        id_doc_no=None,
        floor=master.floor,
        room_no=master.room_no,
        master_checkin_id=master.id,
    )
    db.add(ci)
    db.flush()
    return {"master_checkin_id": master.id, "roommate": checkin_public_dict(ci)}


def add_folio_charge(
    db: Session,
    order_id: int,
    *,
    amount: float,
    description: str = "住中加收",
    entry_type: str = "misc",
    operator_id: Optional[int] = None,
) -> dict:
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    if o.status not in ("checked_in", "checked_out"):
        raise InvalidStateError("当前状态不可加收")
    amt = Decimal(str(amount))
    if amt == 0:
        raise InvalidStateError("金额不能为 0")
    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if not folio:
        raise InvalidStateError("尚无客账")
    db.add(
        PmsFolioEntry(
            folio_id=folio.id,
            entry_type=entry_type or "misc",
            biz_date=date.today(),
            description=description or "住中加收",
            amount=amt,
            source="front_desk",
            operator_id=operator_id,
        )
    )
    if o.status == "checked_in" and amt > 0:
        o.total_amount = Decimal(str(o.total_amount or 0)) + amt
    recalc_folio(db, folio)
    db.flush()
    return folio_snapshot(db, o.id)


def collect_payment(
    db: Session,
    order_id: int,
    *,
    amount: float,
    method: str = "wechat_pos",
    pos_slip_no: Optional[str] = None,
    settle_type: str = "partial",
    operator_id: Optional[int] = None,
    note: str = "",
) -> dict:
    """住中/结账前收款（POS 小票人工录入）。"""
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    amt = float(amount or 0)
    if amt <= 0:
        raise InvalidStateError("收款金额须大于 0")
    if not (pos_slip_no or "").strip() and method not in ("cash", "ar", "corp"):
        # Demo：强制提醒录入小票；现金可空
        pass
    p = post_payment(
        db,
        o,
        amount=amt,
        method=method,
        pos_slip_no=(pos_slip_no or "").strip() or None,
        settle_type=settle_type or "partial",
        operator_id=operator_id,
        note=note,
    )
    folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
    if folio and folio.balance <= 0:
        o.payment_status = "paid"
    elif o.payment_status != "paid":
        o.payment_status = "partial"
    db.flush()
    return {
        "payment_id": p.id,
        "pos_slip_no": p.pos_slip_no,
        "amount": float(p.amount or 0),
        "folio": folio_snapshot(db, o.id),
    }


def mark_no_show(db: Session, order_id: int, *, reason: str = "") -> dict:
    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    o.mark_no_show(reason=reason)
    res = db.query(Reservation).filter_by(order_id=o.id).first()
    # 释放预排房（不改房态为 dirty，因未入住）
    if res:
        res.room_id = None
    db.flush()
    return {"order_id": o.id, "status": o.status}


def list_order_checkins(db: Session, order_id: int) -> list[dict]:
    rows = db.query(PmsCheckin).filter_by(order_id=order_id).order_by(PmsCheckin.id.asc()).all()
    return [checkin_public_dict(c) for c in rows]


def rc_registration_card(db: Session, order_id: int, *, reveal: bool = False) -> dict:
    """RC 入住登记单数据（默认证件脱敏）。"""
    from infra.id_doc_crypto import decrypt_id_doc
    from orders.order_service import order_detail_dict

    o = db.get(Order, order_id)
    if not o:
        raise NotFoundError("订单不存在")
    d = order_detail_dict(db, o)
    checkins = list_order_checkins(db, order_id)
    guests = []
    for c in db.query(PmsCheckin).filter_by(order_id=order_id).order_by(PmsCheckin.id.asc()).all():
        doc = c.id_doc_mask or ""
        if reveal and c.id_doc_cipher:
            doc = decrypt_id_doc(c.id_doc_cipher, hotel_id=c.hotel_id) or doc
        guests.append(
            {
                "guest_name": c.guest_name,
                "id_doc_type": c.id_doc_type,
                "id_doc_display": doc,
                "is_master": c.master_checkin_id is None,
                "room_no": c.room_no,
            }
        )
    return {
        "order": d,
        "checkins": checkins,
        "guests": guests,
        "printed_at": datetime.now().isoformat(timespec="seconds"),
        "hotel_note": "本单为 PMS 登记卡；公安上报由旅业接口另行处理。",
    }


def post_night_audit_room_charges(db: Session, hotel_id: int, biz_date: date) -> dict:
    """夜审：为在住非长住订单写入当日房费分录（幂等）。"""
    posted = 0
    skipped = 0
    amount_total = Decimal("0")
    inhouse = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status == "checked_in",
            Order.check_in <= biz_date,
            Order.check_out > biz_date,
        )
        .all()
    )
    for o in inhouse:
        if getattr(o, "skip_daily_room_charge", False) or int(getattr(o, "order_type", 1) or 1) == 4:
            skipped += 1
            continue
        if getattr(o, "channel_prepaid", False):
            # OTA 预付：日租已在入住时导入/冲减，夜审不再重复记收
            skipped += 1
            continue
        folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
        if not folio:
            skipped += 1
            continue
        exists = (
            db.query(PmsFolioEntry)
            .filter_by(
                folio_id=folio.id,
                entry_type="room_charge",
                biz_date=biz_date,
                source="night_audit",
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        rt = db.get(RoomType, o.room_type_id) if o.room_type_id else None
        if o.nights and o.total_amount and int(o.nights) > 0:
            # 用订单均摊作日租近似
            rate = Decimal(str(o.total_amount)) / Decimal(str(int(o.nights)))
        else:
            rate = Decimal(str(rt.base_price if rt else 0) or 0)
        if rate <= 0:
            skipped += 1
            continue
        db.add(
            PmsFolioEntry(
                folio_id=folio.id,
                entry_type="room_charge",
                biz_date=biz_date,
                description=f"夜审日租 {biz_date.isoformat()}",
                amount=rate,
                qty=1,
                unit_price=rate,
                source="night_audit",
            )
        )
        recalc_folio(db, folio)
        posted += 1
        amount_total += rate
    db.flush()
    return {
        "biz_date": biz_date.isoformat(),
        "posted": posted,
        "skipped": skipped,
        "amount_total": float(amount_total),
    }


def post_longstay_monthly_rent(db: Session, hotel_id: int, *, as_of: Optional[date] = None) -> dict:
    """长住月租入账：对本店长住在住单按月写入 Folio（幂等：同月同订单只记一次）。"""
    day = as_of or date.today()
    month_key = day.strftime("%Y-%m")
    posted = 0
    skipped = 0
    total = Decimal("0")
    rows = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status == "checked_in",
        )
        .all()
    )
    for o in rows:
        is_ls = int(getattr(o, "order_type", 1) or 1) == 4 or getattr(o, "skip_daily_room_charge", False)
        if not is_ls:
            continue
        rent = Decimal(str(getattr(o, "monthly_rent", None) or o.total_amount or 0))
        if rent <= 0:
            skipped += 1
            continue
        folio = db.query(PmsFolio).filter_by(order_id=o.id).first()
        if not folio:
            skipped += 1
            continue
        desc = f"长住月租 {month_key}"
        exists = (
            db.query(PmsFolioEntry)
            .filter(
                PmsFolioEntry.folio_id == folio.id,
                PmsFolioEntry.source == "longstay",
                PmsFolioEntry.description == desc,
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(
            PmsFolioEntry(
                folio_id=folio.id,
                entry_type="room_charge",
                biz_date=day,
                description=desc,
                amount=rent,
                qty=1,
                unit_price=rent,
                source="longstay",
            )
        )
        recalc_folio(db, folio)
        posted += 1
        total += rent
    db.flush()
    return {"month": month_key, "posted": posted, "skipped": skipped, "amount_total": float(total)}
