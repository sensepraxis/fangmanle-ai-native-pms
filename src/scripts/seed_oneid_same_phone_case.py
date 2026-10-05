# SPDX-License-Identifier: Apache-2.0
"""创建同号冲突案例：林晓 / 林小（手机同为 13987654321，非董文）。

含订单、渠道身份、优惠券、待处理 OneID 冲突单，供 Wizard 闭环。
可重复执行（幂等）。
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bootstrap.ensure_wecom import ensure_wecom_schema
from database import SessionLocal, engine
from guests.phone_utils import _normalize_phone_storage, _phone_last6, find_guests_by_phone_exact
from infra.auth_local import DEFAULT_HOTEL_ID
from models import (
    Channel,
    Guest,
    GuestCoupon,
    GuestIdentity,
    Hotel,
    OneIdMergeEvent,
    OneIdPhoneConflict,
    Order,
    OrderItem,
    RoomType,
    WecomBindTicket,
)

PHONE = "13987654321"
CASE_TAG = "oneid_same_phone_case_v1"
EXTERNAL = "wmDEMO_LIN_SAMEPHONE_001"
FOLLOW = "WangWeiWei"


def _ensure_guest(db, *, name: str, gender: str, vip: str, city: str, ltv: str, one_suffix: str) -> Guest:
    phone = _normalize_phone_storage(PHONE)
    for g in find_guests_by_phone_exact(db, phone):
        if g.name == name:
            g.phone = phone
            g.vip_level = vip
            g.ltv = Decimal(ltv)
            g.city = city
            g.gender = gender
            return g
    g = Guest(
        one_id=f"ONE-{one_suffix}-{int(datetime.now().timestamp()) % 100000}",
        name=name,
        phone=phone,
        gender=gender,
        vip_level=vip,
        city=city,
        ltv=Decimal(ltv),
        churn_risk=Decimal("0.22"),
    )
    db.add(g)
    db.flush()
    return g


def _add_order(db, guest: Guest, hotel_id: int, *, days_ago: int, nights: int, status: str, amount: float, note: str):
    exists = db.query(Order).filter(Order.guest_id == guest.id, Order.note.like(f"%{CASE_TAG}%")).count()
    # allow multiple but skip if this exact note exists
    if db.query(Order).filter(Order.guest_id == guest.id, Order.note == note).first():
        return
    hotel = db.get(Hotel, hotel_id) or db.query(Hotel).order_by(Hotel.id.asc()).first()
    rt = db.query(RoomType).filter_by(hotel_id=hotel.id).order_by(RoomType.base_price.desc()).first()
    ch = db.query(Channel).first()
    ci = date.today() - timedelta(days=days_ago)
    o = Order(
        hotel_id=hotel.id,
        order_no=f"ORD-LIN-{guest.id}-{ci.strftime('%m%d')}-{secrets.token_hex(2)}",
        guest_id=guest.id,
        channel_id=ch.id if ch else None,
        room_type_id=rt.id if rt else None,
        check_in=ci,
        check_out=ci + timedelta(days=nights),
        nights=nights,
        rooms=1,
        adults=1,
        children=0,
        total_amount=amount,
        status=status,
        payment_status="paid" if status == "checked_out" else "partial",
        note=note,
    )
    db.add(o)
    db.flush()
    if rt:
        db.add(
            OrderItem(
                order_id=o.id,
                item_type="room",
                description=f"{rt.name} x{nights}晚",
                qty=nights,
                unit_price=Decimal(str(round(amount / max(nights, 1), 2))),
                amount=Decimal(str(amount)),
            )
        )


def _ensure_identity(db, guest: Guest, source: str, external_id: str, method: str):
    row = db.query(GuestIdentity).filter_by(guest_id=guest.id, source=source, external_id=external_id).first()
    if row:
        return
    db.add(
        GuestIdentity(
            guest_id=guest.id,
            source=source,
            external_id=external_id,
            confidence=Decimal("0.96"),
            is_primary=True,
            merge_method=method,
            matched_by="系统脚本",
            linked_at=datetime.now(),
        )
    )


def _ensure_coupon(db, guest: Guest, hotel_id: int, code: str, name: str):
    if db.query(GuestCoupon).filter_by(code=code).first():
        return
    # clear unique (guest, source, type) if needed
    old = db.query(GuestCoupon).filter_by(guest_id=guest.id, source="wecom_scan", coupon_type="room_rate").first()
    if old:
        return
    now = datetime.now()
    db.add(
        GuestCoupon(
            hotel_id=hotel_id,
            guest_id=guest.id,
            code=code,
            name=name,
            recipient_name=guest.name,
            channel="企业微信",
            coupon_type="room_rate",
            discount_rate=Decimal("0.850"),
            source="manual_seed",
            status="active",
            redeem_status="unused",
            valid_from=now,
            valid_until=now + timedelta(days=180),
            note=CASE_TAG,
        )
    )


def main() -> None:
    ensure_wecom_schema(engine)
    db = SessionLocal()
    try:
        hotel_id = DEFAULT_HOTEL_ID
        phone = _normalize_phone_storage(PHONE)
        last6 = _phone_last6(phone)

        a = _ensure_guest(
            db,
            name="林晓",
            gender="F",
            vip="gold",
            city="杭州",
            ltv="12680.00",
            one_suffix="LX",
        )
        b = _ensure_guest(
            db,
            name="林小",
            gender="F",
            vip="silver",
            city="杭州",
            ltv="3180.00",
            one_suffix="LXO",
        )

        _add_order(
            db,
            a,
            hotel_id,
            days_ago=40,
            nights=2,
            status="checked_out",
            amount=1680,
            note=f"{CASE_TAG} · 林晓历史入住 #1",
        )
        _add_order(
            db,
            a,
            hotel_id,
            days_ago=-5,
            nights=2,
            status="confirmed",
            amount=1580,
            note=f"{CASE_TAG} · 林晓待入住 #2",
        )
        _add_order(
            db,
            b,
            hotel_id,
            days_ago=120,
            nights=1,
            status="checked_out",
            amount=780,
            note=f"{CASE_TAG} · 林小历史入住 #1",
        )

        _ensure_identity(db, a, "ota", f"ctrip_lin_{a.id}", "order_match")
        _ensure_identity(db, a, "direct", f"web_lin_{a.id}", "primary_bind")
        _ensure_identity(db, b, "douyin", f"dy_lin_{b.id}", "order_match")
        _ensure_identity(db, b, "meituan", f"mt_lin_{b.id}", "order_match")

        _ensure_coupon(db, a, hotel_id, f"CASE-LX-{a.id}", "同号案例 · 房费85折券")
        _ensure_coupon(db, b, hotel_id, f"CASE-LXO-{b.id}", "同号案例 · 延迟退房券")

        for g, note in (
            (a, f"前台建档：林晓 · {phone} · {CASE_TAG}"),
            (b, f"前台建档：林小 · {phone} · {CASE_TAG}"),
        ):
            if (
                not db.query(OneIdMergeEvent)
                .filter(
                    OneIdMergeEvent.guest_id == g.id,
                    OneIdMergeEvent.note.like(f"%{CASE_TAG}%"),
                )
                .first()
            ):
                db.add(
                    OneIdMergeEvent(
                        guest_id=g.id,
                        action="oneid_born",
                        source="direct",
                        confidence=Decimal("1.0"),
                        merge_method="manual_seed",
                        operator="系统脚本",
                        note=note,
                        occurred_at=datetime.now(),
                    )
                )

        # bind ticket + pending conflict
        ticket = (
            db.query(WecomBindTicket).filter_by(external_userid=EXTERNAL).order_by(WecomBindTicket.id.desc()).first()
        )
        if not ticket:
            ticket = WecomBindTicket(
                hotel_id=hotel_id,
                token=secrets.token_urlsafe(24),
                external_userid=EXTERNAL,
                follow_userid=FOLLOW,
                nickname="林晓微信",
                state="lobby",
                status="conflict",
                phone_submitted=phone,
                welcome_sent=True,
                welcome_mode="link_only",
                error_message=f"全号匹配 2 位客人，待 OneID 人工 · {CASE_TAG}",
                expires_at=datetime.now() + timedelta(days=30),
            )
            db.add(ticket)
            db.flush()
        else:
            ticket.status = "conflict"
            ticket.guest_id = None
            ticket.phone_submitted = phone
            ticket.error_message = f"全号匹配 2 位客人，待 OneID 人工 · {CASE_TAG}"
            ticket.bound_at = None

        conflict = (
            db.query(OneIdPhoneConflict)
            .filter(
                OneIdPhoneConflict.status == "pending",
                OneIdPhoneConflict.external_userid == EXTERNAL,
            )
            .order_by(OneIdPhoneConflict.id.desc())
            .first()
        )
        if not conflict:
            conflict = OneIdPhoneConflict(
                hotel_id=hotel_id,
                status="pending",
                phone_submitted=phone,
                phone_last4=last6,
                match_type="phone_exact_multi",
                external_userid=EXTERNAL,
                nickname="林晓微信",
                follow_userid=FOLLOW,
                bind_ticket_id=ticket.id,
                candidate_guest_ids_json=json.dumps([a.id, b.id]),
                note=f"案例：全号重复 {phone} · {CASE_TAG}",
            )
            db.add(conflict)
        else:
            conflict.phone_submitted = phone
            conflict.phone_last4 = last6
            conflict.match_type = "phone_exact_multi"
            conflict.candidate_guest_ids_json = json.dumps([a.id, b.id])
            conflict.bind_ticket_id = ticket.id
            conflict.note = f"案例：全号重复 {phone} · {CASE_TAG}"

        db.commit()
        print(
            json.dumps(
                {
                    "ok": True,
                    "phone": phone,
                    "guest_a": {"id": a.id, "name": a.name, "vip": a.vip_level, "ltv": float(a.ltv or 0)},
                    "guest_b": {"id": b.id, "name": b.name, "vip": b.vip_level, "ltv": float(b.ltv or 0)},
                    "conflict_id": conflict.id,
                    "ticket_token": ticket.token,
                    "next": [
                        "全景搜 林晓/林小 或 13987654321",
                        "OneID归并台 → 冲突 #… → 归并到林晓并发券",
                        "或 Wizard：冲突队列 → 归并审核 → 资产确认",
                    ],
                },
                ensure_ascii=False,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
