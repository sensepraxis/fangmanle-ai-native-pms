# SPDX-License-Identifier: Apache-2.0
"""合作企业协议（协议客）：企业账户 + 房型价格阶梯（量价置换、挂账、价格刚性）。"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from models import Base, Channel, CorpAccount, CorpPriceLadder, Guest, Hotel, Order, RoomType


def ensure_corp_agreement_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    if "corp_accounts" not in tables:
        need.append(CorpAccount.__table__)
    if "corp_price_ladders" not in tables:
        need.append(CorpPriceLadder.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)


CORP_SEED = [
    {
        "code": "BYTEDANCE",
        "name": "字节跳动差旅",
        "industry": "互联网",
        "contact_name": "陈经理",
        "contact_phone": "138****1100",
        "annual_commit_nights": 800,
        "tiers": [
            ("标准协议档", 0, 299, 0.88),
            ("量价优惠档", 300, 799, 0.82),
            ("战略量价档", 800, None, 0.78),
        ],
    },
    {
        "code": "HUAWEI",
        "name": "华为技术有限公司",
        "industry": "制造/通讯",
        "contact_name": "刘主管",
        "contact_phone": "139****2200",
        "annual_commit_nights": 1200,
        "tiers": [
            ("标准协议档", 0, 499, 0.90),
            ("量价优惠档", 500, 1199, 0.84),
            ("战略量价档", 1200, None, 0.80),
        ],
    },
    {
        "code": "ICBC",
        "name": "工商银行分行差旅",
        "industry": "金融",
        "contact_name": "王主任",
        "contact_phone": "137****3300",
        "annual_commit_nights": 400,
        "tiers": [
            ("标准协议档", 0, 199, 0.92),
            ("量价优惠档", 200, 399, 0.86),
            ("战略量价档", 400, None, 0.83),
        ],
    },
]


def ensure_corp_agreements(db: Session):
    """幂等灌入合作企业与价格阶梯；协议订单挂企业备注（可长可短）。"""
    hotels = db.query(Hotel).all()
    if not hotels:
        return {"corps": 0}

    agr_ch = db.query(Channel).filter_by(code="agreement").first()
    today = date.today()
    created = 0

    for h in hotels:
        rts = db.query(RoomType).filter_by(hotel_id=h.id).order_by(RoomType.base_price.asc()).all()
        if not rts:
            continue
        pick = rts[:3] if len(rts) >= 3 else rts

        for cs in CORP_SEED:
            row = db.query(CorpAccount).filter_by(hotel_id=h.id, code=cs["code"]).first()
            if not row:
                row = CorpAccount(
                    hotel_id=h.id,
                    code=cs["code"],
                    name=cs["name"],
                    industry=cs["industry"],
                    contact_name=cs["contact_name"],
                    contact_phone=cs["contact_phone"],
                    settlement_mode="挂账",
                    price_policy="rigid",
                    annual_commit_nights=cs["annual_commit_nights"],
                    used_nights_ytd=int(cs["annual_commit_nights"] * 0.42),
                    credit_limit=200000,
                    credit_used=0,
                    settle_cycle="monthly",
                    valid_from=date(today.year, 1, 1),
                    valid_to=date(today.year, 12, 31),
                    status="active",
                    note="框架协议一年一签；淡旺季不调价，按量价阶梯执行。",
                )
                db.add(row)
                db.flush()
                created += 1
            else:
                row.settlement_mode = "挂账"
                row.price_policy = "rigid"
                row.name = cs["name"]
                row.industry = cs["industry"]
                row.contact_name = cs["contact_name"]
                row.contact_phone = cs["contact_phone"]
                row.annual_commit_nights = cs["annual_commit_nights"]
                if row.used_nights_ytd is None:
                    row.used_nights_ytd = int(cs["annual_commit_nights"] * 0.42)
                if not getattr(row, "credit_limit", None):
                    row.credit_limit = 200000
                if not getattr(row, "settle_cycle", None):
                    row.settle_cycle = "monthly"
                row.note = "框架协议一年一签；淡旺季不调价，按量价阶梯执行。"

            for rt in pick:
                for ti, (tname, mn, mx, mult) in enumerate(cs["tiers"]):
                    exists = (
                        db.query(CorpPriceLadder).filter_by(corp_id=row.id, room_type_id=rt.id, tier_name=tname).first()
                    )
                    price = round(float(rt.base_price or 400) * mult, 0)
                    if not exists:
                        db.add(
                            CorpPriceLadder(
                                corp_id=row.id,
                                room_type_id=rt.id,
                                tier_name=tname,
                                min_annual_nights=mn,
                                max_annual_nights=mx,
                                contract_price=Decimal(str(price)),
                                sort_order=ti,
                                seasonal_float=False,
                            )
                        )
                    else:
                        exists.contract_price = Decimal(str(price))
                        exists.seasonal_float = False
                        exists.min_annual_nights = mn
                        exists.max_annual_nights = mx
                        exists.sort_order = ti

        # 协议渠道订单：挂企业 + 挂账；补一条长住协议样例（证明可长可短）
        if agr_ch:
            corps = db.query(CorpAccount).filter_by(hotel_id=h.id, status="active").order_by(CorpAccount.id.asc()).all()
            orders = db.query(Order).filter_by(hotel_id=h.id, channel_id=agr_ch.id).order_by(Order.id.asc()).all()
            for i, o in enumerate(orders):
                corp = corps[i % len(corps)] if corps else None
                if corp:
                    o.agreement_id = corp.id
                    o.order_type = 3
                    o.note = f"协议客 · {corp.name} · 挂账结算 · 刚性协议价"
                    # 仅已退房且确有挂账明细的订单才标 on_account；其余保持 unpaid
                    if o.status == "checked_out":
                        o.payment_status = "on_account"
                    elif o.payment_status == "on_account":
                        o.payment_status = "unpaid"

            _ensure_long_short_samples(db, h, agr_ch, corps, rts, today)

    db.commit()
    return {"corps": created}


def _ensure_long_short_samples(db: Session, hotel, agr_ch, corps, rts, today: date):
    """保证协议客样例既有短住也有长住。"""
    if not corps or not rts:
        return
    guests = db.query(Guest).limit(20).all()
    if not guests:
        return

    specs = [
        (1, "短住"),  # 1 晚
        (14, "长住"),  # 14 晚仍属协议客（关系驱动，非时长驱动）
    ]
    existing = db.query(Order).filter_by(hotel_id=hotel.id, channel_id=agr_ch.id).all()
    night_set = {int(o.nights or 0) for o in existing}

    for nights, label in specs:
        if nights in night_set:
            continue
        corp = corps[0 if nights == 1 else min(1, len(corps) - 1)]
        g = guests[nights % len(guests)]
        rt = rts[nights % len(rts)]
        ci = today + timedelta(days=1 if nights == 1 else 3)
        co = ci + timedelta(days=nights)
        # 取当前企业适用阶梯价（按 YTD 间夜）
        used = int(corp.used_nights_ytd or 0)
        ladders = (
            db.query(CorpPriceLadder)
            .filter_by(corp_id=corp.id, room_type_id=rt.id)
            .order_by(CorpPriceLadder.sort_order.asc())
            .all()
        )
        rate = float(rt.base_price or 300) * 0.85
        for lad in ladders:
            mn = int(lad.min_annual_nights or 0)
            mx = lad.max_annual_nights
            if used >= mn and (mx is None or used <= int(mx)):
                rate = float(lad.contract_price)
                break
        total = round(rate * nights, 2)
        order_no = f"AG-{hotel.id}-{label}-{nights}N"
        if db.query(Order).filter_by(order_no=order_no).first():
            continue
        o = Order(
            hotel_id=hotel.id,
            order_no=order_no,
            guest_id=g.id,
            channel_id=agr_ch.id,
            room_type_id=rt.id,
            order_type=3,
            agreement_id=corp.id,
            check_in=ci,
            check_out=co,
            nights=nights,
            rooms=1,
            adults=1,
            children=0,
            total_amount=Decimal(str(total)),
            status="pending",
            payment_status="unpaid",
            note=f"协议客 · {corp.name} · {label}{nights}晚 · 挂账 · 刚性协议价",
        )
        db.add(o)
