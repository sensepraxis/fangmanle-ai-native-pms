# SPDX-License-Identifier: Apache-2.0
"""
房态业务操作（用例 房态-01～12，不含房务工单细节）。

约定：界面中文名见 room_status.STATUS_CN；库内仍存 VC/VD/OCC/EA/DO/OOO/BLK。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
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
from infra.i18n import t
from models import Order, Reservation, Room, RoomType
from rooms.room_status import (
    BLK,
    DO,
    EA,
    OCC,
    OOO,
    VC,
    VD,
    can_checkin,
    label,
    normalize,
    transition,
)


def _set_meta(
    room: Room,
    *,
    note: Optional[str] = None,
    until: Optional[date] = None,
    clear: bool = False,
):
    if clear:
        if hasattr(room, "status_note"):
            room.status_note = None
        if hasattr(room, "status_until"):
            room.status_until = None
        return
    if note is not None and hasattr(room, "status_note"):
        room.status_note = (note or "")[:200] or None
    if until is not None and hasattr(room, "status_until"):
        room.status_until = until


def release_preassign_room(
    db: Session,
    room: Room,
    *,
    reason: str = "释放预分房",
    operator_id: Optional[int] = None,
):
    """预抵房释放回空净房。"""
    if normalize(room.status) == EA:
        transition(db, room, VC, reason=reason, operator_id=operator_id)
        _set_meta(room, clear=True)


def mark_expected_arrival(
    db: Session,
    room: Room,
    *,
    reason: str = "预分房·标记预抵",
    operator_id: Optional[int] = None,
) -> Room:
    """房态-05：空净房 → 预抵房。"""
    st = normalize(room.status)
    if st == EA:
        return room
    if st != VC:
        raise InvalidStateError(f"仅空净房可标记预抵，当前为{label(st)}")
    transition(db, room, EA, reason=reason, operator_id=operator_id)
    return room


def mark_due_out(
    db: Session,
    room: Room,
    *,
    reason: str = "标记预离",
    operator_id: Optional[int] = None,
) -> Room:
    """房态-04：已入住房 → 预离房（展示提醒，仍不可售）。"""
    st = normalize(room.status)
    if st == DO:
        return room
    if st != OCC:
        raise InvalidStateError(f"仅已入住房可标记预离，当前为{label(st)}")
    transition(db, room, DO, reason=reason, operator_id=operator_id)
    return room


def clear_due_out_to_occupied(
    db: Session,
    room: Room,
    *,
    reason: str = "续住·清除预离",
    operator_id: Optional[int] = None,
) -> Room:
    st = normalize(room.status)
    if st == OCC:
        return room
    if st != DO:
        raise InvalidStateError(f"当前非预离房，无法续住清除：{label(st)}")
    transition(db, room, OCC, reason=reason, operator_id=operator_id)
    return room


def set_out_of_order(
    db: Session,
    room: Room,
    *,
    reason: str,
    eta: Optional[date] = None,
    operator_id: Optional[int] = None,
) -> Room:
    """房态-06：非在住 → 维修房。已入住房/预离/预抵禁止直接置维修。同步维修工单。"""
    st = normalize(room.status)
    if st in (OCC, DO):
        raise InvalidStateError(f"{label(st)}不可直接置维修房，请先换房或退房")
    if st == EA:
        raise InvalidStateError("预抵房不可直接置维修房，请先释放预分房")
    if st == OOO:
        _set_meta(room, note=reason, until=eta)
    else:
        if st not in (VC, VD, BLK):
            raise InvalidStateError(f"当前状态{label(st)}不可置维修房")
        # BLK → OOO：经 VC 或 force
        if st == BLK:
            transition(db, room, VC, reason="锁房转维修·先解锁", operator_id=operator_id, force=True)
        transition(db, room, OOO, reason=reason or "设置维修房", operator_id=operator_id)
        _set_meta(room, note=reason, until=eta)
    try:
        from hk.housekeeping_service import ensure_repair_task

        ensure_repair_task(
            db,
            hotel_id=room.hotel_id,
            room_id=room.id,
            reason=reason or "设备故障",
        )
    except Exception:
        pass
    return room


def clear_out_of_order(
    db: Session,
    room: Room,
    *,
    to_status: str = VC,
    reason: str = "解除维修房",
    operator_id: Optional[int] = None,
) -> Room:
    """房态-07：维修房 → 空净房或空脏房。同步关闭维修工单。"""
    if normalize(room.status) != OOO:
        raise InvalidStateError("仅维修房可解除")
    dest = normalize(to_status)
    if dest not in (VC, VD):
        raise InvalidStateError("解除维修后只能变为空净房或空脏房")
    transition(db, room, dest, reason=reason, operator_id=operator_id)
    _set_meta(room, clear=True)
    try:
        from hk.housekeeping_service import close_repair_tasks_for_room

        close_repair_tasks_for_room(
            db,
            hotel_id=room.hotel_id,
            room_id=room.id,
            note=reason or "解除维修",
        )
    except Exception:
        pass
    return room


def set_block(
    db: Session,
    room: Room,
    *,
    reason: str,
    operator_id: Optional[int] = None,
) -> Room:
    """房态-08：空净房 → 锁房。"""
    st = normalize(room.status)
    if st == BLK:
        _set_meta(room, note=reason)
        return room
    if st != VC:
        raise InvalidStateError(f"仅空净房可锁房，当前为{label(st)}")
    transition(db, room, BLK, reason=reason or "锁房", operator_id=operator_id)
    _set_meta(room, note=reason)
    return room


def clear_block(
    db: Session,
    room: Room,
    *,
    reason: str = "解锁",
    operator_id: Optional[int] = None,
) -> Room:
    """房态-08：锁房 → 空净房。"""
    if normalize(room.status) != BLK:
        raise InvalidStateError("仅锁房可解锁")
    transition(db, room, VC, reason=reason, operator_id=operator_id)
    _set_meta(room, clear=True)
    return room


def night_audit_room_flip(db: Session, hotel_id: int, biz_date: date) -> dict:
    """
    房态-10 夜审状态翻转：
    - 已入住房且离店日=当日 → 预离房
    - 预离房且已续住（离店日>当日）→ 已入住房
    - 预抵房超日未住 → 释放空净房，订单标 no_show
    """
    rooms = {r.id: r for r in db.query(Room).filter_by(hotel_id=hotel_id).all()}
    stats = {
        "marked_due_out": 0,
        "cleared_due_out": 0,
        "released_ea": 0,
        "no_show_orders": 0,
    }

    stay = (
        db.query(Reservation, Order)
        .join(Order, Reservation.order_id == Order.id)
        .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
        .all()
    )
    for res, od in stay:
        if not res.room_id:
            continue
        rm = rooms.get(res.room_id)
        if not rm:
            continue
        st = normalize(rm.status)
        co = od.check_out
        if co == biz_date and st == OCC:
            transition(db, rm, DO, reason=f"夜审·预离 {biz_date}")
            stats["marked_due_out"] += 1
        elif co and co > biz_date and st == DO:
            transition(db, rm, OCC, reason=f"夜审·续住清除预离 {biz_date}")
            stats["cleared_due_out"] += 1

    hold = (
        db.query(Reservation, Order)
        .join(Order, Reservation.order_id == Order.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed")),
            Reservation.room_id.isnot(None),
        )
        .all()
    )
    for res, od in hold:
        rm = rooms.get(res.room_id)
        if not rm or normalize(rm.status) != EA:
            continue
        ci = od.check_in
        if ci and ci < biz_date:
            release_preassign_room(db, rm, reason=f"夜审·预抵超时释放 {biz_date}")
            od.mark_no_show(reason=f"夜审·预抵超时 {biz_date}")
            stats["released_ea"] += 1
            stats["no_show_orders"] += 1

    db.flush()
    return stats


def oversell_snapshot(db: Session, hotel_id: int, on_date: Optional[date] = None, days: int = 7) -> dict:
    """
    房态-12：按日×房型对比「物理可售」与「已接预订」。
    物理可售 = 总房 − 维修房 − 锁房。
    """
    on_date = on_date or date.today()
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).all()
    types = {t.id: t for t in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}

    by_type_phys: dict[int, dict] = {}
    for r in rooms:
        tid = r.room_type_id or 0
        bag = by_type_phys.setdefault(
            tid,
            {
                "room_type_id": tid,
                "total": 0,
                "ooo": 0,
                "blk": 0,
                "vc": 0,
                "vd": 0,
                "occ_like": 0,
            },
        )
        bag["total"] += 1
        st = normalize(r.status)
        if st == OOO:
            bag["ooo"] += 1
        elif st == BLK:
            bag["blk"] += 1
        elif st == VC:
            bag["vc"] += 1
        elif st == VD:
            bag["vd"] += 1
        elif st in (OCC, DO, EA):
            bag["occ_like"] += 1

    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed", "checked_in")),
        )
        .all()
    )

    days_out = []
    alerts = []
    for i in range(max(1, days)):
        d = on_date + timedelta(days=i)
        demand_by_type: dict[int, int] = {}
        for o in orders:
            ci = o.check_in
            co = o.check_out
            if not ci:
                continue
            if not co and o.nights:
                co = ci + timedelta(days=int(o.nights))
            if not co:
                co = ci + timedelta(days=1)
            if ci <= d < co:
                tid = o.room_type_id or 0
                demand_by_type[tid] = demand_by_type.get(tid, 0) + int(o.rooms or 1)

        type_rows = []
        day_alert = False
        for tid, phys in by_type_phys.items():
            sellable_phys = phys["total"] - phys["ooo"] - phys["blk"]
            demand = demand_by_type.get(tid, 0)
            short = demand - sellable_phys
            tname = types.get(tid).name if types.get(tid) else "未分房型"
            row = {
                "room_type_id": tid,
                "room_type_name": tname,
                "physical_sellable": sellable_phys,
                "vc": phys["vc"],
                "demand": demand,
                "shortfall": max(0, short),
                "oversell": short > 0,
            }
            type_rows.append(row)
            if short > 0:
                day_alert = True
                alerts.append(
                    {
                        "date": d.isoformat(),
                        "room_type_id": tid,
                        "room_type_name": tname,
                        "message": t(
                            "{date} {room} 超售风险：预订 {demand} > 可售物理 {sellable}",
                            date=d.isoformat(),
                            room=tname,
                            demand=demand,
                            sellable=sellable_phys,
                        ),
                        "demand": demand,
                        "physical_sellable": sellable_phys,
                    }
                )
        days_out.append({"date": d.isoformat(), "oversell": day_alert, "by_type": type_rows})

    return {
        "as_of": on_date.isoformat(),
        "days": days_out,
        "alerts": alerts,
        "has_alert": bool(alerts),
        "summary": (
            t("近 {n} 日超售预警 {count} 条", n=days, count=len(alerts)) if alerts else t("近 {n} 日房量充足", n=days)
        ),
    }


def assert_checkin_room(room: Room) -> None:
    """房态-01/02：仅空净房、预抵房可入住。"""
    if not can_checkin(room.status):
        raise InvalidStateError(
            f"房间状态「{label(room.status)}」不可办理入住，仅空净房/预抵房可入住",
        )


def _order_checkout(od: Order) -> Optional[date]:
    if od.check_out:
        return od.check_out
    if od.check_in and od.nights:
        return od.check_in + timedelta(days=int(od.nights))
    if od.check_in:
        return od.check_in + timedelta(days=1)
    return None


def project_board_for_date(db: Session, hotel_id: int, view_date: date) -> list[dict]:
    """
    未来某日房态看板投影：物理停用（OOO/BLK）+ 已分房订单占用。
    不写库；返回结构对齐 list_rooms（含 projected / view_date）。
    """
    from models import Guest
    from rooms.room_status import label, public_room_dict

    rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id)
        .all()
    )

    stay_by_room: dict[int, tuple] = {}
    stay_rows = (
        db.query(Reservation, Order, Guest)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed", "checked_in")),
            Reservation.room_id.isnot(None),
        )
        .all()
    )
    for res, od, g in stay_rows:
        rid = res.room_id
        if not rid:
            continue
        ci = od.check_in
        co = _order_checkout(od)
        if not ci or not co:
            continue
        if ci <= view_date < co:
            # 同一房多单时保留入住日更近的一单
            prev = stay_by_room.get(rid)
            if not prev or (ci >= prev[0].check_in if prev[0].check_in else True):
                stay_by_room[rid] = (od, g)

    out: list[dict] = []
    for r, rt in rows:
        phys = normalize(r.status)
        if phys in (OOO, BLK):
            until = getattr(r, "status_until", None)
            if until is None or until >= view_date:
                proj = phys
            else:
                proj = VC
        else:
            proj = VC

        od_g = stay_by_room.get(r.id)
        if od_g and proj not in (OOO, BLK):
            od, g = od_g
            if od.check_in == view_date:
                proj = EA
            else:
                proj = OCC

        d = public_room_dict(r)
        d["status"] = proj
        d["status_label"] = label(proj)
        d["status_legacy"] = {
            VC: "vacant",
            VD: "dirty",
            OCC: "occupied",
            EA: "occupied",
            DO: "occupied",
            OOO: "ooo",
            BLK: "ooo",
        }.get(proj, "vacant")
        d["room_type_name"] = rt.name if rt else ""
        base = float(rt.base_price) if rt and rt.base_price is not None else None
        d["base_price"] = base
        d["ai_price"] = base
        d["view_date"] = view_date.isoformat()
        d["projected"] = True

        if proj not in (OOO, BLK):
            d["status_note"] = None
            d["status_until"] = None

        if od_g and proj in (EA, OCC, DO):
            od, g = od_g
            d["guest_name"] = (g.name if g else None) or ("预抵客人" if proj == EA else "在住客人")
            d["guest_id"] = g.id if g else None
            d["order_id"] = od.id
            d["vip_level"] = g.vip_level if g else None
            d["check_in"] = od.check_in.strftime("%m-%d") if od.check_in else None
            d["check_out"] = od.check_out.strftime("%m-%d") if od.check_out else None
            if od.check_in and od.check_out:
                d["nights"] = max(1, (od.check_out - od.check_in).days)
            else:
                d["nights"] = od.nights or 1
            d["ai_tip"] = f"规划·预抵订单 #{od.id}" if proj == EA else f"规划·占用订单 #{od.id}"
        else:
            d["guest_name"] = None
            d["guest_id"] = None
            d["order_id"] = None
            d["check_in"] = None
            d["check_out"] = None
            d["nights"] = None
            note = (getattr(r, "status_note", None) or "").strip() if proj in (OOO, BLK) else ""
            until = d.get("status_until")
            if proj in (OOO, BLK) and note:
                d["ai_tip"] = note + (f" · 预计 {until}" if until else "")
                d["status_note"] = note
            elif proj in (OOO, BLK):
                d["ai_tip"] = "停用/锁房中，不可售"
            else:
                d["ai_tip"] = "规划日空净可售"

        d["open_hk"] = None
        d["open_request"] = None
        out.append(d)

    out.sort(key=lambda x: x["room_no"])
    return out


def room_status_history(
    db: Session,
    hotel_id: int,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    room_no: Optional[str] = None,
    limit: int = 200,
) -> dict:
    """经营分析：房态变更流水（RoomStatusLog）。"""
    from models import RoomStatusLog

    q = db.query(RoomStatusLog, Room).join(Room, RoomStatusLog.room_id == Room.id).filter(Room.hotel_id == hotel_id)
    if room_no:
        q = q.filter(Room.room_no.ilike(f"%{room_no.strip()}%"))
    if date_from:
        q = q.filter(RoomStatusLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(RoomStatusLog.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    rows = q.order_by(RoomStatusLog.id.desc()).limit(max(1, min(int(limit or 200), 500))).all()
    items = []
    for log, rm in rows:
        items.append(
            {
                "id": log.id,
                "room_id": rm.id,
                "room_no": rm.room_no,
                "from_status": log.from_status,
                "to_status": log.to_status,
                "from_label": label(log.from_status) if log.from_status else None,
                "to_label": label(log.to_status) if log.to_status else None,
                "reason": log.reason,
                "operator_id": log.operator_id,
                "created_at": log.created_at.isoformat(sep=" ", timespec="seconds") if log.created_at else None,
            }
        )
    return {
        "hotel_id": hotel_id,
        "from": date_from.isoformat() if date_from else None,
        "to": date_to.isoformat() if date_to else None,
        "room_no": room_no or None,
        "count": len(items),
        "items": items,
    }
