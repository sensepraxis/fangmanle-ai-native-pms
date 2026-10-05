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

from seed import LOCAL_USERS, TAGS
from seed import _common as _seed_common


def seed_local_users(db, hotels, roles):
    """为本店创建可登录的本地账号（幂等）。"""
    if not hotels:
        return
    h = hotels[0]
    for username, password, role_code, full_name in LOCAL_USERS:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            u = User(
                hotel_id=h.id,
                role_id=roles[role_code].id,
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                phone=_seed_common.phone(),
                is_active=True,
            )
            db.add(u)
        else:
            u.password_hash = hash_password(password)
            u.hotel_id = h.id
            u.role_id = roles[role_code].id
            u.full_name = full_name
    db.commit()
    print("Local accounts: admin/admin123 · gm/gm123 · revenue/rm123 · front/front123")


def ensure_tag_rules(db):
    """幂等回填标签可读规则（旧库 rule_expr 仅为 rule:code 时升级）。"""
    by_code = {code: rule for code, _name, _cat, rule in TAGS}
    updated = 0
    for t in db.query(TagDefinition).all():
        want = by_code.get(t.code)
        if not want:
            continue
        cur = (t.rule_expr or "").strip()
        if cur == want:
            continue
        if not cur or cur == f"rule:{t.code}" or cur == t.code or cur.startswith("rule:") or (cur == "规则待完善"):
            t.rule_expr = want
            updated += 1
    if updated:
        db.commit()
        print(f"Backfilled {updated} tag-rule copy strings.")
    else:
        print("Tag-rule copy is up to date; nothing to backfill.")
