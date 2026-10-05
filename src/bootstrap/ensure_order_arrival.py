# SPDX-License-Identifier: Apache-2.0
"""订单到店时刻字段 + 近几日到店数据（与客户全景日历联动）。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models import Channel, Guest, Hotel, Order, OrderItem, Reservation, Room, RoomType


def ensure_order_arrival_schema(engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("orders"):
        return
    cols = {c["name"] for c in insp.get_columns("orders")}
    if "arrival_time" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE orders ADD COLUMN arrival_time VARCHAR(5)"))


def seed_arrival_calendar_demo(db: Session, hotel_id: int | None = None) -> dict:
    """为近 7 日写入可的到店订单：含 check_in、arrival_time、房号、状态。"""
    hotels = db.query(Hotel).all()
    targets = [h for h in hotels if hotel_id is None or h.id == hotel_id]
    added = updated = assigned = 0
    today = date.today()

    # 相对今天的到店分布（人数），日历条会明显起伏
    day_specs: list[tuple[int, list[dict]]] = [
        (
            -3,
            [
                {"time": "13:00", "status": "checked_out", "nights": 1},
                {"time": "15:30", "status": "checked_out", "nights": 1},
            ],
        ),
        (
            -2,
            [
                {"time": "12:30", "status": "checked_out", "nights": 1},
                {"time": "14:00", "status": "checked_in", "nights": 2},
                {"time": "16:00", "status": "checked_in", "nights": 3},
            ],
        ),
        (
            -1,
            [
                {"time": "11:00", "status": "checked_in", "nights": 2},
                {"time": "13:40", "status": "checked_in", "nights": 2},
                {"time": "15:10", "status": "checked_in", "nights": 3},
                {"time": "18:00", "status": "checked_in", "nights": 1},
            ],
        ),
        (
            0,
            [
                {"time": "11:30", "status": "checked_in", "nights": 2, "vip": True},
                {"time": "13:00", "status": "confirmed", "nights": 2},
                {"time": "14:30", "status": "confirmed", "nights": 3, "vip": True},
                {"time": "15:45", "status": "pending", "nights": 1},
                {"time": "17:20", "status": "confirmed", "nights": 2},
                {"time": "19:00", "status": "pending", "nights": 1},
            ],
        ),
        (
            1,
            [
                {"time": "12:00", "status": "confirmed", "nights": 2},
                {"time": "14:00", "status": "pending", "nights": 1},
                {"time": "16:30", "status": "confirmed", "nights": 3},
                {"time": "18:00", "status": "pending", "nights": 2},
            ],
        ),
        (
            2,
            [
                {"time": "13:15", "status": "pending", "nights": 2},
                {"time": "15:00", "status": "confirmed", "nights": 1},
                {"time": "17:40", "status": "pending", "nights": 2},
            ],
        ),
        (
            3,
            [
                {"time": "14:00", "status": "pending", "nights": 1},
                {"time": "16:00", "status": "pending", "nights": 2},
            ],
        ),
    ]

    for h in targets:
        rts = db.query(RoomType).filter_by(hotel_id=h.id).all()
        rooms = db.query(Room).filter_by(hotel_id=h.id).order_by(Room.room_no).all()
        ch = db.query(Channel).filter_by(is_active=True).first()
        guests = db.query(Guest).order_by(Guest.ltv.desc()).limit(80).all()
        if not rts or not rooms or not guests:
            continue

        # 先给已有「窗口内」订单补齐 arrival_time / 房号 / 合理状态
        win_start = today - timedelta(days=3)
        win_end = today + timedelta(days=3)
        existing = (
            db.query(Order)
            .filter(
                Order.hotel_id == h.id,
                Order.check_in >= win_start,
                Order.check_in <= win_end,
                Order.guest_id.isnot(None),
            )
            .order_by(Order.check_in, Order.id)
            .all()
        )
        used_rooms: set[int] = set()
        for res in db.query(Reservation).join(Order).filter(Order.hotel_id == h.id).all():
            if res.room_id:
                used_rooms.add(res.room_id)

        time_pool = ["11:00", "12:30", "14:00", "15:30", "17:00", "18:30"]
        for i, o in enumerate(existing):
            if not o.arrival_time:
                o.arrival_time = time_pool[i % len(time_pool)]
                updated += 1
            if o.check_in == today and (o.status or "") == "pending":
                o.status = "confirmed"
                updated += 1
            has_res = db.query(Reservation).filter_by(order_id=o.id).first()
            if not has_res and o.status in ("checked_in", "confirmed", "pending"):
                free = next((r for r in rooms if r.id not in used_rooms), None)
                if free:
                    db.add(Reservation(order_id=o.id, room_id=free.id))
                    used_rooms.add(free.id)
                    if o.status == "checked_in":
                        free.status = "occupied"
                    assigned += 1

        # 按日补足「专用」订单（带 DEMO-ARR 前缀，可幂等）
        guest_idx = 0
        for offset, specs in day_specs:
            d = today + timedelta(days=offset)
            marker = f"DEMO-ARR-{h.id}-{d.strftime('%m%d')}"
            have = db.query(Order).filter(Order.order_no.like(f"{marker}%")).count()
            need = max(0, len(specs) - have)
            for j in range(need):
                spec = specs[have + j]
                g = guests[guest_idx % len(guests)]
                guest_idx += 1
                if spec.get("vip"):
                    g.vip_level = "gold"
                rt = rts[(guest_idx + j) % len(rts)]
                nights = int(spec["nights"])
                order_no = f"{marker}-{have + j + 1:02d}"
                rate = float(rt.base_price or 388)
                total = round(rate * nights, 2)
                status = spec["status"]
                o = Order(
                    hotel_id=h.id,
                    order_no=order_no,
                    guest_id=g.id,
                    channel_id=ch.id if ch else None,
                    room_type_id=rt.id,
                    check_in=d,
                    check_out=d + timedelta(days=nights),
                    nights=nights,
                    rooms=1,
                    adults=1,
                    children=0,
                    total_amount=total,
                    status=status,
                    payment_status="paid" if status in ("checked_in", "confirmed") else "unpaid",
                    arrival_time=spec["time"],
                    note=f"到店 · 预计 {spec['time']}",
                )
                db.add(o)
                db.flush()
                db.add(
                    OrderItem(
                        order_id=o.id,
                        item_type="room",
                        description=f"{rt.name} ×{nights}晚",
                        qty=nights,
                        unit_price=rate,
                        amount=total,
                    )
                )
                free = next((r for r in rooms if r.id not in used_rooms), None)
                if free:
                    db.add(Reservation(order_id=o.id, room_id=free.id))
                    used_rooms.add(free.id)
                    if status == "checked_in":
                        free.status = "occupied"
                    assigned += 1
                added += 1

    db.commit()
    return {"orders_added": added, "orders_updated": updated, "rooms_assigned": assigned}
