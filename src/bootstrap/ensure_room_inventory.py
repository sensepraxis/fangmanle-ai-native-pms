# SPDX-License-Identifier: Apache-2.0
"""按日×房间库存表：建表 + 从订单/分房/当前房态物化。"""

from datetime import date, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models import (
    Base,
    Guest,
    Hotel,
    Order,
    Reservation,
    Room,
    RoomNightInventory,
    RoomType,
)


def ensure_room_inventory_schema(engine):
    insp = inspect(engine)
    if "room_night_inventory" not in set(insp.get_table_names()):
        RoomNightInventory.__table__.create(bind=engine, checkfirst=True)
        return
    # 旧空表无需改列时直接返回
    cols = {c["name"] for c in insp.get_columns("room_night_inventory")}
    need = {"hotel_id", "room_id", "biz_date", "status", "order_id", "source"}
    if not need.issubset(cols):
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS room_night_inventory"))
        RoomNightInventory.__table__.create(bind=engine, checkfirst=True)


def rebuild_room_night_inventory(
    db: Session,
    hotel_id: int,
    days: int = 14,
    start: date | None = None,
) -> int:
    """按营业日物化每间房库存到 room_night_inventory（覆盖窗口内旧行）。"""
    days = max(1, min(120, int(days or 14)))
    start = start or date.today()
    end = start + timedelta(days=days - 1)

    db.query(RoomNightInventory).filter(
        RoomNightInventory.hotel_id == hotel_id,
        RoomNightInventory.biz_date >= start,
        RoomNightInventory.biz_date <= end,
    ).delete(synchronize_session=False)

    room_rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id)
        .order_by(Room.room_no)
        .all()
    )
    if not room_rows:
        db.commit()
        return 0

    rooms = []
    by_type: dict = {}
    for r, rt in room_rows:
        item = {
            "id": r.id,
            "room_type_id": r.room_type_id,
            "status": r.status,
            "blocked": r.status in ("ooo", "maintenance"),
        }
        rooms.append(item)
        by_type.setdefault(r.room_type_id, []).append(item)

    # (date, room_id) -> row dict
    grid: dict = {}
    for i in range(days):
        d = start + timedelta(days=i)
        for r in rooms:
            if r["blocked"]:
                grid[(d, r["id"])] = {
                    "status": "blocked",
                    "source": "ooo",
                    "order_id": None,
                    "guest_name": None,
                    "order_no": None,
                    "check_in": None,
                    "check_out": None,
                }
            else:
                grid[(d, r["id"])] = {
                    "status": "available",
                    "source": "derived",
                    "order_id": None,
                    "guest_name": None,
                    "order_no": None,
                    "check_in": None,
                    "check_out": None,
                }

    def mark_sold(d0: date, room_id: int, meta: dict):
        key = (d0, room_id)
        cur = grid.get(key)
        if not cur or cur["status"] == "blocked":
            return False
        if cur["status"] == "sold":
            return False
        cur.update(meta)
        cur["status"] = "sold"
        return True

    # 1) 真实分房
    assigned = (
        db.query(Reservation, Order, Guest)
        .join(Order, Reservation.order_id == Order.id)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed", "checked_in")),
            Order.check_in <= end,
            Order.check_out > start,
            Reservation.room_id.isnot(None),
        )
        .all()
    )
    for res, od, g in assigned:
        meta = {
            "source": "reservation",
            "order_id": od.id,
            "guest_name": g.name if g else None,
            "order_no": od.order_no,
            "check_in": od.check_in,
            "check_out": od.check_out,
        }
        d = max(od.check_in, start)
        while d < od.check_out and d <= end:
            mark_sold(d, res.room_id, meta)
            d += timedelta(days=1)

    # 2) 今日 occupied 房态兜底
    for r in rooms:
        if r["status"] == "occupied":
            mark_sold(
                start,
                r["id"],
                {
                    "source": "room_status",
                    "order_id": None,
                    "guest_name": None,
                    "order_no": None,
                    "check_in": None,
                    "check_out": None,
                },
            )

    # 3) 未分房订单：贪心占房并写入日库存（source=order_hold）
    unassigned = (
        db.query(Order, Guest)
        .outerjoin(Guest, Order.guest_id == Guest.id)
        .outerjoin(Reservation, Reservation.order_id == Order.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed")),
            Order.check_in <= end,
            Order.check_out > start,
            Reservation.id.is_(None),
        )
        .order_by(Order.check_in, Order.id)
        .all()
    )
    for od, g in unassigned:
        need = max(1, int(od.rooms or 1))
        candidates = [x for x in by_type.get(od.room_type_id, []) if not x["blocked"]]
        if not candidates:
            candidates = [x for x in rooms if not x["blocked"]]
        for _ in range(need):
            chosen = None
            for cand in candidates:
                ok = True
                d = max(od.check_in, start)
                while d < od.check_out and d <= end:
                    cell = grid.get((d, cand["id"]))
                    if not cell or cell["status"] != "available":
                        ok = False
                        break
                    d += timedelta(days=1)
                if ok:
                    chosen = cand
                    break
            if not chosen:
                break
            meta = {
                "source": "order_hold",
                "order_id": od.id,
                "guest_name": g.name if g else None,
                "order_no": od.order_no,
                "check_in": od.check_in,
                "check_out": od.check_out,
            }
            d = max(od.check_in, start)
            while d < od.check_out and d <= end:
                mark_sold(d, chosen["id"], meta)
                d += timedelta(days=1)

    rows = []
    for (d, room_id), cell in grid.items():
        rows.append(
            RoomNightInventory(
                hotel_id=hotel_id,
                room_id=room_id,
                biz_date=d,
                status=cell["status"],
                order_id=cell.get("order_id"),
                guest_name=cell.get("guest_name"),
                order_no=cell.get("order_no"),
                check_in=cell.get("check_in"),
                check_out=cell.get("check_out"),
                source=cell.get("source") or "derived",
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def ensure_hotel_nights(
    db: Session,
    hotel_id: int,
    days: int = 14,
    start: date | None = None,
) -> None:
    """窗口内缺行或过期则重建。"""
    days = max(1, min(120, int(days or 14)))
    start = start or date.today()
    end = start + timedelta(days=days - 1)
    room_n = db.query(Room).filter_by(hotel_id=hotel_id).count()
    if room_n <= 0:
        return
    expect = room_n * days
    have = (
        db.query(RoomNightInventory)
        .filter(
            RoomNightInventory.hotel_id == hotel_id,
            RoomNightInventory.biz_date >= start,
            RoomNightInventory.biz_date <= end,
        )
        .count()
    )
    # 允许少量误差；缺一大块就重建
    if have < expect * 0.9:
        rebuild_room_night_inventory(db, hotel_id, days, start=start)
