# SPDX-License-Identifier: Apache-2.0
"""
房满乐 PMS —— 假数据种子（用，真实可替换）。
生成 1 家酒店 + 全模块示例数据。运行: python seed.py [--reset]
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

from seed import _common as _seed_common


def seed_supplies_flow(db, hotels):
    """⑧ 物资双线：布草周转 + 易耗消耗（幂等：有 restock_orders 则跳过）。"""
    if db.query(RestockOrder).first():
        return
    vendors = ["雅致洗护专供", "纺织精工", "洁净日化", "醇香咖啡豆坊", "客房易耗品仓"]
    for h in hotels:
        supplies = db.query(Supply).filter_by(hotel_id=h.id).all()
        by_name = {s.name: s for s in supplies}
        rooms = db.query(Room).filter_by(hotel_id=h.id).limit(40).all()
        for d in _seed_common.daterange_days(7, TODAY - timedelta(days=6)):
            for item_type, base in [("床单", 450), ("浴巾", 800), ("枕套", 400), ("面巾", 600)]:
                in_room = int(base * random.uniform(0.3, 0.48))
                pending = int(base * random.uniform(0.12, 0.22))
                washing = int(base * random.uniform(0.18, 0.35))
                storage = max(0, base - in_room - pending - washing - int(base * 0.02))
                discarded = max(0, base - in_room - pending - washing - storage)
                db.add(
                    LinenSnapshot(
                        hotel_id=h.id,
                        biz_date=d,
                        item_type=item_type,
                        in_room=in_room,
                        pending_wash=pending,
                        in_wash=washing,
                        in_storage=storage,
                        discarded=discarded,
                    )
                )
        amenity_alerts = [
            ("0102", "1F", "牙具套装", "high", "单日消耗 x5，远超均值"),
            ("0104", "1F", "洗发水", "mid", "洗发水补货偏频（客诉加换）"),
            ("0203", "2F", "拖鞋", "mid", "拖鞋消耗偏高"),
            ("0108", "1F", "洗发水", "low", "轻微超耗"),
            ("0212", "2F", "矿泉水", "high", "迷你吧补货频繁"),
        ]
        for room_no, floor, sname, sev, msg in amenity_alerts:
            db.add(
                SupplyAlert(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    line="amenity",
                    room_no=room_no,
                    floor=floor,
                    supply_name=sname,
                    severity=sev,
                    message=msg,
                    status="open",
                )
            )
        db.add(
            SupplyAlert(
                hotel_id=h.id,
                biz_date=TODAY,
                line="linen",
                room_no="",
                floor="洗衣房",
                supply_name="浴巾",
                severity="high",
                message="洗涤产能不足，预计 11:00 前仓储耗尽",
                status="open",
            )
        )
        cat_name = {c.id: c.name for c in db.query(SupplyCategory).filter_by(hotel_id=h.id).all()}
        amenity_supplies = [s for s in supplies if cat_name.get(s.category_id) != "布草"]
        if not amenity_supplies:
            amenity_supplies = supplies
        low = [s for s in amenity_supplies if float(s.current_stock or 0) <= float(s.safety_stock or 0) * 1.2]
        if not low:
            low = amenity_supplies[:3]
        for oi, chunk in enumerate([low[:3], low[3:6] or low[:2]]):
            if not chunk:
                continue
            total = 0.0
            order = RestockOrder(
                hotel_id=h.id,
                order_no=f"PO-{h.id}-{TODAY.strftime('%m%d')}-{oi + 1:02d}",
                vendor=vendors[oi % len(vendors)],
                status="submitted" if oi == 0 else "draft",
                total_amount=0,
                note="AI 建议补货" if oi == 0 else "待店长确认",
            )
            db.add(order)
            db.flush()
            for s in chunk:
                need = max(10, int(float(s.safety_stock or 50) - float(s.current_stock or 0) + 40))
                cost = float(s.unit_cost or 10)
                amt = round(need * cost, 2)
                total += amt
                urg = (
                    "critical"
                    if float(s.current_stock or 0) < float(s.safety_stock or 0) * 0.5
                    else "high"
                    if float(s.current_stock or 0) < float(s.safety_stock or 0)
                    else "normal"
                )
                db.add(
                    RestockItem(
                        order_id=order.id,
                        hotel_id=h.id,
                        supply_id=s.id,
                        name=s.name,
                        qty=need,
                        unit_cost=cost,
                        amount=amt,
                        urgency=urg,
                    )
                )
            order.total_amount = round(total, 2)
        staff_pool = [
            ("李阿姨", "清洁一组"),
            ("王大姐", "清洁二组"),
            ("张小妹", "清洁一组"),
            ("刘师傅", "工程部"),
            ("陈姐", "客房部"),
        ]
        for i in range(18):
            s = random.choice(supplies)
            who, dept = staff_pool[i % len(staff_pool)]
            qty = random.randint(12, 28) if who == "张小妹" else random.randint(2, 14)
            if who == "李阿姨":
                qty = random.randint(2, 8)
            db.add(
                SupplyRequisition(
                    hotel_id=h.id,
                    supply_id=s.id,
                    supply_name=s.name,
                    qty=qty,
                    dept=dept,
                    requester=who,
                    status=random.choice(["issued", "issued", "returned"]),
                    note="日常领用",
                    created_at=datetime.now() - timedelta(hours=i * 3),
                )
            )
            db.add(
                StockMovement(
                    hotel_id=h.id,
                    supply_id=s.id,
                    movement_type=random.choice(["issue", "issue", "restock", "damage", "adjust"]),
                    qty=random.randint(2, 30),
                    note="双线流水",
                )
            )
        damage_samples = [
            (
                "amenity",
                "302",
                "电热水壶 (不通电)",
                "电器 (电视、空调、冰箱)",
                "medium",
                "客房电热水壶不通电，疑似加热管损坏。",
                0,
                "repairing",
                "建议分配给工程部检修加热管，预计 20 分钟。",
                "客人今晚入住，建议 18:00 前处理。",
                "电器,热水壶",
            ),
            (
                "amenity",
                "512",
                "休闲椅 (布面撕裂)",
                "家具 (床、桌椅、衣柜)",
                "medium",
                "休闲椅布面撕裂，影响观感。",
                450,
                "scrapped",
                "建议更换椅面或整椅报废置换。",
                "公共区客流量高，尽快闭环。",
                "家具,椅",
            ),
            (
                "amenity",
                "208",
                "花洒软管 (漏水)",
                "卫浴/管道 (马桶、淋浴、水龙头)",
                "high",
                "浴室花洒软管漏水，地面湿滑。",
                45,
                "replaced",
                "建议分配给工程部王师傅更换软管，预计 30 分钟。",
                "该房有预订，需今日完成。",
                "卫浴,漏水,加急",
            ),
            (
                "linen",
                "洗衣房",
                "浴巾批次#402 破损",
                "布草 (床单、毛巾、浴袍)",
                "low",
                "洗涤后发现破损，无法再投用。",
                320,
                "scrapped",
                "建议报废并触发补货。",
                "不影响在住房态。",
                "布草,报废",
            ),
            (
                "linen",
                "405",
                "床单严重污渍无法洗净",
                "布草 (床单、毛巾、浴袍)",
                "medium",
                "床单顽固污渍，多次洗涤无效。",
                180,
                "open",
                "建议报废并自库存替换。",
                "明日有入住，请今日换新。",
                "布草,污渍",
            ),
            (
                "amenity",
                "301",
                "牙具套装整箱受潮",
                "五金件 (门锁、合页)",
                "low",
                "库房受潮导致牙具套装报损。",
                260,
                "open",
                "建议报废并补货。",
                "库存紧张，尽快补货。",
                "易耗,受潮",
            ),
            (
                "amenity",
                "8201",
                "浴室水龙头漏水",
                "卫浴/管道 (马桶、淋浴、水龙头)",
                "medium",
                "浴室水龙头漏水，开关不灵敏。",
                120,
                "open",
                "建议分配给工程部王师傅进行水管阀门芯更换，预计耗时 30 分钟。",
                "该房间明天有客人入住，建议在今天 16:00 前完成维修，避免产生客诉。",
                "卫浴,漏水,加急",
            ),
        ]
        for line, room_no, item, cat, sev, desc, fee, st, ai_s, ai_r, tags in damage_samples:
            db.add(
                DamageTicket(
                    hotel_id=h.id,
                    line=line,
                    room_no=room_no,
                    item_name=item,
                    asset_category=cat,
                    severity=sev,
                    description=desc,
                    photos='["demo://faucet"]' if "漏水" in item or "水龙头" in item else "[]",
                    ai_suggestion=ai_s,
                    ai_risk=ai_r,
                    ai_tags=tags,
                    fee=fee,
                    status=st,
                    note=desc[:80],
                    resolved_at=datetime.now() if st in ("replaced", "scrapped", "closed") else None,
                )
            )
        linen_insights = [
            ("turnover", "高短缺风险：浴巾", "明日高入住叠加洗涤时长，建议批次#402 加急烘干", 800),
            ("forecast", "床单外洗窗口", "本周五洗涤产能见顶，可预约外洗 120 条缓冲", 1200),
            ("replace", "枕套进入待换阶段", "洗涤次数>80 的枕套占比升高，建议本月置换 60 条", 2400),
            ("loss", "报废率偏高", "本周浴巾报废高于均值，建议核查洗涤温度与烘干参数", 600),
        ]
        amenity_insights = [
            ("restock", "牙具低于安全库存", "当前库存紧张，建议采购 100 套并开启自动补货", 1200),
            ("forecast", "洗发水 14 天预测缺口", "按入住率外推将于 9 天后触底，建议提前下单", 900),
            ("rca", "3F 消耗异常", "302/304 牙具与毛巾异常，建议抽查是否多领或客诉加换", 0),
            ("loss", "拖鞋盘亏待核对", "盘点差额 18 双，优先核对领用单与客房补货记录", 150),
        ]
        for cat, title, rec, impact in linen_insights:
            db.add(
                SupplyInsight(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    line="linen",
                    title=title,
                    recommendation=rec,
                    impact_amount=impact,
                    category=cat,
                    status=random.choice(["open", "open", "accepted"]),
                )
            )
        for cat, title, rec, impact in amenity_insights:
            db.add(
                SupplyInsight(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    line="amenity",
                    title=title,
                    recommendation=rec,
                    impact_amount=impact,
                    category=cat,
                    status=random.choice(["open", "open", "accepted"]),
                )
            )
        linens = db.query(Linen).filter_by(hotel_id=h.id).limit(80).all()
        for i, ln in enumerate(linens):
            if i % 5 == 0:
                ln.status = "dirty"
            elif i % 5 == 1:
                ln.status = "in_wash"
            elif i % 7 == 0:
                ln.lifecycle_stage = "待换"
                ln.wash_count = random.randint(80, 120)
    db.commit()
    print("Supplies dual-track seed written (linen / alerts / replenish / issue / write-off / insights).")


def enrich_supplies_rca_demo(db, hotels):
    """已有库：把领用人补成保洁姓名，并补往月 loss 洞察（幂等）。"""
    rename = {"小王": "王大姐", "小李": "李阿姨", "张姐": "张小妹"}
    dept_map = {"李阿姨": "清洁一组", "王大姐": "清洁二组", "张小妹": "清洁一组", "刘师傅": "工程部"}
    changed = 0
    for r in db.query(SupplyRequisition).all():
        new_name = rename.get(r.requester)
        if new_name:
            r.requester = new_name
            r.dept = dept_map.get(new_name, r.dept or "客房部")
            changed += 1
        elif r.requester in dept_map and (not r.dept or r.dept in ("客房部", "前台", "餐饮", "工程")):
            r.dept = dept_map[r.requester]
            changed += 1
    for h in hotels:
        hist = [
            (
                TODAY.replace(day=1) - timedelta(days=1),
                "loss",
                "9月盘点收口",
                "布草报废率较高，已建议更换供应商。",
                480,
            ),
            (
                (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1),
                "loss",
                "8月盘点收口",
                "表现良好，在标准阈值内。",
                120,
            ),
        ]
        for biz, cat, title, rec, impact in hist:
            exists = db.query(SupplyInsight).filter_by(hotel_id=h.id, title=title).first()
            if exists:
                continue
            db.add(
                SupplyInsight(
                    hotel_id=h.id,
                    biz_date=biz,
                    line="amenity",
                    title=title,
                    recommendation=rec,
                    impact_amount=impact,
                    category=cat,
                    status="accepted",
                )
            )
            changed += 1
    if changed:
        db.commit()
        print(f"Supplies RCA backfilled (issuers / prior-month insights ×{changed}).")
