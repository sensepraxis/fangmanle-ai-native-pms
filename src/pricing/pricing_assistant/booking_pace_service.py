# SPDX-License-Identifier: Apache-2.0
"""
价格助手服务：特征层 + §5.6 规则优化 + 三档执行 + 审计三联单。
合规铁律：仅建议、人拍板、绝不自动跟价/爬登录态。
"""

from __future__ import annotations

import hashlib
import json
import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from analytics.forecast_service import build_revenue_forecast
from models import (
    CompetitorProperty,
    CompetitorRateSnapshot,
    CompetitorRoomMap,
    CompetitorSet,
    EventCalendar,
    Order,
    PaceSnapshot,
    ParityAlert,
    PricingAssistantConfig,
    PricingDecision,
    PricingEffect,
    PricingRecommendation,
    Room,
    RoomType,
    RoomTypeBaseRate,
)

DEFAULT_COMMISSION = {
    "ota_ctrip": 0.12,
    "ota_meituan": 0.1,
    "ota_fliggy": 0.08,
    "ota_douyin": 0.08,
    "ota_tongcheng": 0.12,
    "ota_elong": 0.1,
    "jd": 0.0,
    "direct": 0.0,
    "member": 0.0,
    "ota_agoda": 0.15,
    "corp": 0.0,
}
INTENSITY_UPLIFT = {"弱": 0.15, "中": 0.3, "强": 0.5, "爆": 0.8}
DISPLAY_CHANNELS = [
    "direct",
    "ota_ctrip",
    "ota_meituan",
    "ota_fliggy",
    "ota_douyin",
    "member",
    "ota_tongcheng",
    "ota_elong",
    "jd",
    "ota_agoda",
]
DEFAULT_PARAMS = {
    "agg": "balanced",
    "agg_mult": {"conservative": 0.7, "balanced": 1.0, "aggressive": 1.3},
    "target_occ": 78,
    "round": 10,
    "ev_weak": 15,
    "ev_mid": 30,
    "ev_strong": 50,
    "ev_boom": 80,
    "ev_heat_map": 1.0,
    "ev_heat_demo": 95,
    "hol_short": 15,
    "hol_mid": 30,
    "hol_long": 45,
    "ev_cap": 100,
    "ev_km": 5,
    "pace_up": 1.1,
    "pace_down": 0.9,
    "comp_w": 1.0,
    "comp_radius_km": 3,
    "comp_distance_mode": "soft",
    "cap_pct": 50,
    "cost_pct": 55,
    "n_floor": 240,
    "fair_ev": 80,
    "fair_day": 30,
    "step_pct": 15,
}
AGG_LABEL = {"conservative": "保守", "balanced": "均衡", "aggressive": "激进"}

from pricing.pricing_assistant import _common as _pricing_common


def _rooms_count(db: Session, hotel_id: int) -> int:
    return max(db.query(Room).filter_by(hotel_id=hotel_id).count(), 1)


def _booked_for_date(db: Session, hotel_id: int, stay: date, room_type_id: Optional[int] = None) -> int:
    orders = (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["reserved", "confirmed", "checked_in", "pending"]),
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= stay,
            Order.check_out > stay,
        )
        .all()
    )
    total = 0
    for o in orders:
        if room_type_id and o.room_type_id and (int(o.room_type_id) != int(room_type_id)):
            continue
        total += max(1, int(o.rooms or 1))
    return total


def _orders_on_stay(db: Session, hotel_id: int, stay: date) -> list:
    return (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(["reserved", "confirmed", "checked_in", "pending", "checked_out"]),
            Order.check_in.isnot(None),
            Order.check_out.isnot(None),
            Order.check_in <= stay,
            Order.check_out > stay,
        )
        .all()
    )


def _self_adr_for_date(db: Session, hotel_id: int, stay: date) -> Optional[float]:
    """本店 ADR：优先订单单价；无单价则用总价/间夜；再无则用当日已采纳/待处理建议价均值。"""
    orders = _orders_on_stay(db, hotel_id, stay)
    rev = 0.0
    rooms_n = 0
    for o in orders:
        r = max(1, int(o.rooms or 1))
        up = float(getattr(o, "unit_price", None) or 0)
        if up > 0:
            rev += up * r
            rooms_n += r
            continue
        nights = int(o.nights or 0)
        if nights <= 0 and o.check_in and o.check_out:
            nights = max(1, (o.check_out - o.check_in).days)
        nights = max(1, nights)
        amt = float(o.total_amount or 0)
        if amt > 0:
            rev += amt / nights * r
            rooms_n += r
    if rooms_n > 0:
        return _pricing_common._money(rev / rooms_n)
    recos = (
        db.query(PricingRecommendation)
        .filter(
            PricingRecommendation.hotel_id == hotel_id,
            PricingRecommendation.stay_date == stay,
            PricingRecommendation.status.in_(["accepted", "pending", "auto_executed"]),
            PricingRecommendation.channel == "direct",
        )
        .all()
    )
    prices = [float(r.suggested_price or r.current_price or 0) for r in recos if r.suggested_price or r.current_price]
    if prices:
        return _pricing_common._money(sum(prices) / len(prices))
    return None


def _ota_min_for_date(db: Session, hotel_id: int, stay: date) -> Optional[float]:
    """竞品公开价当日最低（真实快照，不造数）。"""
    rows = db.query(CompetitorRateSnapshot).filter_by(hotel_id=hotel_id, stay_date=stay).all()
    vals = [float(r.observed_price) for r in rows if r.observed_price]
    return _pricing_common._money(min(vals)) if vals else None


def _pct_delta(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    if cur is None or prev is None or prev <= 0:
        return None
    return round((cur - prev) / prev * 100, 1)


def get_pace(db: Session, hotel_id: int, stay: date, room_type_id: Optional[int] = None) -> dict:
    q = db.query(PaceSnapshot).filter_by(hotel_id=hotel_id, stay_date=stay)
    if room_type_id:
        q = q.filter(PaceSnapshot.room_type_id == room_type_id)
    row = q.order_by(PaceSnapshot.id.desc()).first()
    if row:
        return {
            "booked": int(row.booked or 0),
            "expected": int(row.expected or 1),
            "pace_ratio": float(row.pace_ratio or 1),
            "source": "pace_snapshot",
        }
    rooms = _rooms_count(db, hotel_id)
    booked = _booked_for_date(db, hotel_id, stay, room_type_id)
    expected = max(1, int(rooms * 0.7))
    return {
        "booked": booked,
        "expected": expected,
        "pace_ratio": round(booked / expected, 2),
        "source": "orders_derived",
    }


def list_data_sources(db: Session, hotel_id: int) -> list[dict]:
    props = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).all()
    out = []
    for p in props:
        last = (
            db.query(CompetitorRateSnapshot)
            .filter_by(comp_id=p.comp_id)
            .order_by(CompetitorRateSnapshot.captured_at.desc())
            .first()
        )
        level = {"rate_shopping": "P0", "manual": "P1", "public_scrape": "P2"}.get(p.data_source or "manual", "P1")
        out.append(
            {
                "comp_name": p.comp_name,
                "data_source": p.data_source,
                "compliance_level": level,
                "frequency": "手工/按需" if p.data_source == "manual" else "≤4次/天",
                "last_captured": last.captured_at.isoformat() if last and last.captured_at else None,
                "status": "正常",
            }
        )
    return out
