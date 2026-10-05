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


def enrich_revenue_anomalies(db, hotels):
    """营收异常/欺诈监控样例（幂等）。"""
    if db.query(RevenueAnomaly).first():
        return
    import json

    samples = [
        {
            "code": "ANM-8924",
            "category": "price",
            "title": "未经审批的人工改价",
            "subtitle": "302 房间 • 前台 • John Doe",
            "score": 92,
            "tone": "high",
            "description": "AI 检测到一笔 45% 的人工折扣，超出标准促销窗口且缺少经理签字。",
            "detail_title": "人工改价",
            "actor": "John Doe",
            "room_label": "302 房间",
            "event_time": "今日 14:32",
            "orig": 1200,
            "new": 660,
            "diff": "-45%",
            "ai_hint": "需经理立即干预或自动冲正交易。用户历史存在类似模式。",
            "timeline": [
                {"tone": "primary", "title": "散客问询", "time": "14:15", "text": "John Doe 报出的标准价。"},
                {
                    "tone": "error",
                    "title": "人工改写价格",
                    "time": "14:32",
                    "text": "价格由 ¥1,200 改为 ¥660，未输入管理审批码。",
                },
                {
                    "tone": "tertiary",
                    "title": "AI 异常已触发",
                    "time": "14:33",
                    "text": "折扣超出散客标准额度（上限 15%），已标记以进行模式匹配。",
                    "ai": True,
                },
            ],
        },
        {
            "code": "ANM-8911",
            "category": "price",
            "title": "异常折扣模式",
            "subtitle": "多笔预订 • 周末群组",
            "score": 68,
            "tone": "mid",
            "description": "同一操作员 48 小时内连续开出 6 笔 ≥25% 折扣，偏离历史基线。",
            "detail_title": "异常折扣模式",
            "actor": "周末群组",
            "room_label": "多笔预订",
            "event_time": "今日 11:08",
            "orig": 4800,
            "new": 3360,
            "diff": "-30%",
            "ai_hint": "建议抽查操作员权限与促销码使用记录，必要时临时收紧折扣上限。",
            "timeline": [
                {"tone": "primary", "title": "群组预订创建", "time": "10:40", "text": "周末团队 8 间夜进入询价。"},
                {
                    "tone": "error",
                    "title": "连续折扣开出",
                    "time": "11:05",
                    "text": "6 笔折扣均 ≥25%，且未关联有效促销活动。",
                },
                {
                    "tone": "tertiary",
                    "title": "AI 模式告警",
                    "time": "11:08",
                    "text": "与该操作员近 30 日折扣分布显著偏离，已标记复核。",
                    "ai": True,
                },
            ],
        },
        {
            "code": "ANM-8902",
            "category": "void",
            "title": "作废交易异常",
            "subtitle": "POS 终端 2 • 餐厅",
            "score": 75,
            "tone": "mid",
            "description": "同一 POS 终端短时多次作废大额单，疑似套现或账实不符。",
            "detail_title": "作废交易异常",
            "actor": "POS 终端 2",
            "room_label": "餐厅",
            "event_time": "今日 12:46",
            "orig": 2180,
            "new": 0,
            "diff": "作废",
            "ai_hint": "建议核对当班收银录像与作废审批链，必要时锁定该终端。",
            "timeline": [
                {"tone": "primary", "title": "正餐结账", "time": "12:22", "text": "桌台 T12 开出 ¥2,180 账单。"},
                {"tone": "error", "title": "交易作废", "time": "12:41", "text": "未输入主管密码即作废，金额原路退回。"},
                {
                    "tone": "tertiary",
                    "title": "AI 异常已触发",
                    "time": "12:46",
                    "text": "该终端今日作废笔数已超阈值（3 笔）。",
                    "ai": True,
                },
            ],
        },
        {
            "code": "ANM-8876",
            "category": "ota",
            "title": "OTA 佣金渗漏",
            "subtitle": "Booking.com • 价格不符",
            "score": 34,
            "tone": "low",
            "description": "渠道卖价低于 PMS 底价，可能导致佣金与净收双损。",
            "detail_title": "OTA 佣金渗漏",
            "actor": "Booking.com",
            "room_label": "价格不符",
            "event_time": "昨日 22:10",
            "orig": 980,
            "new": 860,
            "diff": "-12%",
            "ai_hint": "建议核对渠道映射房价与 BAR，必要时暂停该房型推送。",
            "timeline": [
                {"tone": "primary", "title": "渠道房价同步", "time": "21:55", "text": "BAR ¥980 推送至 Booking.com。"},
                {"tone": "error", "title": "卖价偏离", "time": "22:08", "text": "渠道展示价 ¥860，低于底价护栏。"},
                {
                    "tone": "tertiary",
                    "title": "AI 渗漏提示",
                    "time": "22:10",
                    "text": "预估单间夜佣金与净收损失约 ¥45。",
                    "ai": True,
                },
            ],
        },
    ]
    for h in hotels:
        for s in samples:
            db.add(
                RevenueAnomaly(
                    hotel_id=h.id,
                    code=s["code"],
                    category=s["category"],
                    title=s["title"],
                    subtitle=s["subtitle"],
                    score=s["score"],
                    tone=s["tone"],
                    description=s["description"],
                    detail_title=s["detail_title"],
                    actor=s["actor"],
                    room_label=s["room_label"],
                    event_time=s["event_time"],
                    orig_amount=s["orig"],
                    new_amount=s["new"],
                    diff_label=s["diff"],
                    timeline_json=json.dumps(s["timeline"], ensure_ascii=False),
                    ai_hint=s["ai_hint"],
                    status="open",
                )
            )
    db.commit()
    print("Revenue anomaly / fraud monitor seed written.")


def enrich_risk_alerts(db, hotels):
    """经营风控预警样例：补齐到每店至少 4 条（幂等按数量）。"""
    for h in hotels:
        n = db.query(RiskAlert).filter_by(hotel_id=h.id).count()
        if n >= 4:
            continue
        extras = [
            ("信用", "高", "订单疑似拒付卡，建议预付验证", "open"),
            ("安全", "中", "连续多次门卡异常，疑似尾随", "open"),
            ("合规", "低", "夜审差异未自动核销", "closed"),
            ("舆情", "中", "渠道差评 2h 内未回复", "open"),
            ("供需", "高", "大型展会取消，未来 14 天需求骤降", "open"),
        ]
        for alert_type, level, msg, status in extras[: 4 - n]:
            db.add(RiskAlert(hotel_id=h.id, alert_type=alert_type, level=level, message=msg, status=status))
    db.commit()
    print("Ops risk alert seed backfilled.")
