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

from seed import ASSET_FLOW_TPL
from seed import _common as _seed_common


def seed_assets_flow(db, hotels):
    """设备设施动线：告警/洞察/事件/盘点/维保（幂等：有 asset_alerts 则跳过）。"""
    from seed.locale_pack import seed_text as _st

    ensure_asset_schema(engine)
    ensure_supplies_schema(engine)
    Base.metadata.create_all(engine)
    if db.query(AssetAlert).first():
        seed_iot_metrics(db, hotels)
        return
    owners = [_st("张师傅"), _st("李工"), _st("王工"), _st("工程外包")]
    for h in hotels:
        existing = db.query(Asset).filter_by(hotel_id=h.id).all()
        by_name = {a.name: a for a in existing}
        assets = []
        for i, (name, cat, room, loc, asset_no, model, pv, score, insight, st) in enumerate(ASSET_FLOW_TPL):
            purch = date(2020 + i % 4, i % 12 + 1, 10)
            warranty = purch + timedelta(days=365 * (1 if score < 60 else 2))
            residual = round(pv * random.uniform(0.35, 0.85), 2)
            repair = round(pv * random.uniform(0.05, 0.38), 2) if score < 80 else round(pv * 0.02, 2)
            a = by_name.get(name)
            if a:
                a.category = cat
                a.location = loc or a.location
                a.room_no = room or None
                a.asset_no = asset_no
                a.sn = a.sn or f"MFG-{asset_no.split('-')[-1]}"
                a.brand_model = model
                a.purchase_date = a.purchase_date or purch
                a.purchase_value = a.purchase_value or pv
                a.current_value = residual
                a.repair_cost_total = repair
                a.health_score = score
                a.insight = insight
                a.warranty_until = warranty
                a.runtime_hours = random.randint(800, 9000)
                a.avg_power_w = round(random.uniform(40, 280), 1)
                a.next_maintain_date = _seed_common._due_this_month()
                a.supplier = random.choice(["厂家直供", "工程总包", "区域经销商"])
                a.dept = "工程维保部"
                a.status = st
            else:
                a = Asset(
                    hotel_id=h.id,
                    name=name,
                    category=cat,
                    location=loc or room,
                    room_no=room or None,
                    asset_no=asset_no,
                    sn=f"MFG-{asset_no.split('-')[-1]}",
                    brand_model=model,
                    purchase_date=purch,
                    purchase_value=pv,
                    current_value=residual,
                    repair_cost_total=repair,
                    health_score=score,
                    insight=insight,
                    warranty_until=warranty,
                    runtime_hours=random.randint(800, 9000),
                    avg_power_w=round(random.uniform(40, 280), 1),
                    next_maintain_date=_seed_common._due_this_month(),
                    supplier=random.choice(["厂家直供", "工程总包", "区域经销商"]),
                    dept="工程维保部",
                    status=st,
                )
                db.add(a)
                db.flush()
            assets.append(a)
        for a in existing:
            if not getattr(a, "asset_no", None):
                a.asset_no = getattr(a, "sn", None) or f"EQ-{a.id:05d}"
            if not getattr(a, "sn", None):
                a.sn = f"MFG-{a.id:04d}"
                a.health_score = a.health_score or random.randint(60, 95)
                a.category = a.category or "设备"
                a.insight = a.insight or "待完善台账"
                a.next_maintain_date = a.next_maintain_date or _seed_common._due_this_month()
                a.repair_cost_total = a.repair_cost_total or 0
                if a not in assets:
                    assets.append(a)
        db.flush()
        for a in assets:
            if a.health_score and a.health_score < 75:
                note = a.insight or "按计划维保"
                if a.health_score < 55 or a.status == "abnormal":
                    st = "doing" if random.random() < 0.4 else "overdue"
                    ttype = _st("紧急检修")
                else:
                    st = "scheduled"
                    ttype = _st("预防性保养")
                db.add(
                    AssetMaintenance(
                        hotel_id=h.id,
                        asset_id=a.id,
                        task_type=ttype,
                        due_date=a.next_maintain_date or _seed_common._due_this_month(),
                        status=st,
                        cost=round(random.uniform(120, 1800), 2),
                        note=note,
                        owner=random.choice(owners),
                    )
                )
            elif random.random() < 0.35:
                db.add(
                    AssetMaintenance(
                        hotel_id=h.id,
                        asset_id=a.id,
                        task_type=_st("定期保养"),
                        due_date=_seed_common._due_this_month(),
                        status="scheduled",
                        cost=round(random.uniform(80, 600), 2),
                        note=_st("季度例行"),
                        owner=random.choice(owners),
                    )
                )
            if a.repair_cost_total and float(a.repair_cost_total) > 200:
                db.add(
                    AssetMaintenance(
                        hotel_id=h.id,
                        asset_id=a.id,
                        task_type=_st("历史维修"),
                        due_date=TODAY - timedelta(days=random.randint(30, 200)),
                        status="done",
                        cost=round(float(a.repair_cost_total) * random.uniform(0.3, 0.7), 2),
                        note=_st("已归档维修"),
                        owner=random.choice(owners),
                        completed_at=datetime.now() - timedelta(days=random.randint(20, 180)),
                    )
                )
        alert_specs = [
            ("0102", "1F", "索尼 65寸 智能电视", "health", "mid", "待机功耗略升，建议纳入下周巡检"),
            ("0202", "2F", "大金中央空调", "health", "high", "运行功率偏高 20%，建议清洗滤网"),
            ("0210", "2F", "智能门锁", "iot", "high", "剩余电量低于 15%，预计可维持 3 天"),
            ("0105", "1F", "TOTO 智能马桶", "health", "high", "水压异常波动，建议立即检查水阀"),
            ("", "1F大堂", "大堂香氛机", "health", "mid", "香氛溶液预计明晚耗尽"),
            ("", "大堂", "客梯 A", "warranty", "mid", "本周例行检修窗口，请预留停梯时段"),
        ]
        name_to_id = {a.name: a.id for a in assets}
        for room_no, floor, aname, atype, sev, msg in alert_specs:
            db.add(
                AssetAlert(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    asset_id=name_to_id.get(_st(aname)),
                    room_no=room_no,
                    floor=_st(floor) if floor and not floor[0].isdigit() else floor,
                    asset_name=_st(aname),
                    alert_type=atype,
                    severity=sev,
                    message=_st(msg),
                    status="open",
                )
            )
        insight_specs = [
            (
                "maintain",
                "黄灯资产集中维保",
                "建议明日 11:00-14:00 低入住时段统一安排预防性维护，可自动生成工单。",
                0,
                None,
            ),
            (
                "replace",
                "丝涟床垫临近更换周期",
                "302 房床垫基于高入住率外推，约 2 个月后进入最佳更换末端。",
                8800,
                "丝涟床垫",
            ),
            (
                "roi",
                "大金空调维保成本偏高",
                "累计维保已接近原值 35%，建议评估 6 个月内整机置换。",
                4500,
                "大金中央空调",
            ),
            (
                "health",
                "弱电门锁电量集群风险",
                "5F 多把门锁电量告警，建议批量更换电池避免夜间开锁失败。",
                600,
                "智能门锁",
            ),
            ("audit", "固定物品盘点差异待核", "遥控器/吹风机等差异已入盘点表，请工程与房务联合复核。", 1200, None),
        ]
        for cat, title, rec, impact, aname in insight_specs:
            db.add(
                AssetInsight(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    asset_id=name_to_id.get(_st(aname)) if aname else None,
                    title=_st(title),
                    recommendation=_st(rec),
                    impact_amount=impact,
                    category=cat,
                    status=random.choice(["open", "open", "accepted"]),
                )
            )
        for a in assets[:4]:
            base = datetime.combine(a.purchase_date or TODAY - timedelta(days=800), datetime.min.time())
            db.add(
                AssetEvent(
                    hotel_id=h.id,
                    asset_id=a.id,
                    event_type="purchase",
                    title=_st("入库采购"),
                    happened_at=base,
                    note=f"{_st('供应商')}：{a.supplier or '—'}",
                    cost=float(a.purchase_value or 0),
                    owner=_st("采购部"),
                )
            )
            db.add(
                AssetEvent(
                    hotel_id=h.id,
                    asset_id=a.id,
                    event_type="install",
                    title=_st("初次安装"),
                    happened_at=base + timedelta(days=3),
                    note=f"{_st('安装于')} {a.location or a.room_no or '—'}",
                    owner=_st("工程部"),
                )
            )
            if float(a.repair_cost_total or 0) > 100:
                db.add(
                    AssetEvent(
                        hotel_id=h.id,
                        asset_id=a.id,
                        event_type="repair",
                        title=_st("历次维保/维修"),
                        happened_at=datetime.now() - timedelta(days=random.randint(40, 200)),
                        note=a.insight or _st("维修归档"),
                        cost=float(a.repair_cost_total or 0) * 0.4,
                        owner=random.choice(owners),
                    )
                )
            if a.health_score and a.health_score < 80:
                db.add(
                    AssetEvent(
                        hotel_id=h.id,
                        asset_id=a.id,
                        event_type="predict",
                        title=_st("AI 故障预测点"),
                        happened_at=datetime.now(),
                        note=a.insight or _st("建议生成预防性工单"),
                        owner="AI",
                    )
                )
        audit_rows = [
            ("空调滤网", 40, 2, "多楼层空调清洗后滤网库存告急，建议紧急补货。", "high"),
            ("淋浴喷头", 60, 15, "客房卫浴备件水位偏低。", "mid"),
            ("客房遥控器", 240, 228, "高度疑似客带离或房务漏扫，近 3 天入住率偏高。", "high"),
            ("壁挂吹风机", 120, 117, "3 间房标签离线，待工程复核。", "mid"),
            ("智能门锁电池", 80, 71, "批量更换后库存未回写，疑似账实不同步。", "mid"),
            ("迷你吧冰箱", 96, 96, "账实一致。", "low"),
        ]
        for name, theo, actual, risk, sev in audit_rows:
            db.add(
                AssetAuditItem(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    name=name,
                    theoretical_qty=theo,
                    actual_qty=actual,
                    risk=risk,
                    severity=sev,
                    status="open" if theo != actual else "closed",
                )
            )
    db.commit()
    print("Asset/facility seed written (ledger / alerts / insights / events / inventory / maintenance).")
    seed_iot_metrics(db, hotels)


def seed_iot_metrics(db, hotels):
    """客房 IoT 能耗/温湿度时序（幂等：有 room_iot_metrics 则跳过）。"""
    Base.metadata.create_all(engine)
    if db.query(RoomIotMetric).first():
        return
    if not hotels:
        return
    for h in hotels:
        for floor in ("1F", "2F"):
            for i in range(24):
                hour = i
                base = 28 + 18 * max(0, _seed_common.math_sin_day(hour))
                spike = 12 if hour in (9, 10) and floor == "1F" else 0
                energy = round(base + spike + random.uniform(-1.2, 1.2), 2)
                temp = round(
                    22.5 + 3.2 * max(0, (hour - 6) / 10) - (0.8 if hour >= 20 else 0) + random.uniform(-0.3, 0.3), 1
                )
                humidity = round(58 - 0.7 * (temp - 22.5) + random.uniform(-1.5, 1.5), 1)
                humidity = max(35.0, min(75.0, humidity))
                recorded = datetime.combine(TODAY, datetime.min.time()) + timedelta(hours=hour)
                db.add(
                    RoomIotMetric(
                        hotel_id=h.id,
                        floor=floor,
                        recorded_at=recorded,
                        energy_kw=energy,
                        temp_c=temp,
                        humidity_pct=humidity,
                    )
                )
    db.commit()
    print("Room IoT time-series seed written (energy / temp-humidity).")
