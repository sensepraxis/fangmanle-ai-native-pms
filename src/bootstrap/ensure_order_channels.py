# SPDX-License-Identifier: Apache-2.0
"""订单渠道扩容：地图 / GEO / 团购；常住客与协议客拆分；按来源补样例单。

渠道元数据与 `source_group_for` 已抽到 `orders.channel_config`；本文件保留启动期
幂等的 schema 保活 + 样例单灌入。
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from models import Channel, Guest, Order, OrderItem, RoomType
from orders.channel_config import channel_display_name, extra_channels, source_group_for


def ensure_order_channels(db: Session):
    """幂等：补渠道 + 拆分常住/协议 + 样例单。"""
    existing = {c.code: c for c in db.query(Channel).all()}
    created = []
    for code, zh_name, ctype, comm in extra_channels():
        name = channel_display_name(code, zh_name, for_seed=True)
        if code in existing:
            ch = existing[code]
            ch.name = name
            ch.type = ctype
            ch.commission_rate = Decimal(str(comm))
            ch.is_active = True
        else:
            ch = Channel(code=code, name=name, type=ctype, commission_rate=comm, is_active=True)
            db.add(ch)
            db.flush()
            existing[code] = ch
            created.append(code)

    # 旧渠道类型对齐
    if "douyin" in existing:
        existing["douyin"].type = "voucher"
        existing["douyin"].name = channel_display_name("douyin", "抖音团购", for_seed=True)
    if "ota" in existing:
        existing["ota"].type = "booking"
        existing["ota"].name = channel_display_name("ota", "其他预订渠道", for_seed=True)
        ota_subs = [existing[c] for c in ("ctrip", "meituan", "fliggy") if c in existing]
        if ota_subs:
            legacy = db.query(Order).filter_by(channel_id=existing["ota"].id).all()
            for i, ord_row in enumerate(legacy):
                ord_row.channel_id = ota_subs[i % len(ota_subs)].id

    # 收款 method=ota 改为订单真实渠道 code（携程/美团/飞猪等）
    from models import Payment

    ch_by_id = {row.id: row for row in existing.values()}
    for p in db.query(Payment).filter(Payment.method == "ota").all():
        code = "ctrip"
        if p.order_id:
            o = db.get(Order, p.order_id)
            if o and o.channel_id and o.channel_id in ch_by_id:
                c = ch_by_id[o.channel_id]
                if c.code and c.code != "ota":
                    code = c.code
        p.method = code

    if "wechat" in existing:
        existing["wechat"].type = "wechat"
        existing["wechat"].name = channel_display_name("wechat", "企微私域", for_seed=True)
    if "direct" in existing:
        existing["direct"].type = "direct"
        existing["direct"].name = channel_display_name("direct", "散客直订", for_seed=True)
    if "agreement" in existing:
        existing["agreement"].type = "agreement"
        existing["agreement"].name = channel_display_name("agreement", "协议客户", for_seed=True)
    if "longstay" in existing:
        existing["longstay"].type = "longstay"
        existing["longstay"].name = channel_display_name("longstay", "常住客", for_seed=True)
    if "xiaohongshu" in existing:
        existing["xiaohongshu"].name = channel_display_name("xiaohongshu", "小红书", for_seed=True)

    db.flush()
    _retag_legacy_notes(db, existing)
    _ensure_sample_orders(db, existing)
    db.commit()
    return {"channels_added": created, "channels": len(existing)}


def _retag_legacy_notes(db: Session, ch_by_code: dict):
    """仅校正备注语义；不再把长住协议单迁到常住渠道。"""
    agr = ch_by_code.get("agreement")
    ls = ch_by_code.get("longstay")
    if agr:
        for o in db.query(Order).filter_by(channel_id=agr.id).all():
            note = (o.note or "").strip()
            if not note or "常住/协议" in note or note in ("协议价订单", "协议价订单 · 企业约定折扣"):
                o.note = "协议客 · 企业协议价 · 挂账"
            if o.payment_status == "paid" and o.status == "checked_out":
                o.payment_status = "on_account"
    if ls:
        for o in db.query(Order).filter_by(channel_id=ls.id).all():
            note = (o.note or "").strip()
            if (not note) or ("协议" in note and "常住" not in note):
                n = int(o.nights or 0)
                o.note = f"常住客 · 连住{n or '多'}晚 · 时长折扣"


def _ensure_sample_orders(db: Session, ch_by_code: dict):
    from models import Hotel

    today = date.today()
    hotels = db.query(Hotel).all()
    # 常住 / 协议分开补样例
    codes_need = [row[0] for row in extra_channels()]
    if "direct" not in codes_need:
        codes_need.append("direct")

    for h in hotels:
        rts = db.query(RoomType).filter_by(hotel_id=h.id).all()
        if not rts:
            continue
        guests = db.query(Guest).limit(40).all()
        if not guests:
            continue

        for i, code in enumerate(codes_need):
            ch = ch_by_code.get(code)
            if not ch:
                continue
            n = db.query(Order).filter_by(hotel_id=h.id, channel_id=ch.id).count()
            need = max(0, 2 - n)
            for j in range(need):
                g = guests[(h.id * 17 + i * 3 + j) % len(guests)]
                rt = rts[(i + j) % len(rts)]
                ci = today + timedelta(days=(i + j) % 5)
                if code == "longstay":
                    nights = 30 if j == 0 else 14  # 长住，绝非 1–2 天
                elif code == "agreement":
                    nights = 1 if j == 0 else 4  # 协议客可短住；长住样例由企业迁移补齐
                else:
                    nights = 2
                co = ci + timedelta(days=nights)
                rate = float(rt.base_price or 300)
                if code == "longstay":
                    rate = round(rate * 0.68, 2)  # 长住阶梯折扣
                elif code == "agreement":
                    rate = round(rate * 0.85, 2)  # 刚性协议价
                elif code in ("map_baidu", "map_amap", "geo_doubao"):
                    rate = round(rate * 0.95, 2)
                elif code in ("douyin", "meituan_voucher"):
                    rate = round(rate * 0.85, 2)
                total = round(rate * nights, 2)
                status = "checked_in" if (code == "longstay" and j == 0) else "pending"
                pay = (
                    "on_account"
                    if code == "agreement"
                    else (
                        "paid"
                        if code
                        in (
                            "ctrip",
                            "meituan",
                            "fliggy",
                            "douyin",
                            "meituan_voucher",
                            "map_baidu",
                            "map_amap",
                            "geo_doubao",
                            "booking",
                            "agoda",
                            "expedia",
                        )
                        else "unpaid"
                    )
                )
                prefix = {
                    "ctrip": "XC",
                    "booking": "BK",
                    "agoda": "AGD",
                    "expedia": "EXP",
                    "meituan": "MTJD",
                    "fliggy": "FZ",
                    "douyin": "DY",
                    "meituan_voucher": "MT",
                    "direct": "WK",
                    "map_baidu": "BD",
                    "map_amap": "GD",
                    "geo_doubao": "GEO",
                    "wechat": "WX",
                    "wecom": "WECOM",
                    "longstay": "LS",
                    "agreement": "AG",
                }.get(code, "ORD")
                order_no = f"{prefix}-{h.id}-{ci.strftime('%m%d')}-{100 + i * 10 + j}"
                if db.query(Order).filter_by(order_no=order_no).first():
                    continue
                note_map = {
                    "ctrip": "携程预付单",
                    "booking": "Booking.com prepaid",
                    "agoda": "Agoda prepaid",
                    "expedia": "Expedia prepaid",
                    "meituan": "美团酒店预付单",
                    "fliggy": "飞猪预付单",
                    "douyin": "抖音团购核销成单",
                    "meituan_voucher": "美团团购核销成单",
                    "direct": "散客前台直订/即时入住",
                    "map_baidu": "百度地图 POI 预订",
                    "map_amap": "高德地图 POI 预订",
                    "geo_doubao": "GEO 推荐·豆包落地预订",
                    "wechat": "企微私域 · 顾问跟进成单",
                    "wecom": "企业微信 · 私域下单",
                    "longstay": f"常住客 · 连住{nights}晚 · 时长折扣",
                    "agreement": f"协议客 · 挂账 · 刚性协议价 · {nights}晚",
                }
                o = Order(
                    hotel_id=h.id,
                    order_no=order_no,
                    guest_id=g.id,
                    channel_id=ch.id,
                    room_type_id=rt.id,
                    check_in=ci,
                    check_out=co,
                    nights=nights,
                    rooms=1,
                    adults=1,
                    children=0,
                    total_amount=total,
                    status=status,
                    payment_status=pay,
                    note=note_map.get(code, ""),
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
