# SPDX-License-Identifier: Apache-2.0
"""为营收预测补齐 2026-09-01 ~ 2026-09-10 交易数据。

覆盖：已退房 / 在住 / 预订确认 / 待入住 / 未到店 / 取消 / 多间 / 团队。
对应客人挂标签与渠道身份，可在用户画像中查看。
幂等：按 note 标记 CASE_TAG 去重；夜审按 hotel+biz_date upsert。
"""

from __future__ import annotations

import os
import secrets
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from infra.auth_local import DEFAULT_HOTEL_ID
from infra.id_doc_crypto import pack_phone_fields
from models import (
    Channel,
    Guest,
    GuestIdentity,
    GuestTag,
    Hotel,
    NightAuditLog,
    Order,
    OrderItem,
    Payment,
    RoomType,
    TagDefinition,
)

CASE_TAG = "sept_forecast_demo_v1"
YEAR = 2026


def _d(m: int, day: int, year: int = YEAR) -> date:
    return date(year, m, day)


GUESTS = [
    # name, phone, vip, city, ltv, churn, gender, tags, identity_source
    ("赵明远", "13820090101", "gold", "上海", "18600", "0.18", "男", ["business", "high_value", "repeat"], "ctrip"),
    ("陈思雨", "13920090102", "silver", "杭州", "9200", "0.25", "女", ["family", "active_90d"], "meituan"),
    (
        "周启航",
        "13720090103",
        "platinum",
        "北京",
        "42800",
        "0.12",
        "男",
        ["vip", "business", "high_value"],
        "agreement",
    ),
    ("林婉清", "13620090104", "normal", "苏州", "3600", "0.41", "女", ["price_sensitive", "douyin_fan"], "douyin"),
    ("韩冬生", "13520090105", "gold", "南京", "15400", "0.22", "男", ["business", "pref_quiet_high_floor"], "direct"),
    ("许晓彤", "13420090106", "silver", "无锡", "7800", "0.33", "女", ["xhs_fan", "repeat"], "xiaohongshu"),
    ("郑立成", "13320090107", "normal", "合肥", "2100", "0.55", "男", ["complaint_risk"], "ota"),
    ("孙嘉怡", "13220090108", "gold", "宁波", "11200", "0.20", "女", ["family", "vip"], "wechat"),
    ("吴博文", "13120090109", "normal", "常州", "4500", "0.38", "男", ["business"], "fliggy"),
    ("何雨萱", "13020090110", "silver", "嘉兴", "6700", "0.28", "女", ["repeat", "active_90d"], "wecom"),
]


def _note(key: str) -> str:
    return f"{CASE_TAG}|{key}"


def _ensure_guest(db, hotel_id: int, spec: tuple) -> Guest:
    name, phone, vip, city, ltv, churn, gender, tags, src = spec
    packed = pack_phone_fields(phone, hotel_id)
    existing = db.query(Guest).filter(Guest.name == name, Guest.phone_mask == packed["phone_mask"]).first()
    if existing:
        g = existing
        g.vip_level = vip
        g.city = city
        g.ltv = Decimal(ltv)
        g.churn_risk = Decimal(churn)
        g.gender = gender
    else:
        g = Guest(
            one_id=f"ONE-SEPT-{phone[-4:]}-{secrets.token_hex(2).upper()}",
            name=name,
            gender=gender,
            vip_level=vip,
            city=city,
            ltv=Decimal(ltv),
            churn_risk=Decimal(churn),
            birthday=date(1990 + (int(phone[-2:]) % 15), (int(phone[-1]) % 12) + 1, 10),
            phone=packed["phone"],
            phone_cipher=packed["phone_cipher"],
            phone_mask=packed["phone_mask"],
            phone_hash=packed["phone_hash"],
        )
        db.add(g)
        db.flush()

    tag_defs = {t.code: t for t in db.query(TagDefinition).filter(TagDefinition.code.in_(tags)).all()}
    for code in tags:
        td = tag_defs.get(code)
        if not td:
            continue
        if not db.query(GuestTag).filter_by(guest_id=g.id, tag_id=td.id).first():
            db.add(GuestTag(guest_id=g.id, tag_id=td.id, confidence=Decimal("0.92"), source="seed"))

    ext = f"SEPT-{src.upper()}-{phone[-4:]}"
    if not db.query(GuestIdentity).filter_by(guest_id=g.id, source=src, external_id=ext).first():
        db.add(
            GuestIdentity(
                guest_id=g.id,
                source=src,
                external_id=ext,
                confidence=Decimal("0.95"),
                is_primary=True,
                merge_method="phone",
                matched_by="seed_sept_forecast",
            )
        )
    return g


def _channel_map(db) -> dict[str, int]:
    return {c.code: c.id for c in db.query(Channel).all()}


def _room_types(db, hotel_id: int) -> dict[str, RoomType]:
    return {rt.code: rt for rt in db.query(RoomType).filter_by(hotel_id=hotel_id).all()}


def _add_order(
    db,
    *,
    hotel_id: int,
    guest: Guest,
    key: str,
    check_in: date,
    check_out: date,
    status: str,
    payment_status: str,
    rt: RoomType,
    channel_id: Optional[int],
    rooms: int = 1,
    adults: int = 1,
    children: int = 0,
    order_type: int = 1,
    adr: Optional[float] = None,
    arrival_time: Optional[str] = None,
    group_name: Optional[str] = None,
    extra_note: str = "",
) -> Optional[Order]:
    note = _note(key)
    if db.query(Order).filter(Order.note == note).first():
        return None

    nights = max(1, (check_out - check_in).days)
    unit = float(adr if adr is not None else (rt.base_price or 400))
    total = round(unit * nights * rooms, 2)
    o = Order(
        hotel_id=hotel_id,
        order_no=f"SEPT-{check_in.strftime('%m%d')}-{key[-6:]}-{secrets.token_hex(2).upper()}",
        guest_id=guest.id,
        channel_id=channel_id,
        room_type_id=rt.id,
        order_type=order_type,
        one_id=guest.one_id,
        guest_phone=guest.phone_mask or guest.phone,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        rooms=rooms,
        adults=adults,
        children=children,
        total_amount=Decimal(str(total)),
        status=status,
        payment_status=payment_status,
        arrival_time=arrival_time,
        group_name=group_name,
        note=f"{note} {extra_note}".strip(),
        deposit_amount=Decimal(str(round(unit * 0.3, 2))) if status in ("confirmed", "checked_in", "pending") else 0,
    )
    db.add(o)
    db.flush()
    db.add(
        OrderItem(
            order_id=o.id,
            item_type="room",
            description=f"{rt.name} ×{nights}晚×{rooms}间",
            qty=nights * rooms,
            unit_price=Decimal(str(unit)),
            amount=Decimal(str(total)),
        )
    )
    if payment_status in ("paid", "partial") and status not in ("cancelled",):
        paid = total if payment_status == "paid" else round(total * 0.4, 2)
        db.add(
            Payment(
                hotel_id=hotel_id,
                order_id=o.id,
                method="wechat_pos" if payment_status == "paid" else "deposit_offset",
                amount=Decimal(str(paid)),
                received_amount=Decimal(str(paid)),
                settle_type="full" if payment_status == "paid" else "partial",
                paid_at=datetime.combine(check_in, datetime.min.time()) + timedelta(hours=15),
                note=CASE_TAG,
            )
        )
    return o


def _upsert_audit(db, hotel_id: int, biz_date: date, revenue: float, room_nights: int, exceptions: int = 0):
    row = db.query(NightAuditLog).filter_by(hotel_id=hotel_id, biz_date=biz_date).first()
    if row:
        row.status = "passed"
        row.revenue = Decimal(str(revenue))
        row.room_nights = room_nights
        row.exceptions = exceptions
        row.ran_at = datetime.combine(biz_date, datetime.min.time()) + timedelta(hours=23, minutes=50)
    else:
        db.add(
            NightAuditLog(
                hotel_id=hotel_id,
                biz_date=biz_date,
                status="passed",
                revenue=Decimal(str(revenue)),
                room_nights=room_nights,
                exceptions=exceptions,
                ran_at=datetime.combine(biz_date, datetime.min.time()) + timedelta(hours=23, minutes=50),
            )
        )


def seed(hotel_id: int = DEFAULT_HOTEL_ID) -> dict:
    db = SessionLocal()
    try:
        hotel = db.get(Hotel, hotel_id) or db.query(Hotel).order_by(Hotel.id.asc()).first()
        if not hotel:
            raise RuntimeError("未找到酒店，请先用 deploy/dev 或 seed 灌库")
        hotel_id = hotel.id
        ch = _channel_map(db)
        rts = _room_types(db, hotel_id)
        if not rts:
            raise RuntimeError("未找到房型")

        guests = [_ensure_guest(db, hotel_id, spec) for spec in GUESTS]
        g = {guest.name: guest for guest in guests}

        biz = rts.get("biz-twin") or next(iter(rts.values()))
        deluxe = rts.get("deluxe-king") or biz
        suite = rts.get("exec-suite") or deluxe
        family = rts.get("family") or deluxe
        premier = rts.get("premier-king") or deluxe
        std = rts.get("std-twin") or biz

        scenarios = [
            # —— 9/1 已住完 ——
            dict(
                key="co_early_out",
                guest=g["赵明远"],
                check_in=_d(8, 30),
                check_out=_d(9, 1),
                status="checked_out",
                payment_status="paid",
                rt=deluxe,
                channel_id=ch.get("ctrip"),
                adr=520,
                extra_note="商务差旅已离店",
            ),
            dict(
                key="co_sept1_night",
                guest=g["陈思雨"],
                check_in=_d(9, 1),
                check_out=_d(9, 2),
                status="checked_out",
                payment_status="paid",
                rt=family,
                channel_id=ch.get("meituan"),
                adults=2,
                children=1,
                adr=720,
                arrival_time="15:30",
                extra_note="亲子一日游已退房",
            ),
            # —— 9/1 未到店 / 取消 ——
            dict(
                key="noshow_sept1",
                guest=g["郑立成"],
                check_in=_d(9, 1),
                check_out=_d(9, 2),
                status="no_show",
                payment_status="refunded",
                rt=std,
                channel_id=ch.get("ota"),
                adr=199,
                extra_note="未到店，已退款",
            ),
            dict(
                key="cancel_before_arrive",
                guest=g["林婉清"],
                check_in=_d(9, 1),
                check_out=_d(9, 3),
                status="cancelled",
                payment_status="refunded",
                rt=biz,
                channel_id=ch.get("douyin"),
                adr=380,
                extra_note="提前取消",
            ),
            # —— 在住（覆盖今天 9/2）——
            dict(
                key="inhouse_from_sept1",
                guest=g["周启航"],
                check_in=_d(9, 1),
                check_out=_d(9, 5),
                status="checked_in",
                payment_status="partial",
                rt=suite,
                channel_id=ch.get("agreement"),
                order_type=3,
                rooms=2,
                adults=2,
                adr=860,
                arrival_time="13:00",
                extra_note="协议客在住（2间）",
            ),
            dict(
                key="inhouse_arrive_today",
                guest=g["韩冬生"],
                check_in=_d(9, 2),
                check_out=_d(9, 4),
                status="checked_in",
                payment_status="paid",
                rt=premier,
                channel_id=ch.get("direct"),
                adr=560,
                arrival_time="14:20",
                extra_note="今日到店已入住",
            ),
            # —— 未来预订 9/3-9/10 ——
            dict(
                key="conf_weekend_family",
                guest=g["孙嘉怡"],
                check_in=_d(9, 5),
                check_out=_d(9, 7),
                status="confirmed",
                payment_status="paid",
                rt=family,
                channel_id=ch.get("wechat"),
                adults=2,
                children=2,
                adr=750,
                arrival_time="16:00",
                extra_note="周末亲子已确认已付",
            ),
            dict(
                key="conf_midweek_biz",
                guest=g["吴博文"],
                check_in=_d(9, 3),
                check_out=_d(9, 6),
                status="confirmed",
                payment_status="partial",
                rt=deluxe,
                channel_id=ch.get("fliggy"),
                adr=490,
                arrival_time="18:30",
                extra_note="工作日商务预订",
            ),
            dict(
                key="pending_late_week",
                guest=g["许晓彤"],
                check_in=_d(9, 8),
                check_out=_d(9, 10),
                status="pending",
                payment_status="unpaid",
                rt=biz,
                channel_id=ch.get("xiaohongshu"),
                adr=450,
                arrival_time="15:00",
                extra_note="待确认小红书客",
            ),
            dict(
                key="pending_sept10",
                guest=g["何雨萱"],
                check_in=_d(9, 10),
                check_out=_d(9, 12),
                status="pending",
                payment_status="unpaid",
                rt=premier,
                channel_id=ch.get("wecom"),
                adr=540,
                extra_note="国庆前夕待入住",
            ),
            dict(
                key="conf_multi_rooms",
                guest=g["周启航"],
                check_in=_d(9, 7),
                check_out=_d(9, 9),
                status="confirmed",
                payment_status="paid",
                rt=deluxe,
                channel_id=ch.get("agreement"),
                order_type=5,
                rooms=4,
                adults=8,
                adr=480,
                group_name="启航科技团建",
                extra_note="团队确认 4 间",
            ),
            dict(
                key="conf_long_span",
                guest=g["赵明远"],
                check_in=_d(9, 4),
                check_out=_d(9, 10),
                status="confirmed",
                payment_status="partial",
                rt=suite,
                channel_id=ch.get("ctrip"),
                adr=900,
                arrival_time="12:30",
                extra_note="跨周末长住预订",
            ),
            # —— 未来取消 / 可能影响 pickup 但不计入 ——
            dict(
                key="cancel_future",
                guest=g["林婉清"],
                check_in=_d(9, 6),
                check_out=_d(9, 8),
                status="cancelled",
                payment_status="refunded",
                rt=std,
                channel_id=ch.get("douyin"),
                adr=210,
                extra_note="未来单已取消（不计入 pickup）",
            ),
            dict(
                key="reserved_alias",
                guest=g["陈思雨"],
                check_in=_d(9, 9),
                check_out=_d(9, 11),
                status="reserved",
                payment_status="partial",
                rt=family,
                channel_id=ch.get("meituan"),
                adults=2,
                children=1,
                adr=700,
                extra_note="reserved 状态占房",
            ),
        ]

        created = 0
        for sc in scenarios:
            o = _add_order(db, hotel_id=hotel_id, **sc)
            if o:
                created += 1

        # 夜审：过去日实际营收（24 间规模，OCC≈70%）
        # 9/1 已过；若今天是 9/2，则 9/1 显示 actual
        audits = {
            _d(9, 1): (9800.0, 17, 1),  # 含 no_show 异常
            _d(8, 30): (8600.0, 15, 0),
            _d(8, 31): (9100.0, 16, 0),
            # 去年同期，供同比线
            _d(9, 1, 2025): (8200.0, 14, 0),
            _d(9, 2, 2025): (8700.0, 15, 0),
            _d(9, 3, 2025): (7900.0, 13, 0),
            _d(9, 4, 2025): (8100.0, 14, 0),
            _d(9, 5, 2025): (10200.0, 18, 0),
            _d(9, 6, 2025): (11500.0, 20, 0),
            _d(9, 7, 2025): (9800.0, 17, 0),
            _d(9, 8, 2025): (7600.0, 12, 0),
            _d(9, 9, 2025): (7400.0, 12, 0),
            _d(9, 10, 2025): (8800.0, 15, 0),
        }
        # 补近几周工作日夜审，稳住星期基线（若已有则覆盖为更合理规模）
        for offset, rev, rn in [
            (7, 8400.0, 14),
            (8, 9200.0, 16),
            (9, 7800.0, 13),
            (10, 10500.0, 18),
            (11, 11200.0, 19),
            (12, 6900.0, 11),
            (13, 7200.0, 12),
            (14, 8800.0, 15),
        ]:
            audits[_d(9, 1) - timedelta(days=offset)] = (rev, rn, 0)

        for biz_date, (rev, rn, exc) in audits.items():
            _upsert_audit(db, hotel_id, biz_date, rev, rn, exc)

        db.commit()
        return {
            "hotel_id": hotel_id,
            "guests": len(guests),
            "orders_created": created,
            "audits_upserted": len(audits),
            "guest_names": [x[0] for x in GUESTS],
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = seed()
    print("OK", result)
