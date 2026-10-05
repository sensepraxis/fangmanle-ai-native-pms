# SPDX-License-Identifier: Apache-2.0
"""自然语言客群查询：种子灌入。

NL 解析与候选查询已抽到 `guests.nl_filter`；本文件保留标签种子与近 90 天取消/复购
演示订单灌入函数（`ensure_business_tag` / `ensure_family_repeat_tags` /
`_assign_tag` / `seed_nl_cancel_demo`）。

关联键：orders.guest_id → guests.id（会员主档 OneID）。
本店范围：orders.hotel_id。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from guests.nl_filter import CANCEL_PREFIX, STAY_PREFIX, parse_nl_to_filter
from models import (
    Channel,
    Guest,
    GuestTag,
    Hotel,
    Order,
    OrderItem,
    Room,
    RoomType,
    TagDefinition,
)


def ensure_business_tag(db: Session) -> TagDefinition | None:
    t = db.query(TagDefinition).filter_by(code="business").first()
    if t:
        return t
    t = TagDefinition(
        code="business", name="商务常旅客", category="画像", rule_expr="工作日入住占比 > 70%", is_active=True
    )
    db.add(t)
    db.flush()
    return t


def ensure_family_repeat_tags(db: Session) -> dict[str, TagDefinition]:
    out = {}
    for code, name, cat, rule in [
        ("family", "亲子家庭", "画像", "历史携儿童订单 ≥ 2"),
        ("repeat", "复购客", "忠诚度", "180 天内订单 ≥ 5"),
        ("pref_quiet_high_floor", "偏好高层安静房", "画像", "review:quiet AND pref:high_floor"),
    ]:
        t = db.query(TagDefinition).filter_by(code=code).first()
        if not t:
            t = TagDefinition(code=code, name=name, category=cat, rule_expr=rule, is_active=True)
            db.add(t)
            db.flush()
        out[code] = t
    return out


def _assign_tag(db: Session, guest_id: int, tag: TagDefinition) -> None:
    exists = db.query(GuestTag).filter_by(guest_id=guest_id, tag_id=tag.id).first()
    if not exists:
        db.add(GuestTag(guest_id=guest_id, tag_id=tag.id, confidence=0.95, source="nl_seed"))


def seed_nl_cancel_demo(db: Session, hotel_id: int | None = None) -> dict[str, int]:
    """
    幂等补种：近 90 天取消单，挂到带「商务」标签的客人（orders.guest_id 打通 CRM）。
    同时补亲子/复购实住单，支撑「三次以上+亲子+高层」类查询。
    """
    biz = ensure_business_tag(db)
    extra = ensure_family_repeat_tags(db)
    hotels = db.query(Hotel).all()
    targets = [h for h in hotels if hotel_id is None or h.id == hotel_id]
    added_cx = added_st = tagged = 0

    for h in targets:
        # 已种过则跳过该店取消单
        existing_cx = (
            db.query(func.count(Order.id))
            .filter(Order.hotel_id == h.id, Order.order_no.like(f"{CANCEL_PREFIX}%"))
            .scalar()
            or 0
        )
        rts = db.query(RoomType).filter_by(hotel_id=h.id).all()
        ch = db.query(Channel).filter_by(is_active=True).first()
        guests = db.query(Guest).order_by(Guest.ltv.desc()).limit(100).all()
        if not rts or not guests:
            continue
        rt = rts[0]
        ch_id = ch.id if ch else None

        # 选 28 个客人打商务标 + 取消单
        biz_guests = guests[:28]
        for i, g in enumerate(biz_guests):
            _assign_tag(db, g.id, biz)
            tagged += 1
            if existing_cx >= 20:
                continue
            # 每人 1～2 张近 90 天取消单
            for j in range(1 + (i % 2)):
                day_ago = 5 + (i * 3 + j * 7) % 85
                ci = date.today() - timedelta(days=day_ago)
                co = ci + timedelta(days=1 + (i % 3))
                ono = f"{CANCEL_PREFIX}{h.id}-{g.id}-{j}"
                if db.query(Order).filter_by(order_no=ono).first():
                    continue
                amt = round(float(rt.base_price or 400) * (1 + (i % 5) * 0.1), 2)
                o = Order(
                    hotel_id=h.id,
                    order_no=ono,
                    guest_id=g.id,
                    channel_id=ch_id,
                    room_type_id=rt.id,
                    check_in=ci,
                    check_out=co,
                    nights=(co - ci).days,
                    rooms=1,
                    adults=1,
                    children=0,
                    total_amount=amt,
                    status="cancelled",
                    payment_status="unpaid",
                    note="NL客群·取消单",
                    created_at=datetime.combine(ci, datetime.min.time()) + timedelta(hours=10),
                )
                db.add(o)
                db.flush()
                db.add(
                    OrderItem(
                        order_id=o.id,
                        item_type="room",
                        description=f"{rt.name}·取消",
                        qty=1,
                        unit_price=amt,
                        amount=amt,
                    )
                )
                added_cx += 1

        # 亲子+复购：另选客人补实住单（去年三次以上、带孩）
        existing_st = (
            db.query(func.count(Order.id))
            .filter(Order.hotel_id == h.id, Order.order_no.like(f"{STAY_PREFIX}%"))
            .scalar()
            or 0
        )
        fam_guests = guests[28:48] if len(guests) > 48 else guests[:20]
        rooms = db.query(Room).filter_by(hotel_id=h.id).order_by(Room.room_no).all()
        high_rooms = [
            r
            for r in rooms
            if (r.floor and int(r.floor or 0) >= 8) or (str(r.room_no or "").isdigit() and int(r.room_no) >= 800)
        ]
        if existing_st < 40:
            for i, g in enumerate(fam_guests):
                _assign_tag(db, g.id, extra["family"])
                _assign_tag(db, g.id, extra["repeat"])
                if i % 2 == 0:
                    _assign_tag(db, g.id, extra["pref_quiet_high_floor"])
                tagged += 1
                for j in range(3):  # 至少三次入住
                    day_ago = 40 + i * 5 + j * 30
                    if day_ago > 350:
                        day_ago = 60 + j * 40
                    ci = date.today() - timedelta(days=day_ago)
                    co = ci + timedelta(days=2)
                    ono = f"{STAY_PREFIX}{h.id}-{g.id}-{j}"
                    if db.query(Order).filter_by(order_no=ono).first():
                        continue
                    amt = round(float(rt.base_price or 450) * 2, 2)
                    o = Order(
                        hotel_id=h.id,
                        order_no=ono,
                        guest_id=g.id,
                        channel_id=ch_id,
                        room_type_id=rt.id,
                        check_in=ci,
                        check_out=co,
                        nights=2,
                        rooms=1,
                        adults=2,
                        children=1,
                        total_amount=amt,
                        status="checked_out",
                        payment_status="paid",
                        note="NL客群·亲子复购",
                        created_at=datetime.combine(ci, datetime.min.time()) + timedelta(hours=14),
                    )
                    db.add(o)
                    db.flush()
                    db.add(
                        OrderItem(
                            order_id=o.id,
                            item_type="room",
                            description=f"{rt.name}·亲子",
                            qty=2,
                            unit_price=amt / 2,
                            amount=amt,
                        )
                    )
                    # 尽量排高层房
                    if high_rooms:
                        from models import Reservation

                        rm = high_rooms[i % len(high_rooms)]
                        if not db.query(Reservation).filter_by(order_id=o.id).first():
                            db.add(Reservation(order_id=o.id, room_id=rm.id))
                    added_st += 1

    db.commit()
    return {"cancel_orders_added": added_cx, "stay_orders_added": added_st, "tags_assigned": tagged}
