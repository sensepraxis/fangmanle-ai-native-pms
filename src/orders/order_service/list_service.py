# SPDX-License-Identifier: Apache-2.0
"""orders.order_service 子模块 — auto-split by AST.

本文件由 src/orders/order_service.py 按业务子域拆分而成。
外部调用 `from orders.order_service import xxx` 仍兼容（见 __init__.py）。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

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

# 同包 cross-import：list_service 复用 lifecycle_service 的 row_to_dict
from orders.order_service.lifecycle_service import row_to_dict
from orders.pms_domain import (
    apply_order_domain_defaults,
    close_checkin,
    folio_snapshot,
    open_checkin_and_folio,
    post_ar_charge,
    post_payment,
)

WECHAT_CHANNEL_CODES = frozenset({"wechat", "wecom", "xiaohongshu"})

DIRECT_LIKE_GROUPS = frozenset({"direct"})


def orders_work_summary(db: Session, hotel_id: int, on_date: date) -> dict:
    """前台任务视图固定计数（不随搜索/来源筛选变化）。"""
    from sqlalchemy import func, or_

    base = db.query(Order).filter(Order.hotel_id == hotel_id, Order.status != "cancelled")
    unassigned_q = (
        base.filter(Order.status.in_(("pending", "confirmed")))
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .filter(or_(Reservation.id.is_(None), Reservation.room_id.is_(None)))
    )
    return {
        "date": on_date.isoformat(),
        "all": base.count(),
        "arrivals": base.filter(Order.check_in == on_date, Order.status.in_(("pending", "confirmed"))).count(),
        "inhouse": base.filter(Order.status == "checked_in").count(),
        "departures": base.filter(Order.check_out == on_date, Order.status == "checked_in").count(),
        "created_today": base.filter(func.date(Order.created_at) == on_date).count(),
        "unassigned": unassigned_q.distinct().count(),
        "pending": base.filter(Order.status == "pending").count(),
    }


def _channel_ids_for_source(db: Session, source: str) -> list[int] | None:
    if not source or source == "all":
        return None
    if source == "group":
        return None
    channels = db.query(Channel).all()
    if source == "ota":
        return [c.id for c in channels if source_group_for(c) == "ota"]
    if source in OTA_CHANNEL_CODES:
        return [c.id for c in channels if c.code == source]
    if source == "wechat":
        return [c.id for c in channels if c.code in WECHAT_CHANNEL_CODES]
    if source == "xiaohongshu":
        return [c.id for c in channels if c.code == "xiaohongshu"]
    if source == "direct":
        return [c.id for c in channels if source_group_for(c) in DIRECT_LIKE_GROUPS]
    ids = [c.id for c in channels if source_group_for(c) == source]
    return ids


def _apply_combo_search(query, filters: dict):
    """组合搜索：各字段非空时 AND 叠加（精确到字段，非全局 OR）。"""
    from sqlalchemy import String, cast, or_

    f = {k: (v or "").strip() for k, v in filters.items()}
    active = {k: v for k, v in f.items() if v}
    if not active:
        return query
    need_guest = bool(active.get("guest_name") or active.get("phone"))
    need_res = bool(active.get("reception_no") or active.get("room_no"))
    if need_guest:
        query = query.outerjoin(Guest, Order.guest_id == Guest.id)
    if need_res:
        query = query.outerjoin(Reservation, Reservation.order_id == Order.id)
    if active.get("room_no"):
        from models import PmsCheckin

        query = query.outerjoin(Room, Reservation.room_id == Room.id)
        query = query.outerjoin(PmsCheckin, PmsCheckin.order_id == Order.id)
    if active.get("order_no"):
        query = query.filter(Order.order_no.ilike(f"%{active['order_no']}%"))
    if active.get("external_order_no"):
        query = query.filter(
            or_(
                Order.external_order_no.ilike(f"%{active['external_order_no']}%"),
                Order.voucher_code.ilike(f"%{active['external_order_no']}%"),
            )
        )
    if active.get("note"):
        query = query.filter(Order.note.ilike(f"%{active['note']}%"))
    if active.get("guest_name"):
        query = query.filter(Guest.name.ilike(f"%{active['guest_name']}%"))
    if active.get("phone"):
        query = query.filter(Guest.phone.ilike(f"%{active['phone']}%"))
    if active.get("room_no"):
        from models import PmsCheckin

        query = query.filter(
            or_(Room.room_no.ilike(f"%{active['room_no']}%"), PmsCheckin.room_no.ilike(f"%{active['room_no']}%"))
        )
    if active.get("reception_no"):
        term = active["reception_no"].upper().replace("JDD", "").strip()
        query = query.filter(cast(Reservation.id, String).ilike(f"%{term}%"))
    return query.distinct()


def query_orders_list(
    db: Session,
    hotel_id: int,
    *,
    view: str = "all",
    on_date: date | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    source: str | None = None,
    channel_id: int | None = None,
    room_type_id: int | None = None,
    q: str | None = None,
    order_no: str | None = None,
    external_order_no: str | None = None,
    reception_no: str | None = None,
    room_no: str | None = None,
    guest_name: str | None = None,
    phone: str | None = None,
    note: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """分页订单列表（扁平面板）。"""
    from sqlalchemy import String, cast, func, or_

    on_date = on_date or date.today()
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 20)))
    query = db.query(Order).filter(Order.hotel_id == hotel_id)
    if view == "arrivals":
        query = query.filter(Order.check_in == on_date, Order.status.in_(("pending", "confirmed")))
    elif view == "inhouse":
        query = query.filter(Order.status == "checked_in")
    elif view == "departures":
        query = query.filter(Order.check_out == on_date, Order.status == "checked_in")
    elif view == "created_today":
        query = query.filter(func.date(Order.created_at) == on_date, Order.status != "cancelled")
    elif view == "unassigned":
        query = (
            query.filter(Order.status.in_(("pending", "confirmed")))
            .outerjoin(Reservation, Reservation.order_id == Order.id)
            .filter(or_(Reservation.id.is_(None), Reservation.room_id.is_(None)))
        )
    elif view == "pending":
        query = query.filter(Order.status == "pending")
    elif view == "all":
        query = query.filter(Order.status != "cancelled")
    else:
        query = query.filter(Order.status != "cancelled")
    if status:
        query = query.filter(Order.status == status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if room_type_id:
        query = query.filter(Order.room_type_id == int(room_type_id))
    if channel_id:
        query = query.filter(Order.channel_id == int(channel_id))
    elif (source or "") == "group":
        query = query.filter(Order.order_type == 5)
    else:
        ch_ids = _channel_ids_for_source(db, source or "")
        if ch_ids is not None:
            if not ch_ids:
                return ([], 0)
            query = query.filter(Order.channel_id.in_(ch_ids), Order.order_type != 5)
    query = _apply_combo_search(
        query,
        {
            "order_no": order_no,
            "external_order_no": external_order_no,
            "reception_no": reception_no,
            "room_no": room_no,
            "guest_name": guest_name,
            "phone": phone,
            "note": note,
        },
    )
    term = (q or "").strip()
    combo_used = any(
        (x or "").strip() for x in (order_no, external_order_no, reception_no, room_no, guest_name, phone, note)
    )
    if term and (not combo_used):
        like = f"%{term}%"
        query = (
            query.outerjoin(Guest, Order.guest_id == Guest.id)
            .outerjoin(Reservation, Reservation.order_id == Order.id)
            .outerjoin(Room, Reservation.room_id == Room.id)
            .filter(
                or_(
                    Order.order_no.ilike(like),
                    Order.external_order_no.ilike(like),
                    Order.voucher_code.ilike(like),
                    Order.note.ilike(like),
                    Guest.name.ilike(like),
                    Guest.phone.ilike(like),
                    Room.room_no.ilike(like),
                    cast(Reservation.id, String).ilike(like),
                )
            )
            .distinct()
        )
    total = query.count()
    if view == "arrivals":
        query = query.order_by(Order.check_in.asc(), Order.id.asc())
    elif view == "departures":
        query = query.order_by(Order.check_out.asc(), Order.id.asc())
    elif view == "inhouse":
        query = query.order_by(Order.check_in.desc(), Order.id.desc())
    else:
        query = query.order_by(Order.check_in.desc(), Order.id.desc())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [row_to_dict(db, o) for o in rows]
    return (items, total)


def list_orders_compat(
    db: Session,
    hotel_id: int,
    *,
    status: Optional[str] = None,
    channel_id: Optional[int] = None,
    source: Optional[str] = None,
    view: Optional[str] = None,
    q: Optional[str] = None,
    order_no: Optional[str] = None,
    external_order_no: Optional[str] = None,
    reception_no: Optional[str] = None,
    room_no: Optional[str] = None,
    guest_name: Optional[str] = None,
    phone: Optional[str] = None,
    note: Optional[str] = None,
    on_date: Optional[str] = None,
    room_type_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    page: Optional[int] = None,
    page_size: int = 20,
) -> Any:
    """订单列表（含分页与旧版数组兼容）。"""
    from datetime import date

    biz_date = date.fromisoformat(on_date) if on_date else date.today()
    if page is not None:
        items, total = query_orders_list(
            db,
            hotel_id,
            view=view or "arrivals",
            on_date=biz_date,
            status=status,
            payment_status=payment_status,
            source=source,
            channel_id=channel_id,
            room_type_id=room_type_id,
            q=q,
            order_no=order_no,
            external_order_no=external_order_no,
            reception_no=reception_no,
            room_no=room_no,
            guest_name=guest_name,
            phone=phone,
            note=note,
            page=page,
            page_size=page_size,
        )
        summary = orders_work_summary(db, hotel_id, biz_date)
        return {"items": items, "total": total, "page": page, "page_size": page_size, "summary": summary}
    items, _total = query_orders_list(
        db,
        hotel_id,
        view=view or "all",
        on_date=biz_date,
        status=status,
        payment_status=payment_status,
        source=source,
        channel_id=channel_id,
        room_type_id=room_type_id,
        q=q,
        order_no=order_no,
        external_order_no=external_order_no,
        reception_no=reception_no,
        room_no=room_no,
        guest_name=guest_name,
        phone=phone,
        note=note,
        page=1,
        page_size=5000,
    )
    return items
