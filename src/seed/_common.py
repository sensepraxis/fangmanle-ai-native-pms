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


def _due_this_month():
    """维保/排期：日期均匀落在当月，便于排期日历整月展示。"""
    last = calendar.monthrange(TODAY.year, TODAY.month)[1]
    return date(TODAY.year, TODAY.month, random.randint(1, last))


def name():
    from seed.locale_pack import get_pack, get_seed_locale

    pack = get_pack()
    if get_seed_locale() == "en":
        return f"{random.choice(pack.SURNAMES)} {random.choice(pack.GIVEN)}"
    return random.choice(pack.SURNAMES) + random.choice(pack.GIVEN)


def phone():
    return "1" + random.choice("356789") + "".join(random.choice("0123456789") for _ in range(9))


def daterange_days(n, start=TODAY):
    return [start + timedelta(days=i) for i in range(n)]


def math_sin_day(hour: int) -> float:
    """0~23 映射到白天高峰的平滑系数（约 0~1）。"""
    x = (hour - 6) / 12.0
    if x < 0 or x > 1.2:
        return 0.05
    return max(0.05, math.sin(math.pi * min(x, 1.0)))
