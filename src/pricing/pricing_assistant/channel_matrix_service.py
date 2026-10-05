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
from pricing.pricing_assistant import config_service as _pricing_config_service


def _est_n(net_anchor: float, channel: str, cfg: dict, promo: float = 0.0) -> float:
    """Net parity: N is the anchor; commission is reflected in channel list price."""
    return _pricing_common._money(max(0.0, float(net_anchor) - float(promo or 0)))


def _guest_price_from_base(
    net_anchor: float, channel: str, cfg: Optional[dict] = None, *, rate: Optional[float] = None, round_step: float = 10
) -> float:
    """channel_price = N / (1 - commission_rate)."""
    from finance.ota_commission_service import channel_price_from_net

    r = float(rate) if rate is not None else _pricing_config_service._commission_rate(cfg or {}, channel)
    raw = channel_price_from_net(float(net_anchor), r)
    return _round_to(raw, round_step) if round_step else _pricing_common._money(raw)


def _base_from_guest(
    guest_l: float, channel: str, cfg: Optional[dict] = None, *, rate: Optional[float] = None
) -> float:
    from finance.ota_commission_service import net_from_channel_price

    r = float(rate) if rate is not None else _pricing_config_service._commission_rate(cfg or {}, channel)
    return _pricing_common._money(net_from_channel_price(float(guest_l), r))


def build_channel_matrix(
    net_anchor: float,
    cfg: dict,
    *,
    db: Optional[Session] = None,
    hotel_id: Optional[int] = None,
    room_type_id: Optional[int] = None,
    on_date: Optional[date] = None,
    round_step: float = 10,
) -> list[dict]:
    """渠道分发行：与「系统配置 · OTA 佣金 · 渠道列表」同源，不摊开订单侧渠道。"""
    ordered: list[str] = []
    if db is not None:
        try:
            for row in _pricing_config_service._commission_channels_for_ui(db):
                code = str(row.get("code") or "").strip()
                if code and code not in ordered:
                    ordered.append(code)
        except Exception:
            ordered = []
    if not ordered:
        rates = cfg.get("commission") or DEFAULT_COMMISSION
        ordered = [c for c in DISPLAY_CHANNELS if c in rates or c in DEFAULT_COMMISSION]
    out = []
    for ch in ordered:
        r = _pricing_config_service._resolve_rate(db, hotel_id, ch, cfg=cfg, room_type_id=room_type_id, on_date=on_date)
        guest = _guest_price_from_base(net_anchor, ch, cfg, rate=r, round_step=round_step)
        out.append(
            {
                "channel": ch,
                "commission_rate": r,
                "commission_pct": round(r * 10000) / 100,
                "channel_price": guest,
                "net_price": _est_n(net_anchor, ch, cfg),
                "calc_mode": "net_parity",
            }
        )
    return out


def _round_to(n: float, step: float) -> float:
    if not step or step <= 0:
        return _pricing_common._money(n)
    return _pricing_common._money(round(n / step) * step)
