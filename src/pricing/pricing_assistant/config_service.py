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

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from analytics.forecast_service import build_revenue_forecast
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
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


def get_or_create_config(db: Session, hotel_id: int) -> PricingAssistantConfig:
    cfg = db.query(PricingAssistantConfig).filter_by(hotel_id=hotel_id).first()
    if cfg:
        if (cfg.execution_mode or "") != "assisted" or cfg.delegated_enabled:
            cfg.execution_mode = "assisted"
            cfg.delegated_enabled = False
        return cfg
    for obj in db.new:
        if isinstance(obj, PricingAssistantConfig) and obj.hotel_id == hotel_id:
            return obj
    cfg = PricingAssistantConfig(
        hotel_id=hotel_id,
        execution_mode="assisted",
        delegated_enabled=False,
        commission_json=_pricing_common._json_dumps(DEFAULT_COMMISSION),
    )
    sp = db.begin_nested()
    db.add(cfg)
    try:
        db.flush()
        sp.commit()
    except IntegrityError:
        sp.rollback()
        cfg = db.query(PricingAssistantConfig).filter_by(hotel_id=hotel_id).first()
        if cfg is None:
            raise
    return cfg


def get_config_dict(db: Session, hotel_id: int) -> dict:
    cfg = get_or_create_config(db, hotel_id)
    params = {**DEFAULT_PARAMS, **_pricing_common._json_loads(getattr(cfg, "params_json", None), {})}
    params["ev_cap"] = 100
    params["agg_mult"] = DEFAULT_PARAMS["agg_mult"]
    comp_count = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).count()
    return {
        "hotel_id": hotel_id,
        "execution_mode": "assisted",
        "delegated_enabled": False,
        "comp_compare_enabled": bool(getattr(cfg, "comp_compare_enabled", False)),
        "comp_count": comp_count,
        "params": params,
        "self_location": params.get("self_location") or {},
        "comp_radius_km": float(params.get("comp_radius_km") or 3),
        "commission": _commission_dict(db, cfg),
        "commission_channels": _commission_channels_for_ui(db),
        "circuit_breakers": {
            "n_drop_pct": 10,
            "single_drop_pct": 20,
            "parity_days": 3,
            "passive_drops_7d": 3,
            "event_uplift_max": 100,
        },
    }


def _commission_dict(db: Session, cfg: PricingAssistantConfig) -> dict:
    try:
        from finance.ota_commission_service import commission_map_for_pricing

        ch_rates = commission_map_for_pricing(db)
    except Exception:
        ch_rates = {}
    return {**DEFAULT_COMMISSION, **_pricing_common._json_loads(cfg.commission_json, {}), **ch_rates}


def _commission_channels_for_ui(db: Session) -> list[dict]:
    """价格助手展示用渠道条：与 OTA 佣金页 list 同源，仅启用中的档案渠道。"""
    try:
        from finance.ota_commission_service import list_ota_commission_channels

        rows = list_ota_commission_channels(db)
    except Exception:
        rows = []
    out = []
    for r in rows:
        if not r.get("is_enabled", True):
            continue
        code = r.get("code") or r.get("channel_code")
        if not code:
            continue
        out.append(
            {
                "code": code,
                "name": r.get("name") or r.get("channel_name") or code,
                "commission_rate": float(r.get("commission_rate") or 0),
                "commission_pct": float(r.get("commission_pct") or 0),
            }
        )
    return out


def sync_commission_from_channels(db: Session, hotel_id: int) -> dict:
    """系统设置保存佣金后同步镜像到价格助手 config（PA 不编辑）。"""
    from finance.ota_commission_service import commission_map_for_pricing

    cfg = get_or_create_config(db, hotel_id)
    rates = {**DEFAULT_COMMISSION, **commission_map_for_pricing(db)}
    cfg.commission_json = _pricing_common._json_dumps(rates)
    cfg.updated_at = datetime.now()
    db.commit()
    return rates


def update_config(db: Session, hotel_id: int, payload: dict) -> dict:
    cfg = get_or_create_config(db, hotel_id)
    if payload.get("execution_mode") is not None:
        cfg.execution_mode = "assisted"
    if "delegated_enabled" in payload:
        cfg.delegated_enabled = False
    if "comp_compare_enabled" in payload:
        cfg.comp_compare_enabled = bool(payload["comp_compare_enabled"])
    if payload.get("params"):
        cur = {**DEFAULT_PARAMS, **_pricing_common._json_loads(getattr(cfg, "params_json", None), {})}
        incoming = dict(payload["params"])
        if "ev_cap" in incoming:
            incoming["ev_cap"] = min(float(incoming["ev_cap"]), 100)
        for k in ("ev_weak", "ev_mid", "ev_strong", "ev_boom", "hol_short", "hol_mid", "hol_long"):
            if k in incoming:
                incoming[k] = min(float(incoming[k]), float(incoming.get("ev_cap", cur.get("ev_cap", 100))))
        if "ev_heat" in incoming or "ev_heat_demo" in incoming:
            heat_v = float(incoming.get("ev_heat_demo", incoming.get("ev_heat", 95)))
            incoming["ev_heat_demo"] = max(0.0, min(100.0, heat_v))
            incoming.pop("ev_heat", None)
        if "ev_heat_map" in incoming:
            incoming["ev_heat_map"] = max(0.1, min(2.0, float(incoming["ev_heat_map"])))
        if "agg" in incoming and incoming["agg"] not in ("conservative", "balanced", "aggressive"):
            raise InvalidStateError("agg must be conservative/balanced/aggressive")
        cur.update(incoming)
        cur["ev_cap"] = 100
        cur["agg_mult"] = DEFAULT_PARAMS["agg_mult"]
        cfg.params_json = _pricing_common._json_dumps(cur)
        db.add(
            PricingDecision(
                decision_id=_pricing_common._sid("dec_"),
                reco_id="params_update",
                hotel_id=hotel_id,
                decision="ignore",
                decided_by=str(payload.get("staff_no") or "system")[:32],
                decided_at=datetime.now(),
                before_price=None,
                after_price=None,
                reason_note=f"定价参数更新: {json.dumps(incoming, ensure_ascii=False)[:200]}",
                audit_id=_pricing_common._sid("aud_"),
            )
        )
    cfg.updated_at = datetime.now()
    db.commit()
    return get_config_dict(db, hotel_id)


def _commission_rate(cfg: dict, channel: str) -> float:
    return float(cfg.get("commission", {}).get(channel, DEFAULT_COMMISSION.get(channel, 0.12)))


def _resolve_rate(
    db: Optional[Session],
    hotel_id: Optional[int],
    channel: str,
    *,
    cfg: Optional[dict] = None,
    room_type_id: Optional[int] = None,
    on_date: Optional[date] = None,
) -> float:
    """Prefer resolve_commission_rate (overrides); else config commission map."""
    if db is not None and hotel_id and channel:
        try:
            from finance.ota_commission_service import resolve_commission_rate

            return float(
                resolve_commission_rate(db, int(hotel_id), channel, room_type_id=room_type_id, on_date=on_date) or 0
            )
        except Exception:
            pass
    if cfg is not None:
        return _commission_rate(cfg, channel)
    return float(DEFAULT_COMMISSION.get(channel, 0.12))
