# SPDX-License-Identifier: Apache-2.0
"""seed 子包 — 保留外部 `from seed import seed` 兼容。

原 src/seed.py（1408 行）按业务子域拆为：
  - _common        : 通用 helper（name/phone/daterange_days 等）
  - users          : 角色 / 用户 / 标签
  - finance        : 财务流
  - housekeeping   : 房务 / 客需 / 排班
  - risk           : 营收异常 / 风险预警
  - supplies       : 物资 / 布草
  - assets         : 资产 / IoT
  - seed()         : 主调度函数（保留在 __init__.py）

外部 `from seed import seed` / `from seed import xxx` 走这里。
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import random
from datetime import date, datetime, timedelta

from bootstrap.ensure_assets import ensure_asset_schema
from bootstrap.ensure_supplies import ensure_supplies_schema
from bootstrap.migrations.alter_to_single_hotel import ensure_local_users, ensure_single_hotel_schema
from database import SessionLocal, engine
from infra.auth_local import hash_password
from models import (
    AiCommand,
    Asset,
    AssetAlert,
    AssetAuditItem,
    AssetEvent,
    AssetInsight,
    AssetMaintenance,
    Base,
    Campaign,
    Channel,
    ChannelAttribution,
    ChannelContract,
    DamageTicket,
    DemandForecast,
    FinanceReport,
    Guest,
    GuestIdentity,
    GuestTag,
    Hotel,
    HousekeepingTask,
    InventoryAllocation,
    Invoice,
    LedgerEntry,
    Linen,
    LinenSnapshot,
    NightAuditException,
    NightAuditLog,
    Order,
    OrderItem,
    Payment,
    PriceSuggestion,
    ProfitInsight,
    RateStrategy,
    ReconBatch,
    ReconItem,
    Reservation,
    RestockItem,
    RestockOrder,
    RevenueAnomaly,
    Review,
    RiskAlert,
    Role,
    Room,
    RoomInspection,
    RoomIotMetric,
    RoomStatusLog,
    RoomType,
    Segment,
    SegmentMember,
    ServiceRequest,
    StaffShift,
    StaffShiftRequest,
    StockMovement,
    Supply,
    SupplyAlert,
    SupplyCategory,
    SupplyInsight,
    SupplyRequisition,
    TagDefinition,
    TaxFiling,
    User,
    Venue,
    VenueBooking,
)

random.seed(20260812)
TODAY = date.today()

# ---- 模块级常量：按 SEED_LOCALE 选择中文 / 英文 pack ----
from seed.locale_pack import get_pack, get_seed_locale, seed_text  # noqa: E402

_pack = get_pack()
SURNAMES = _pack.SURNAMES
GIVEN = _pack.GIVEN
HOTELS = _pack.HOTELS
LOCAL_USERS = _pack.LOCAL_USERS
ROOM_TYPE_TPL = _pack.ROOM_TYPE_TPL
CHANNELS = _pack.CHANNELS
try:
    from infra.packs import ensure_packs, pack_channel_seeds

    ensure_packs()
    _pack_chs = pack_channel_seeds()
    if _pack_chs:
        CHANNELS = list(_pack_chs)
except Exception:
    pass
TAGS = _pack.TAGS
SUPPLY_CATS = _pack.SUPPLY_CATS
SUPPLIES = _pack.SUPPLIES
ASSET_TPL = _pack.ASSET_TPL
ASSET_FLOW_TPL = _pack.ASSET_FLOW_TPL
print(
    f"[seed] locale={get_seed_locale()} pack={_pack.__name__} FML_PACKS={__import__('os').environ.get('FML_PACKS', 'cn')}"
)

from seed import _common as _seed_common  # noqa: F401
from seed import assets as _seed_assets  # noqa: F401
from seed import finance as _seed_finance  # noqa: F401
from seed import housekeeping as _seed_housekeeping  # noqa: F401
from seed import risk as _seed_risk  # noqa: F401
from seed import supplies as _seed_supplies  # noqa: F401
from seed import users as _seed_users  # noqa: F401

# ---- 公共 API re-export ----
from seed._common import _due_this_month, daterange_days, math_sin_day, name, phone
from seed.assets import seed_assets_flow, seed_iot_metrics
from seed.finance import seed_finance_flow
from seed.housekeeping import enrich_housekeeping_demo, enrich_room_inspections
from seed.risk import enrich_revenue_anomalies, enrich_risk_alerts
from seed.supplies import enrich_supplies_rca_demo, seed_supplies_flow
from seed.users import ensure_tag_rules, seed_local_users

# ---- 主 seed() 函数（原状保留，待下轮拆 god function）----


# ---- 主种子数据生成（god function 隔离层）----


def _seed_demo_data(db, reset=False):
    """灌所有 demo 数据（roles + users + hotels + channels + rooms + 客户 + 订单 + 价格 + ...）。

    重构说明：原 seed() 主函数是 380+ 行 god function（含 12 个 inline 段，
    段与段之间局部变量互相依赖：roles → users → channels → rooms → 客户 → 订单 → 价格 → ...
    此版将整个 inline 段集中到 _seed_demo_data 作为可识别的边界，seed() 主函数变薄。
    后续可逐段重构（每次只动一段，跑测试再继续）。
    """
    db = SessionLocal()
    try:
        if reset:
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
            db.commit()
        if db.query(Hotel).first():
            print("Data already present; skipping core seed (use --reset to rebuild).")
            hotels = db.query(Hotel).all()
            Base.metadata.create_all(engine)
            ensure_single_hotel_schema(engine)
            ensure_asset_schema(engine)
            ensure_supplies_schema(engine)
            ensure_local_users(db)
            seed_finance_flow(db, hotels)
            seed_supplies_flow(db, hotels)
            enrich_supplies_rca_demo(db, hotels)
            seed_assets_flow(db, hotels)
            enrich_housekeeping_demo(db, hotels)
            ensure_tag_rules(db)
            return
        roles = {}
        for code, rname, desc in _pack.ROLES:
            r = Role(code=code, name=rname, description=desc, is_system=True)
            db.add(r)
            db.flush()
            roles[code] = r
        hotels = []
        for h_idx, (code, hname, city, addr, star) in enumerate(HOTELS):
            h = Hotel(code=code, name=hname, city=city, address=addr, star_rating=star, currency="CNY")
            db.add(h)
            db.flush()
            hotels.append(h)
        seed_local_users(db, hotels, roles)
        users = {}
        for username, _pw, role_code, _fn in LOCAL_USERS:
            users[role_code] = db.query(User).filter_by(username=username).first()
        users["fd1"] = users.get("fd")
        users["hk1"] = users.get("fd")
        users["mgr1"] = users.get("gm")
        users["mgr"] = users.get("gm")
        users["hk"] = users.get("fd")
        users["fin"] = users.get("gm")
        channels = []
        for code, cname, ctype, comm in CHANNELS:
            c = Channel(code=code, name=cname, type=ctype, commission_rate=comm)
            db.add(c)
            db.flush()
            channels.append(c)
        ch_by_code = {c.code: c for c in channels}
        room_types = []
        rooms_by_hotel = {}
        for h in hotels:
            for code, tname, bed, cap, base, bf in ROOM_TYPE_TPL:
                is_suite = code == "exec-suite" or "套" in tname or "Suite" in tname
                area = int(28 + cap * 6 + (10 if is_suite else 0))
                tags = []
                if bf:
                    tags.append(_pack.AMENITY_BF)
                if cap >= 3:
                    tags.append(_pack.AMENITY_EXTRA_BED)
                if is_suite:
                    tags.append(_pack.AMENITY_LIVING)
                    tags.append(_pack.AMENITY_TUB)
                else:
                    tags.append(_pack.AMENITY_SHOWER)
                rt = RoomType(
                    hotel_id=h.id,
                    code=code,
                    name=tname,
                    bed_type=bed,
                    capacity=cap,
                    base_price=base,
                    breakfast_included=bf,
                    area=area,
                    amenities=json.dumps(tags, ensure_ascii=False),
                )
                db.add(rt)
                db.flush()
                room_types.append(rt)
            hrooms = []
            rt_cycle = room_types_for = [rt for rt in room_types if rt.hotel_id == h.id]
            idx = 0
            for floor in range(1, 3):
                for n in range(1, 13):
                    rt = rt_cycle[idx % len(rt_cycle)]
                    idx += 1
                    r = Room(
                        hotel_id=h.id,
                        room_type_id=rt.id,
                        room_no=f"{floor:02d}{n:02d}",
                        building="A",
                        floor=floor,
                        status="vacant",
                    )
                    db.add(r)
                    db.flush()
                    hrooms.append(r)
            rooms_by_hotel[h.id] = hrooms
            db.add(
                RateStrategy(
                    hotel_id=h.id,
                    name=_pack.RATE_STRATEGY_NAME,
                    min_floor_price=base * 0.7,
                    max_ceiling_price=base * 1.8,
                    auto_cruise=True,
                    effective_from=TODAY - timedelta(days=30),
                    effective_to=TODAY + timedelta(days=180),
                )
            )
        tag_defs = []
        for code, tname, cat, rule in TAGS:
            t = TagDefinition(code=code, name=tname, category=cat, rule_expr=rule)
            db.add(t)
            db.flush()
            tag_defs.append(t)
        tag_by_code = {t.code: t for t in tag_defs}
        from bootstrap.ensure_oneid_audit import create_realistic_identities

        guests = []
        for i in range(220):
            g = Guest(
                one_id=f"ONE{100000 + i}",
                name=name(),
                phone=phone(),
                gender=random.choice(["M", "F", "U"]),
                birthday=date(random.randint(1970, 2005), random.randint(1, 12), random.randint(1, 28)),
                vip_level=random.choice(["normal", "normal", "silver", "gold", "platinum"]),
                city=random.choice(list(_pack.CITIES)),
                ltv=round(random.uniform(0, 12000), 2),
                churn_risk=round(random.uniform(0, 1), 2),
            )
            db.add(g)
            db.flush()
            guests.append(g)
            pool = list(ch_by_code.keys()) or ["direct"]
            k = min(len(pool), random.randint(1, 3))
            sources = random.sample(pool, k)
            create_realistic_identities(db, g, sources)
            for t in random.sample(tag_defs, random.randint(1, 3)):
                db.add(
                    GuestTag(guest_id=g.id, tag_id=t.id, confidence=round(random.uniform(0.6, 1.0), 2), source="model")
                )
        orders = []
        order_no_seq = 1
        channel_codes = list(ch_by_code.keys()) or ["direct"]
        _cw_pref = {
            "direct": 4,
            "agreement": 1,
            "longstay": 1,
            "booking": 3,
            "agoda": 3,
            "expedia": 2,
            "traveloka": 2,
            "ctrip": 3,
            "meituan": 3,
            "fliggy": 2,
            "douyin": 2,
            "xiaohongshu": 2,
            "wechat": 2,
        }
        cw = {c: _cw_pref.get(c, 2) for c in channel_codes}
        private_like = {c for c in ("wechat", "direct") if c in ch_by_code}
        ota_like = {
            c.code
            for c in channels
            if (c.type or "") in ("booking", "voucher", "xiaohongshu")
            or c.code
            in (
                "douyin",
                "xiaohongshu",
                "ctrip",
                "meituan",
                "fliggy",
                "booking",
                "agoda",
                "expedia",
                "traveloka",
            )
        }
        assist_pool = [c for c in channel_codes if c not in private_like]
        occupied_rooms = set()
        for h in hotels:
            h_rt = [rt for rt in room_types if rt.hotel_id == h.id]
            for _ in range(160):
                ci = TODAY + timedelta(days=random.randint(-30, 30))
                nights = random.randint(1, 4)
                co = ci + timedelta(days=nights)
                rt = random.choice(h_rt)
                ch = random.choices(channel_codes, weights=[cw[c] for c in channel_codes])[0]
                rooms_n = random.randint(1, 2)
                if co < TODAY:
                    status = "checked_out"
                    pay = "paid"
                elif ci <= TODAY < co:
                    status = "checked_in"
                    pay = "paid"
                elif random.random() < 0.08:
                    status = random.choice(["cancelled", "no_show"])
                    pay = "unpaid"
                else:
                    status = "pending"
                    pay = random.choice(["unpaid", "partial", "paid"])
                rate = rt.base_price * (1 - ch_by_code[ch].commission_rate * 0.5)
                total = round(rate * nights * rooms_n, 2)
                g = random.choice(guests)
                order_no = f"ORD-{ci.strftime('%Y%m%d')}-{order_no_seq:03d}"
                order_no_seq += 1
                o = Order(
                    hotel_id=h.id,
                    order_no=order_no,
                    guest_id=g.id,
                    channel_id=ch_by_code[ch].id,
                    room_type_id=rt.id,
                    check_in=ci,
                    check_out=co,
                    nights=nights,
                    rooms=rooms_n,
                    adults=random.randint(1, 2),
                    children=random.randint(0, 1),
                    total_amount=total,
                    status=status,
                    payment_status=pay,
                )
                db.add(o)
                db.flush()
                orders.append(o)
                db.add(
                    OrderItem(
                        order_id=o.id,
                        item_type="room",
                        description=f"{rt.name} ×{nights}晚×{rooms_n}间",
                        qty=nights * rooms_n,
                        unit_price=round(rate, 2),
                        amount=total,
                    )
                )
                if status in ("checked_in", "checked_out"):
                    free = [
                        r
                        for r in rooms_by_hotel[h.id]
                        if r.room_type_id == rt.id and r.id not in occupied_rooms and (r.status == "vacant")
                    ]
                    if free:
                        rm = random.choice(free)
                        if status == "checked_in":
                            rm.status = "occupied"
                            occupied_rooms.add(rm.id)
                            db.add(
                                RoomStatusLog(room_id=rm.id, from_status="vacant", to_status="occupied", reason="入住")
                            )
                        else:
                            rm.status = "dirty"
                            db.add(
                                RoomStatusLog(room_id=rm.id, from_status="occupied", to_status="dirty", reason="退房")
                            )
                        db.add(Reservation(order_id=o.id, room_id=rm.id))
                if pay == "paid":
                    pay_method = ch if ch in ch_by_code else "direct"
                    db.add(
                        Payment(
                            hotel_id=h.id,
                            order_id=o.id,
                            method=pay_method,
                            amount=total,
                            operator_id=users[f"fd{hotels.index(h) + 1}"].id,
                        )
                    )
                    db.add(
                        Invoice(
                            hotel_id=h.id,
                            order_id=o.id,
                            invoice_no=f"INV-{o.id:06d}",
                            amount=total,
                            tax=round(total * 0.06, 2),
                            status="issued",
                            issued_at=datetime.now(),
                        )
                    )
                    db.add(
                        LedgerEntry(
                            hotel_id=h.id,
                            biz_date=ci,
                            account="主营业务收入-房费",
                            credit=total,
                            ref_type="order",
                            ref_id=o.id,
                        )
                    )
                    db.add(
                        LedgerEntry(
                            hotel_id=h.id, biz_date=ci, account="应收账款", debit=total, ref_type="order", ref_id=o.id
                        )
                    )
                if ch in private_like and assist_pool and random.random() < 0.7:
                    assist = random.choice(assist_pool)
                    db.add(ChannelAttribution(hotel_id=h.id, order_id=o.id, source=assist, attributed_rev=total))
                elif ch in ota_like:
                    db.add(ChannelAttribution(hotel_id=h.id, order_id=o.id, source=ch, attributed_rev=total))
        for h in hotels:
            h_rt = [rt for rt in room_types if rt.hotel_id == h.id]
            strat = db.query(RateStrategy).filter_by(hotel_id=h.id).first()
            floor = strat.min_floor_price
            for d in daterange_days(7):
                for rt in h_rt:
                    cur = rt.base_price
                    sug = round(cur * random.uniform(0.85, 1.25), 0)
                    conf = random.choice(["high", "high", "medium", "low"])
                    if sug < floor:
                        st, gm = ("blocked", f"低于最低价地板 ¥{floor:.0f}")
                    elif random.random() < 0.35:
                        st, gm = ("accepted", None)
                    else:
                        st, gm = ("pending", None)
                    db.add(
                        PriceSuggestion(
                            hotel_id=h.id,
                            room_type_id=rt.id,
                            biz_date=d,
                            current_price=cur,
                            suggested_price=sug,
                            confidence=conf,
                            status=st,
                            guardrail_msg=gm,
                            model_version="fml-rm-1.2",
                        )
                    )
        for h in hotels:
            h_rt = [rt for rt in room_types if rt.hotel_id == h.id]
            for d in daterange_days(14):
                for rt in h_rt:
                    for c in channels:
                        if random.random() < 0.5:
                            continue
                        db.add(
                            InventoryAllocation(
                                hotel_id=h.id,
                                room_type_id=rt.id,
                                channel_id=c.id,
                                biz_date=d,
                                allotment=random.randint(3, 20),
                                sold=random.randint(0, 12),
                            )
                        )
                    db.add(
                        DemandForecast(
                            hotel_id=h.id,
                            room_type_id=rt.id,
                            biz_date=d,
                            predicted_occ=round(random.uniform(0.4, 0.95), 2),
                            predicted_adr=round(rt.base_price * random.uniform(0.8, 1.2), 2),
                            model_version="fml-fc-1.0",
                        )
                    )
        for h in hotels:
            dirty = [r for r in rooms_by_hotel[h.id] if r.status in ("dirty", "occupied")]
            hk_users = [users[f"hk{hotels.index(h) + 1}"], users[f"fd{hotels.index(h) + 1}"]]
            for i, r in enumerate(dirty[:8]):
                db.add(
                    HousekeepingTask(
                        hotel_id=h.id,
                        room_id=r.id,
                        task_type="clean" if r.status == "dirty" else "inspect",
                        assignee_id=hk_users[i % len(hk_users)].id,
                        priority=random.randint(1, 5),
                        status=random.choice(["open", "assigned", "in_progress"]),
                        due_at=datetime.now() + timedelta(hours=2),
                    )
                )
            for r in dirty[8:10]:
                db.add(
                    HousekeepingTask(
                        hotel_id=h.id,
                        room_id=r.id,
                        task_type="clean",
                        assignee_id=hk_users[0].id,
                        priority=3,
                        status="done",
                        created_at=datetime.now() - timedelta(hours=2),
                        done_at=datetime.now() - timedelta(minutes=40),
                        due_at=datetime.now(),
                    )
                )
            for ui, sh in enumerate(["morning", "afternoon", "night"]):
                db.add(
                    StaffShift(
                        hotel_id=h.id,
                        user_id=hk_users[ui % len(hk_users)].id,
                        shift_date=TODAY,
                        shift=sh,
                        handover_note=None,
                    )
                )
        for h in hotels:
            cats = {}
            for cname, parent in SUPPLY_CATS:
                sc = SupplyCategory(hotel_id=h.id, name=cname)
                db.add(sc)
                db.flush()
                cats[cname] = sc
            for sidx, (cat, sname, unit, ss, cs) in enumerate(SUPPLIES):
                cur = random.randint(int(cs * 0.3), int(cs * 1.5))
                sp = Supply(
                    hotel_id=h.id,
                    category_id=cats[cat].id,
                    sku=f"SKU-{hotels.index(h) + 1}{sidx:02d}",
                    name=sname,
                    unit=unit,
                    safety_stock=ss,
                    current_stock=cur,
                    unit_cost=round(random.uniform(1, 30), 2),
                )
                db.add(sp)
                db.flush()
                db.add(
                    StockMovement(
                        hotel_id=h.id,
                        supply_id=sp.id,
                        movement_type="issue" if cur < cs else "restock",
                        qty=random.randint(5, 40),
                        operator_id=users[f"hk{hotels.index(h) + 1}"].id,
                        note="日常",
                    )
                )
            for r in rooms_by_hotel[h.id][:30]:
                for it in ["床单", "枕套", "浴巾", "面巾"]:
                    db.add(
                        Linen(
                            hotel_id=h.id,
                            room_id=r.id,
                            item_type=it,
                            status=random.choice(["in_use", "in_wash", "available"]),
                            wash_count=random.randint(1, 40),
                            lifecycle_stage=random.choice(["良好", "磨损", "待换"]),
                        )
                    )
            for sidx, a in enumerate(ASSET_TPL):
                purch = date(random.randint(2019, 2024), random.randint(1, 12), 1)
                pv = round(random.uniform(3000, 80000), 2)
                asset_no = f"EQ-{hotels.index(h) + 1:02d}{sidx + 1:04d}"
                db.add(
                    Asset(
                        hotel_id=h.id,
                        name=a,
                        category="设备",
                        location=f"{random.randint(1, 12)}F",
                        asset_no=asset_no,
                        purchase_date=purch,
                        purchase_value=pv,
                        current_value=round(pv * random.uniform(0.4, 0.9), 2),
                        repair_cost_total=round(pv * random.uniform(0.01, 0.15), 2),
                        health_score=random.randint(55, 96),
                        sn=f"MFG-{asset_no.split('-')[-1]}",
                        next_maintain_date=_due_this_month(),
                        dept="工程维保部",
                        status=random.choice(["active", "active", "maintenance"]),
                    )
                )
            amts = db.query(Asset).filter_by(hotel_id=h.id).all()
            for a in amts[:3]:
                db.add(
                    AssetMaintenance(
                        hotel_id=h.id,
                        asset_id=a.id,
                        task_type="定期保养",
                        due_date=_due_this_month(),
                        status=random.choice(["scheduled", "overdue"]),
                        cost=round(random.uniform(100, 2000), 2),
                        note="主种子维保",
                        owner="工程部",
                    )
                )
        instay_bad_scores = [1.8, 2.4, 2.8, 3.2, 3.6]
        for h in hotels:
            for score in instay_bad_scores:
                g = random.choice(guests)
                db.add(
                    Review(
                        hotel_id=h.id,
                        guest_id=g.id,
                        channel_id=random.choice(channels).id,
                        rating=score,
                        content="",
                        replied=False,
                        reply_content=None,
                    )
                )
            for _ in range(20):
                g = random.choice(guests)
                db.add(
                    Review(
                        hotel_id=h.id,
                        guest_id=g.id,
                        channel_id=random.choice(channels).id,
                        rating=round(random.uniform(3.5, 5.0), 1),
                        content="",
                        replied=random.random() < 0.5,
                        reply_content="",
                    )
                )
            for ch, cn in [("douyin", "抖音探店挑战赛"), ("xiaohongshu", "小红书种草笔记"), ("geo", "商圈GEO品牌曝光")]:
                spend = round(random.uniform(2000, 20000), 2)
                rev = round(spend * random.uniform(1.5, 6), 2)
                db.add(
                    Campaign(
                        hotel_id=h.id,
                        channel=ch,
                        name=cn,
                        spend=spend,
                        attributed_rev=rev,
                        roi=round(rev / spend, 2),
                        start_date=TODAY - timedelta(days=20),
                        end_date=TODAY + timedelta(days=10),
                    )
                )
            db.add(
                RiskAlert(
                    hotel_id=h.id,
                    alert_type="供需",
                    level="高",
                    message=f"{h.city}门店未来7天预测入住率低于60%",
                    status="open",
                )
            )
            db.add(
                RiskAlert(
                    hotel_id=h.id, alert_type="舆情", level="中", message="近24小时出现2条3星以下评价", status="closed"
                )
            )
            db.add(
                RiskAlert(
                    hotel_id=h.id,
                    alert_type="信用",
                    level="高",
                    message="订单疑似拒付风险，建议预付验证",
                    status="open",
                )
            )
            db.add(
                RiskAlert(hotel_id=h.id, alert_type="安全", level="中", message="楼层门卡连续异常刷卡", status="open")
            )
            db.add(
                AiCommand(
                    hotel_id=h.id,
                    user_id=users[f"mgr{hotels.index(h) + 1}"].id,
                    utterance="把周五豪华大床房提价到520",
                    intent="price_adjust",
                    result="已生成价格建议 ORD-建议，待确认",
                )
            )
            db.add(
                AiCommand(
                    hotel_id=h.id,
                    user_id=users[f"mgr{hotels.index(h) + 1}"].id,
                    utterance="查一下今天有哪些退房",
                    intent="room_query",
                    result="今日预计退房 12 间",
                )
            )
        for h in hotels:
            for d in daterange_days(20, TODAY - timedelta(days=20)):
                rev = round(random.uniform(8000, 40000), 2)
                db.add(
                    NightAuditLog(
                        hotel_id=h.id,
                        biz_date=d,
                        status="passed",
                        exceptions=random.randint(0, 2),
                        revenue=rev,
                        room_nights=random.randint(40, 110),
                        ran_at=datetime.now(),
                    )
                )
            for m in range(6):
                p = (TODAY - timedelta(days=30 * m)).strftime("%Y-%m")
                occ = round(random.uniform(0.65, 0.92), 3)
                adr = round(random.uniform(380, 620), 2)
                db.add(FinanceReport(hotel_id=h.id, period=p, metric="occ", value=occ))
                db.add(FinanceReport(hotel_id=h.id, period=p, metric="adr", value=adr))
                db.add(FinanceReport(hotel_id=h.id, period=p, metric="revpar", value=round(occ * adr, 2)))
        for h in hotels:
            v1 = Venue(hotel_id=h.id, name="宴会厅A", capacity=200, hourly_rate=800)
            v2 = Venue(hotel_id=h.id, name="会议室B", capacity=40, hourly_rate=200)
            db.add(v1)
            db.add(v2)
            db.flush()
            db.add(
                VenueBooking(
                    hotel_id=h.id,
                    venue_id=v1.id,
                    event_name="公司年会",
                    event_date=TODAY + timedelta(days=10),
                    attendees=180,
                    amount=12000,
                    status="booked",
                )
            )
            db.add(
                VenueBooking(
                    hotel_id=h.id,
                    venue_id=v2.id,
                    event_name="产品发布会",
                    event_date=TODAY + timedelta(days=5),
                    attendees=35,
                    amount=2400,
                    status="booked",
                )
            )
        db.commit()
        print(f"Seed complete: {len(hotels)} hotel(s), {len(guests)} guests, {len(orders)} orders.")
        ensure_local_users(db)
        seed_finance_flow(db, hotels)
        enrich_revenue_anomalies(db, hotels)
        enrich_risk_alerts(db, hotels)
        seed_supplies_flow(db, hotels)
        enrich_supplies_rca_demo(db, hotels)
        seed_assets_flow(db, hotels)
        enrich_housekeeping_demo(db, hotels)
        from bootstrap.ensure_member_crm import ensure_member_crm

        ensure_member_crm(db)
        print("Member CRM segments backfilled.")
        from bootstrap.ensure_order_attribution import ensure_order_attribution

        atr = ensure_order_attribution(db)
        print(
            f"Order channel attribution: campaigns +{atr['campaigns_added']} · attributions +{atr['attributions_added']}"
        )
    finally:
        db.close()


# ---- 主 seed() 入口（调度器）----


def seed(reset=False):
    """主种子入口：建库 + 调 _seed_demo_data + enrich 子模块函数。"""
    db = SessionLocal()
    try:
        if db.query(Hotel).first() and not reset:
            # 已有数据：只跑 enrich，跳过主种子
            print("Data already present; skipping core seed (use --reset to rebuild).")
            hotels = db.query(Hotel).all()
            Base.metadata.create_all(engine)
            ensure_single_hotel_schema(engine)
            ensure_asset_schema(engine)
            ensure_supplies_schema(engine)
            ensure_local_users(db)
            seed_finance_flow(db, hotels)
            seed_supplies_flow(db, hotels)
            enrich_supplies_rca_demo(db, hotels)
            seed_assets_flow(db, hotels)
            enrich_housekeeping_demo(db, hotels)
            ensure_tag_rules(db)
            return

        # 无数据：从零灌（_seed_demo_data 内部关闭 db）
        _seed_demo_data(db, reset=reset)
        # 重新打开新 session 拿 hotels（避免 detached instance）
        db = SessionLocal()
        hotels = db.query(Hotel).all()

        # enrich 子模块（补强 demo 数据）
        ensure_local_users(db)
        seed_finance_flow(db, hotels)
        seed_supplies_flow(db, hotels)
        enrich_supplies_rca_demo(db, hotels)
        seed_assets_flow(db, hotels)
        enrich_housekeeping_demo(db, hotels)
        ensure_tag_rules(db)
    finally:
        db.close()
