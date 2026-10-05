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
from seed import risk as _seed_risk  # cross-submodule: enrich_revenue_anomalies / enrich_risk_alerts


def seed_finance_flow(db, hotels):
    """⑨ 日结财务合规：夜审异常 / 对账批次 / 报税 / 利润建议（幂等：表空才灌）。"""
    if db.query(ReconBatch).first():
        return
    for h in hotels:
        logs = db.query(NightAuditLog).filter_by(hotel_id=h.id).order_by(NightAuditLog.biz_date.desc()).limit(5).all()
        for i, log in enumerate(logs[:3]):
            samples = [
                (
                    "ROOM_MISMATCH",
                    "低",
                    f"{200 + i}房间状态不符",
                    "系统显示在住，客房状态为脏房。可能打扫未完成或状态未更新。",
                    "low",
                    "fixed" if i == 0 else "open",
                ),
                (
                    "BALANCE_OPEN",
                    "中",
                    f"{300 + i}账单未平",
                    f"客房已退房，仍有未结清余额 ¥{120 + i * 10:.2f}（迷你吧消费）。",
                    "mid",
                    "open" if i < 2 else "fixed",
                ),
                (
                    "RATE_OVERRIDE",
                    "高",
                    "人工改价未审批",
                    "豪华大床房当日房价被人工覆盖且无审批记录。",
                    "high",
                    "ignored" if i == 2 else "open",
                ),
            ]
            for code, _sev_cn, title, detail, severity, status in samples:
                db.add(
                    NightAuditException(
                        hotel_id=h.id,
                        audit_log_id=log.id,
                        biz_date=log.biz_date,
                        code=code,
                        title=title,
                        detail=detail,
                        severity=severity,
                        status=status,
                        fixed_at=datetime.now() if status == "fixed" else None,
                    )
                )
        from finance.recon_service import rebuild_recon_from_orders

        rebuild_recon_from_orders(db, h.id, days=14, as_of=TODAY)
        for m in range(3):
            period = (TODAY - timedelta(days=30 * m)).strftime("%Y-%m")
            inv_cnt = random.randint(40, 120)
            tax = round(random.uniform(8000, 35000), 2)
            st = "filed" if m > 0 else random.choice(["ready", "draft"])
            db.add(
                TaxFiling(
                    hotel_id=h.id,
                    period=period,
                    filing_type="vat",
                    tax_amount=tax,
                    invoice_count=inv_cnt,
                    status=st,
                    filed_at=datetime.now() - timedelta(days=30 * m) if st == "filed" else None,
                    note="增值税及附加" if st != "draft" else "待财务确认",
                )
            )
            db.add(
                TaxFiling(
                    hotel_id=h.id,
                    period=period,
                    filing_type="invoice_pack",
                    tax_amount=round(tax * 0.1, 2),
                    invoice_count=inv_cnt,
                    status="filed" if m > 0 else "ready",
                    filed_at=datetime.now() - timedelta(days=30 * m) if m > 0 else None,
                    note="电子发票汇总打包",
                )
            )
        insights = [
            ("rate", "高峰日提价空间", "周五/周六豪华大床房可在护栏内上调 3%~5%，预计周增收", 4200),
            ("channel", "压缩高佣金渠道配额", "OTA 佣金偏高时段可向企微/直订倾斜 10% 配额", 2800),
            ("cost", "布草洗涤成本优化", "本月洗涤超额，建议按预测入住率动态送洗", 960),
            ("tax", "进项票及时认证", "尚有未认证进项可抵扣，建议本周完成认证", 1500),
        ]
        for cat, title, rec, impact in insights:
            db.add(
                ProfitInsight(
                    hotel_id=h.id,
                    biz_date=TODAY,
                    title=title,
                    recommendation=rec,
                    impact_amount=impact,
                    category=cat,
                    status=random.choice(["open", "open", "accepted"]),
                )
            )
    db.commit()
    print("Finance flow seed written (night-audit / recon / tax / profit tips).")
    enrich_revenue_anomalies = _seed_risk.enrich_revenue_anomalies
    enrich_risk_alerts = _seed_risk.enrich_risk_alerts
    enrich_revenue_anomalies(db, hotels)
    enrich_risk_alerts(db, hotels)
