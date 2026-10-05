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

from fastapi import HTTPException  # noqa: F401  (except 分支用)
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

from infra.i18n import t
from pricing.pricing_assistant import _common as _pricing_common
from pricing.pricing_assistant import booking_pace_service as _pricing_booking_pace_service
from pricing.pricing_assistant import channel_matrix_service as _pricing_channel_matrix_service
from pricing.pricing_assistant import config_service as _pricing_config_service
from pricing.pricing_assistant import event_service as _pricing_event_service


def _comp_median_guest(
    db: Session,
    hotel_id: int,
    stay: date,
    room_type_id: Optional[int] = None,
    channel: str = "ota_ctrip",
    default_w: float = 1.0,
    params: Optional[dict] = None,
) -> Optional[float]:
    """竞品同渠道客付挂牌价加权中位数（like-for-like · weight · 距离可比性）。"""
    params = {**DEFAULT_PARAMS, **(params or {})}
    radius = float(params.get("comp_radius_km") or 5)
    mode = str(params.get("comp_distance_mode") or "soft").strip().lower()
    props = {p.comp_id: p for p in db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).all()}
    weight_by_comp: dict[str, float] = {}
    preferred_names: set[str] = set()
    if room_type_id:
        rt = db.get(RoomType, room_type_id)
        if rt and rt.name:
            preferred_names.add(str(rt.name).strip())
        maps = (
            db.query(CompetitorRoomMap)
            .filter_by(hotel_id=hotel_id, self_room_type_id=room_type_id, is_active=True)
            .all()
        )
        for m in maps:
            w = float(getattr(m, "weight", None) or default_w)
            weight_by_comp[m.comp_id] = max(0.1, min(1.0, w))
            if m.comp_room_type_raw:
                preferred_names.add(str(m.comp_room_type_raw).strip())

    def _distance_weight(comp_id: str, base_w: float) -> Optional[float]:
        prop = props.get(comp_id)
        dist = float(prop.distance_km) if prop and prop.distance_km is not None else None
        if dist is None:
            return base_w
        if dist > radius:
            if mode == "hard":
                return None
            return max(0.1, base_w * 0.35)
        proximity = 1.0 - dist / max(radius, 0.1) * 0.4
        return max(0.1, min(1.0, base_w * proximity))

    q = db.query(CompetitorRateSnapshot).filter_by(hotel_id=hotel_id, stay_date=stay, channel=channel)
    rows = q.all()

    def _dedupe(rows_in: list) -> list:
        """同一竞品×房型只留最新一条，避免旧 snapshot_id 与新 id 重复计入中位。"""
        best: dict[tuple[str, str], Any] = {}
        for r in rows_in:
            if not r.observed_price:
                continue
            if r.comp_id not in props:
                continue
            rt_eq = str(r.room_type_eq or "").strip()
            key = (str(r.comp_id), rt_eq)
            prev = best.get(key)
            if prev is None:
                best[key] = r
                continue
            prev_ts = prev.captured_at or datetime.min
            cur_ts = r.captured_at or datetime.min
            if cur_ts >= prev_ts or int(r.id or 0) >= int(prev.id or 0):
                best[key] = r
        return list(best.values())

    rows = _dedupe(rows)
    weighted: list[tuple[float, float]] = []
    for r in rows:
        if preferred_names and str(r.room_type_eq or "").strip() not in preferred_names:
            continue
        base_w = weight_by_comp.get(r.comp_id, default_w)
        w = _distance_weight(r.comp_id, base_w)
        if w is None:
            continue
        weighted.append((float(r.observed_price), w))
    if not weighted and (not preferred_names):
        rows2 = _dedupe(db.query(CompetitorRateSnapshot).filter_by(hotel_id=hotel_id, stay_date=stay).all())
        for r in rows2:
            w = _distance_weight(r.comp_id, default_w)
            if w is None:
                continue
            weighted.append((float(r.observed_price), w))
    if not weighted:
        return None
    expanded: list[float] = []
    for price, w in weighted:
        n = max(1, int(round(w * 10)))
        expanded.extend([price] * n)
    return _pricing_common._money(statistics.median(expanded))


def build_explain_json(
    *,
    base_rate: float,
    suggested_price: float,
    suggested_base: float,
    prev_price: float,
    pace_ratio: float,
    tightness: float,
    rem_rooms: int,
    event: dict,
    comp_median: Optional[float],
    comp_on: bool,
    params: dict,
    n_est: float,
    is_event_day: bool,
) -> dict:
    """§5.7 加法分解：Σ因子增量 ≡ 建议价 − 基准价 B（形状权重归一）。"""
    target = suggested_price - base_rate
    shapes: list[dict] = []
    if event.get("uplift", 0) > 0 and event.get("event_name"):
        hist = min(float(event["uplift"]), float(params.get("ev_cap", 100)) / 100.0)
        heat = event.get("heat_score")
        src = event.get("source") or t("活动日历 · 实际系数 +{pct}%（受活动因子硬上限约束）", pct=f"{hist * 100:.1f}")
        shapes.append(
            {
                "key": "event",
                "name": t("{name}（活动日历 event_calendar）", name=event["event_name"]),
                "source": src,
                "shape": max(10, int(base_rate * hist)),
                "color": "#7c3aed",
                "heat_score": heat,
                "distance_km": event.get("distance_km"),
                "venue_lat": event.get("venue_lat"),
                "venue_lng": event.get("venue_lng"),
                "venue_address": event.get("venue_address"),
                "event_id": event.get("event_id"),
                "spatial": True,
            }
        )
    pace_delta_shape = (
        28 if pace_ratio >= params.get("pace_up", 1.1) else -22 if pace_ratio <= params.get("pace_down", 0.9) else 8
    )
    pace_pct = f"{('+' if pace_ratio >= 1 else '')}{int((pace_ratio - 1) * 100)}"
    shapes.append(
        {
            "key": "pace",
            "name": t("预订进度 {pct}%", pct=pace_pct),
            "source": t(
                "预订进度快照 · 阈值 >{up} 涨 / <{down} 降",
                up=f"{params.get('pace_up', 1.1):.2f}",
                down=f"{params.get('pace_down', 0.9):.2f}",
            ),
            "shape": abs(pace_delta_shape),
            "sign": 1 if pace_delta_shape >= 0 else -1,
            "color": "#1d4ed8",
        }
    )
    inv_shape = 14 if rem_rooms <= 8 else 6 if rem_rooms <= 16 else -10
    inv_name = t("库存偏紧（剩 {n} 间）", n=rem_rooms) if rem_rooms <= 8 else t("库存偏松（剩 {n} 间）", n=rem_rooms)
    shapes.append(
        {
            "key": "inv",
            "name": inv_name,
            "source": t("库存快照 (inventory_snapshot) · 紧张度 (Tightness) {n}", n=f"{tightness / 100:.2f}"),
            "shape": abs(inv_shape),
            "sign": 1 if inv_shape >= 0 else -1,
            "color": "#d97706",
        }
    )
    if comp_on and comp_median is not None:
        gap = suggested_price - comp_median
        shapes.append(
            {
                "key": "comp",
                "name": t("竞品中位 ¥{price} vs 本店", price=f"{comp_median:.0f}"),
                "source": t(
                    "竞品房价快照 · 加权中位（距离半径 {km}km · 模式 {mode} · w{w}）",
                    km=params.get("comp_radius_km", 5),
                    mode=params.get("comp_distance_mode", "soft"),
                    w=f"{params.get('comp_w', 1):.2f}",
                ),
                "shape": 16 if abs(gap) > 5 else 6,
                "sign": 1 if gap >= 0 else -1,
                "color": "#16a34a",
                "spatial": True,
                "comp_radius_km": params.get("comp_radius_km", 5),
            }
        )
    elif comp_on:
        shapes.append(
            {
                "key": "comp_na",
                "name": t("竞品对比已开启 · 当日无可用竞品价"),
                "source": t(
                    "开关已开，但该入住日缺少可比竞品客付价快照（需录价且日期匹配；有房型映射时须 like-for-like），故竞品因子贡献为 0"
                ),
                "shape": 0,
                "sign": 1,
                "color": "#9ca3af",
                "muted": True,
                "spatial": True,
                "comp_radius_km": params.get("comp_radius_km", 5),
            }
        )
    else:
        shapes.append(
            {
                "key": "na",
                "name": t("竞品对比未开启"),
                "source": t("仅基于本店房态 / 库存 / 销售信号，竞品因子不参与"),
                "shape": 0,
                "sign": 1,
                "color": "#9ca3af",
                "muted": True,
            }
        )
    raw_sum = sum(s["shape"] for s in shapes) or 1
    factors = []
    acc = 0
    for i, s in enumerate(shapes):
        sign = s.get("sign", 1)
        if i == len(shapes) - 1:
            delta = target - acc
        else:
            delta = int(round(s["shape"] / raw_sum * target))
            if sign < 0 and target > 0 and (s["shape"] > 0):
                pass
            acc += delta
        factors.append(
            {
                "key": s["key"],
                "name": s["name"],
                "source": s["source"],
                "delta": delta,
                "color": s["color"],
                "muted": bool(s.get("muted")),
            }
        )
    factor_sum = sum(f["delta"] for f in factors)
    if factors and factor_sum != target:
        factors[-1]["delta"] += int(round(target - factor_sum))
    prev = prev_price or base_rate
    chg_pct = round((suggested_price - prev) / max(prev, 1) * 100, 1)
    cost_floor = _pricing_common._money(base_rate * float(params.get("cost_pct", 55)) / 100)
    n_floor = float(params.get("n_floor", 240))
    cap_pct = float(params.get("cap_pct", 50))
    fair = None
    if comp_on and comp_median is not None:
        up_band = float(params.get("fair_ev" if is_event_day else "fair_day", 30))
        lo = _pricing_common._money(comp_median * (1 - 0.25))
        hi = _pricing_common._money(comp_median * (1 + up_band / 100))
        dev = round((suggested_price - comp_median) / max(comp_median, 1) * 100, 1)
        if is_event_day:
            status = "event"
            title = t("✓ 事件驱动 · 公平价带内") if lo <= suggested_price <= hi else t("ⓘ 事件驱动 · 偏离偏大")
            msg = t("演唱会/节假日下，建议价偏离竞品中位 {dev}%（阈值 ≤ +{band}%）", dev=dev, band=up_band)
        elif suggested_price > hi:
            status, title = ("over", t("⚠ 软提示 · 超出公平价带（不阻断采纳）"))
            msg = t(
                "建议价高出竞品中位 {dev}%（公平价带 ¥{lo}–¥{hi}）。请确认本店定位/质量是否支撑。",
                dev=dev,
                lo=f"{lo:.0f}",
                hi=f"{hi:.0f}",
            )
        elif suggested_price < lo:
            status, title = ("under", t("ⓘ 低于公平价带"))
            msg = t("建议价低于竞品中位 {dev}%，疑似清库存或低价丢利。", dev=abs(dev))
        else:
            status, title = ("ok", t("✓ 落在公平价带内"))
            msg = t("建议价偏离竞品中位 {dev}%（公平价带 ¥{lo}–¥{hi}）", dev=dev, lo=f"{lo:.0f}", hi=f"{hi:.0f}")
        fair = {
            "comp_median": comp_median,
            "lo": lo,
            "hi": hi,
            "dev_pct": dev,
            "status": status,
            "title": title,
            "msg": msg,
            "is_event": is_event_day,
        }
    elif comp_on:
        fair = {
            "status": "na",
            "title": t("公平价带暂不可用"),
            "msg": t(
                "竞品对比已开启，但该日无可用竞品中位价，公平价带不计算。请为建议入住日补录竞品客付价后重新生成建议。"
            ),
            "is_event": False,
        }
    else:
        fair = {
            "status": "na",
            "title": t("公平价带不可用"),
            "msg": t("竞品对比未开启：公平价带不计算。"),
            "is_event": False,
        }
    agg = params.get("agg", "balanced")
    return {
        "base_rate": base_rate,
        "base_source": "room_type_base_rate.base_rate",
        "suggested_price": suggested_price,
        "suggested_base": suggested_base,
        "factor_sum": sum(f["delta"] for f in factors),
        "factors": factors,
        "compliance": {
            "daily_uplift_pct": chg_pct,
            "cap_pct": cap_pct,
            "cap_ok": chg_pct <= cap_pct,
            "cost_floor": cost_floor,
            "cost_floor_ok": suggested_price >= cost_floor,
            "n_est": n_est,
            "n_floor": n_floor,
            "n_floor_ok": n_est >= n_floor,
        },
        "fair_price_band": fair,
        "params": {
            "agg": agg,
            "agg_label": t(AGG_LABEL.get(agg, agg)),
            "agg_mult": DEFAULT_PARAMS["agg_mult"].get(agg, 1.0),
            "target_occ": params.get("target_occ"),
            "round": params.get("round"),
            "ev_cap": params.get("ev_cap"),
            "ev_weak": params.get("ev_weak"),
            "ev_mid": params.get("ev_mid"),
            "ev_strong": params.get("ev_strong"),
            "ev_boom": params.get("ev_boom"),
            "ev_heat_map": params.get("ev_heat_map"),
            "ev_heat_demo": params.get("ev_heat_demo"),
            "hol_short": params.get("hol_short"),
            "hol_mid": params.get("hol_mid"),
            "hol_long": params.get("hol_long"),
            "ev_km": params.get("ev_km"),
            "cap_pct": params.get("cap_pct"),
            "cost_pct": params.get("cost_pct"),
            "n_floor": params.get("n_floor"),
            "fair_ev": params.get("fair_ev"),
            "fair_day": params.get("fair_day"),
            "comp_w": params.get("comp_w"),
            "pace_up": params.get("pace_up"),
            "pace_down": params.get("pace_down"),
            "comp_compare_enabled": comp_on,
            "event_heat": event.get("heat_score"),
            "event_uplift_pct": round(float(event.get("uplift") or 0) * 100, 1),
            "event_model": event.get("model"),
        },
        "note": t(
            "基准价 B → 叠加事件热度/假期长度 + Pace/库存/竞品 → 过合规闸门（日环比≤+50%、活动因子硬上限+100% 独立）；Σ因子增量 ≡ 建议价 − B。读快照不实时重算。"
        ),
    }


def compute_tightness(
    db: Session,
    hotel_id: int,
    stay: date,
    room_type_id: Optional[int],
    pace_ratio: float,
    event_uplift: float,
    occ_forecast: float,
) -> float:
    rooms = _pricing_booking_pace_service._rooms_count(db, hotel_id)
    booked = _pricing_booking_pace_service._booked_for_date(db, hotel_id, stay, room_type_id)
    rem_pressure = min(1.0, booked / rooms)
    pace_term = min(1.2, max(0.5, pace_ratio)) / 1.2
    event_term = min(1.0, event_uplift / 1.0)
    occ_term = min(1.0, (occ_forecast or 70) / 100)
    return round((0.35 * occ_term + 0.25 * rem_pressure + 0.25 * pace_term + 0.15 * event_term) * 100, 1)


def _horizon_label(days_out: int) -> str:
    if days_out <= 3:
        return t("尾端")
    if days_out <= 14:
        return t("近端")
    if days_out <= 30:
        return t("中期")
    if days_out <= 90:
        return t("中远")
    return t("远期")


def _is_comp_reason(text: str) -> bool:
    s = str(text or "")
    low = s.lower()
    return "竞品" in s or "competitor" in low or "comp median" in low


def optimize_price(
    *,
    current_guest: float,
    current_base: float,
    n_floor: float,
    bar_lower: float,
    bar_upper: float,
    pace_ratio: float,
    tightness: float,
    gap: Optional[float],
    event_uplift: float,
    channel: str,
    cfg: dict,
    occ_forecast: float,
) -> dict:
    """§5.6 五步仿真，输出建议价。"""
    candidates = []
    for i in range(-8, 9):
        factor = 1.0 + i * 0.02
        if factor < 0.85 or factor > 1.15:
            continue
        b = _pricing_common._money(current_base * factor)
        if event_uplift > 0 and pace_ratio >= 0.95:
            b = _pricing_common._money(b * (1 + event_uplift * 0.6))
        b = max(bar_lower, min(bar_upper, b))
        if current_base > 0 and (b - current_base) / current_base > 0.15:
            b = _pricing_common._money(current_base * 1.15)
        candidates.append(b)
    filtered = []
    for b in candidates:
        n = _pricing_channel_matrix_service._est_n(b, channel, cfg)
        if n >= n_floor:
            filtered.append((b, n))
    if not filtered:
        b = current_base
        return {
            "suggested_base": b,
            "suggested_price": _pricing_channel_matrix_service._guest_price_from_base(b, channel, cfg),
            "est_n": _pricing_channel_matrix_service._est_n(b, channel, cfg),
            "blocked": True,
            "block_reason": t("无候选满足净到手下限"),
        }
    comp_med = None
    if gap is not None:
        comp_med = current_guest - gap
    scored = []
    for b, n in filtered:
        pg = _pricing_channel_matrix_service._guest_price_from_base(b, channel, cfg)
        elasticity = 1.0
        if pace_ratio > 1.1:
            elasticity = 1.05 if pg >= current_guest else 0.98
        elif pace_ratio < 0.9:
            elasticity = 0.95 if pg > current_guest else 1.08
        occ_adj = min(0.98, max(0.4, occ_forecast / 100 * elasticity))
        score = occ_adj * n
        if comp_med is not None:
            if pg <= comp_med + 5:
                score *= 1.05
            elif pg > comp_med * 1.12:
                score *= 0.9
        scored.append((score, b, n, pg))
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0]
    b_star, n_star, pg_star = (best[1], best[2], best[3])
    if tightness > 70 and pg_star < current_guest * 0.92:
        b_star = current_base
        n_star = _pricing_channel_matrix_service._est_n(b_star, channel, cfg)
        pg_star = _pricing_channel_matrix_service._guest_price_from_base(b_star, channel, cfg)
    reasons = []
    if pace_ratio >= 1.1:
        reasons.append(t("预订进度 {pct}%", pct=f"+{int((pace_ratio - 1) * 100)}"))
    elif pace_ratio <= 0.9:
        reasons.append(t("预订进度 {pct}%", pct=f"{int((pace_ratio - 1) * 100)}"))
    else:
        reasons.append(t("预订进度 平稳 {ratio}", ratio=f"{pace_ratio:.2f}"))
    reasons.append(t("紧张度 (Tightness) {n}", n=f"{tightness:.0f}"))
    if event_uplift > 0:
        reasons.append(t("活动 +{pct}%", pct=int(event_uplift * 100)))
    elif gap is not None:
        if gap > 5:
            reasons.append(t("竞品中位偏低 · 价差 (Gap) +¥{n}", n=f"{abs(gap):.0f}"))
        elif gap < -5:
            reasons.append(t("低于竞品中位 · 价差 (Gap) ¥{n}", n=f"{gap:.0f}"))
        else:
            reasons.append(t("贴近竞品中位 ¥{n}", n=f"{current_guest - gap:.0f}") if gap is not None else t("竞品对齐"))
    else:
        reasons.append(t("{horizon}库存优化", horizon=_horizon_label(0)))
    conf = t("高") if abs(pg_star - current_guest) / max(current_guest, 1) < 0.08 and pace_ratio else t("中")
    if abs(pg_star - current_guest) < 1:
        conf = t("高")
    revpar_delta = _pricing_common._money((pg_star - current_guest) * (occ_forecast / 100))
    return {
        "suggested_base": b_star,
        "suggested_price": pg_star,
        "est_n": n_star,
        "est_occ_pct": _pricing_common._money(occ_forecast),
        "est_revpar_delta": revpar_delta,
        "top_reasons": reasons[:3],
        "confidence": conf,
        "blocked": False,
        "comp_median": comp_med,
    }


def _dense_direct_coverage_ok(db: Session, hotel_id: int, days: int, room_type_ids: list[int]) -> bool:
    """日历 dense 直订建议是否已覆盖「房型 × 天」；齐全则可跳过重算。"""
    if not room_type_ids or days <= 0:
        return True
    today = date.today()
    end = today + timedelta(days=days)
    rows = (
        db.query(PricingRecommendation.room_type_id, PricingRecommendation.stay_date)
        .filter(
            PricingRecommendation.hotel_id == hotel_id,
            PricingRecommendation.channel == "direct",
            PricingRecommendation.stay_date >= today,
            PricingRecommendation.stay_date < end,
            PricingRecommendation.status.in_(["pending", "accepted", "blocked"]),
            PricingRecommendation.room_type_id.in_(room_type_ids),
        )
        .all()
    )
    have = {
        (int(rid), sd.isoformat() if hasattr(sd, "isoformat") else str(sd))
        for rid, sd in rows
        if rid is not None and sd is not None
    }
    needed = {(int(rid), (today + timedelta(days=i)).isoformat()) for rid in room_type_ids for i in range(days)}
    return needed.issubset(have)


def _comp_rates_stale_vs_recos(db: Session, hotel_id: int, *, days: int = 30) -> bool:
    """竞品录价晚于上次建议生成水印 → 建议价/中位已过期，必须 force 重算。"""
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    if not cfg.get("comp_compare_enabled"):
        return False
    today = date.today()
    end = today + timedelta(days=max(int(days), 1))
    max_rate = (
        db.query(func.max(CompetitorRateSnapshot.captured_at))
        .filter(
            CompetitorRateSnapshot.hotel_id == hotel_id,
            CompetitorRateSnapshot.stay_date >= today,
            CompetitorRateSnapshot.stay_date < end,
        )
        .scalar()
    )
    if not max_rate:
        return False
    gen_raw = (cfg.get("params") or {}).get("reco_gen_at")
    if not gen_raw:
        return True
    try:
        gen_at = datetime.fromisoformat(str(gen_raw).replace("Z", ""))
    except ValueError:
        return True
    if isinstance(max_rate, str):
        try:
            max_rate = datetime.fromisoformat(max_rate)
        except ValueError:
            return True
    return max_rate > gen_at


def _mark_reco_gen_at(db: Session, hotel_id: int) -> None:
    """记录本机时间水印，与 competitor_rate_snapshot.captured_at 同一时钟，避免 UTC/本地混比。"""
    row = _pricing_config_service.get_or_create_config(db, hotel_id)
    params = {**DEFAULT_PARAMS, **_pricing_common._json_loads(getattr(row, "params_json", None), {})}
    params["reco_gen_at"] = datetime.now().isoformat(timespec="seconds")
    row.params_json = _pricing_common._json_dumps(params)


def ensure_recommendations_fresh(
    db: Session, hotel_id: int, *, days: int = 30, channels: Optional[list[str]] = None
) -> dict:
    """若竞品价新于建议快照，则 force 重算；否则走稠密覆盖补齐。"""
    force = _comp_rates_stale_vs_recos(db, hotel_id, days=days)
    return generate_recommendations(db, hotel_id, days=days, force=force, dense=True, channels=channels or ["direct"])


def generate_recommendations(
    db: Session,
    hotel_id: int,
    *,
    days: int = 7,
    channels: Optional[list[str]] = None,
    force: bool = False,
    dense: bool = False,
) -> dict:
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    params = cfg.get("params") or DEFAULT_PARAMS
    comp_on = bool(cfg.get("comp_compare_enabled"))
    agg = params.get("agg", "balanced")
    agg_mult = float(DEFAULT_PARAMS["agg_mult"].get(agg, 1.0))
    round_step = float(params.get("round") or 10)
    today = date.today()
    channels = channels or ["direct", "ota_ctrip"]
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    rt_ids = [int(rt.id) for rt in room_types]
    if not force and dense and (set(channels) == {"direct"}) and _dense_direct_coverage_ok(db, hotel_id, days, rt_ids):
        return {
            "created": 0,
            "skipped": len(rt_ids) * days,
            "coverage_ok": True,
            "note": "dense coverage complete · skipped regenerate",
        }
    forecast = build_revenue_forecast(db, hotel_id)
    occ_by_day = {d["biz_date"]: d.get("occ_forecast", 75) for d in forecast.get("daily", [])}
    total_rooms = _pricing_booking_pace_service._rooms_count(db, hotel_id)
    created = 0
    skipped = 0
    for rt in room_types:
        bar = db.query(RoomTypeBaseRate).filter_by(hotel_id=hotel_id, room_type_id=rt.id).first()
        base = float(bar.base_rate) if bar else float(rt.base_price or 380)
        n_floor = float(bar.n_floor) if bar else float(params.get("n_floor") or base * 0.6)
        bar_lower = float(bar.bar_lower) if bar else base * 0.7
        bar_upper = float(bar.bar_upper) if bar else base * 2.0
        for offset in range(0, days):
            stay = today + timedelta(days=offset)
            pace = _pricing_booking_pace_service.get_pace(db, hotel_id, stay, rt.id)
            event = _pricing_event_service.get_event_uplift(db, hotel_id, stay, params)
            raw_uplift = float(event.get("uplift") or 0)
            cap = float(params.get("ev_cap", 100)) / 100.0
            event = {**event, "uplift": min(raw_uplift, cap)}
            occ = float(occ_by_day.get(stay.isoformat(), 72))
            tightness = compute_tightness(db, hotel_id, stay, rt.id, pace["pace_ratio"], event.get("uplift", 0), occ)
            booked = _pricing_booking_pace_service._booked_for_date(db, hotel_id, stay, rt.id)
            rem = max(0, total_rooms - booked)
            for ch in channels:
                rate = _pricing_config_service._resolve_rate(
                    db, hotel_id, ch, cfg=cfg, room_type_id=rt.id, on_date=stay
                )
                current_base = _pricing_common._money(base * (1.02 if stay.weekday() >= 4 else 1.0))
                current_guest = _pricing_channel_matrix_service._guest_price_from_base(
                    current_base, ch, cfg, rate=rate, round_step=round_step
                )
                comp_med = None
                gap = None
                if comp_on:
                    comp_med = _comp_median_guest(
                        db, hotel_id, stay, rt.id, "ota_ctrip", float(params.get("comp_w") or 1), params=params
                    )
                    gap = _pricing_common._money(current_guest - comp_med) if comp_med else None
                opt = optimize_price(
                    current_guest=current_guest,
                    current_base=current_base,
                    n_floor=n_floor,
                    bar_lower=bar_lower,
                    bar_upper=bar_upper,
                    pace_ratio=pace["pace_ratio"],
                    tightness=tightness,
                    gap=gap,
                    event_uplift=float(event.get("uplift") or 0),
                    channel=ch,
                    cfg=cfg,
                    occ_forecast=occ,
                )
                raw_net = float(opt["suggested_base"])
                delta = raw_net - base
                sug_base = _pricing_channel_matrix_service._round_to(base + delta * agg_mult, round_step)
                sug_base = max(bar_lower, min(bar_upper, sug_base))
                step = float(params.get("step_pct", 15)) / 100.0
                if current_base > 0 and abs(sug_base - current_base) / current_base > step:
                    sug_base = _pricing_channel_matrix_service._round_to(
                        current_base * (1 + step if sug_base > current_base else 1 - step), round_step
                    )
                sug_guest = _pricing_channel_matrix_service._guest_price_from_base(
                    sug_base, ch, cfg, rate=rate, round_step=round_step
                )
                est_n = _pricing_channel_matrix_service._est_n(sug_base, ch, cfg)
                opt["suggested_price"] = sug_guest
                opt["suggested_base"] = sug_base
                opt["est_n"] = est_n
                opt["channel_matrix"] = _pricing_channel_matrix_service.build_channel_matrix(
                    sug_base, cfg, db=db, hotel_id=hotel_id, room_type_id=rt.id, on_date=stay, round_step=round_step
                )
                if not force and (not dense) and (abs(sug_guest - current_guest) < 3):
                    skipped += 1
                    continue
                existing = (
                    db.query(PricingRecommendation)
                    .filter_by(hotel_id=hotel_id, room_type_id=rt.id, channel=ch, stay_date=stay, status="pending")
                    .first()
                )
                if existing and (not force):
                    skipped += 1
                    continue
                if existing and force:
                    existing.status = "expired"
                prev_price = current_guest
                if offset > 0:
                    prev_stay = stay - timedelta(days=1)
                    prev_reco = (
                        db.query(PricingRecommendation)
                        .filter_by(hotel_id=hotel_id, room_type_id=rt.id, channel=ch, stay_date=prev_stay)
                        .order_by(PricingRecommendation.id.desc())
                        .first()
                    )
                    if prev_reco:
                        prev_price = float(prev_reco.suggested_price or prev_reco.current_price or current_guest)
                is_event = bool(event.get("uplift", 0) > 0)
                explain = build_explain_json(
                    base_rate=base,
                    suggested_price=sug_guest,
                    suggested_base=sug_base,
                    prev_price=prev_price,
                    pace_ratio=pace["pace_ratio"],
                    tightness=tightness,
                    rem_rooms=rem,
                    event=event,
                    comp_median=comp_med,
                    comp_on=comp_on,
                    params=params,
                    n_est=est_n,
                    is_event_day=is_event,
                )
                explain["calc_mode"] = "net_parity"
                explain["channel_matrix"] = opt.get("channel_matrix") or []
                explain["params"]["commission"] = {
                    k: round(float(v) * 10000) / 100 for k, v in (cfg.get("commission") or {}).items()
                }
                explain["params"]["commission_note"] = "readonly: system config / finance params / OTA commission"
                features = {
                    "pace": pace,
                    "tightness": tightness,
                    "gap": gap,
                    "comp_median": comp_med,
                    "event": event,
                    "horizon": _horizon_label(offset),
                    "price_basis": "net_parity",
                    "calc_mode": "net_parity",
                    "commission_rate": rate,
                    "channel_matrix": opt.get("channel_matrix") or [],
                    "rem_rooms": rem,
                    "occ_pct": occ,
                    "signals": {"comp": comp_med, "occ": occ, "inv": rem, "pace": round(pace["pace_ratio"] * 100, 1)},
                }
                snap = hashlib.md5(_pricing_common._json_dumps(features).encode()).hexdigest()[:16]
                reasons = list(opt.get("top_reasons") or [])
                if event.get("event_name"):
                    reasons = [
                        t("活动：{name}+{pct}%", name=event["event_name"], pct=int(event["uplift"] * 100))
                    ] + reasons
                    reasons = reasons[:3]
                if not comp_on:
                    reasons = [r for r in reasons if not _is_comp_reason(r)]
                    if len(reasons) < 3:
                        reasons.append(t("未含竞品信号（内部基准模式）"))
                    reasons = reasons[:3]
                status = "blocked" if opt.get("blocked") else "pending"
                reco = PricingRecommendation(
                    reco_id=_pricing_common._sid("reco_"),
                    hotel_id=hotel_id,
                    room_type_id=rt.id,
                    channel=ch,
                    stay_date=stay,
                    current_price=current_guest,
                    suggested_price=sug_guest,
                    suggested_base=sug_base,
                    est_n=est_n,
                    est_occ_pct=opt.get("est_occ_pct"),
                    est_revpar_delta=_pricing_common._money((sug_guest - current_guest) * (occ / 100)),
                    confidence=opt.get("confidence", t("中")),
                    top_reasons=_pricing_common._json_dumps(reasons),
                    features_snapshot=_pricing_common._json_dumps(features),
                    explain_json=_pricing_common._json_dumps(explain),
                    execution_mode=cfg["execution_mode"],
                    status=status,
                    snapshot_hash=snap,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(days=2),
                )
                db.add(reco)
                created += 1
    from pricing.pricing_assistant.rule_hooks import run_extra_recommendation_hooks

    created += run_extra_recommendation_hooks(
        db,
        hotel_id,
        {
            "days": days,
            "channels": channels,
            "force": force,
            "dense": dense,
            "params": params,
            "cfg": cfg,
        },
    )
    db.flush()
    if created or force:
        _mark_reco_gen_at(db, hotel_id)
    return {"created": created, "skipped": skipped, "execution_mode": cfg["execution_mode"]}


def _reco_to_dict(db: Session, r: PricingRecommendation) -> dict:
    rt = db.get(RoomType, r.room_type_id)
    feat = _pricing_common._json_loads(r.features_snapshot, {})
    explain = _pricing_common._json_loads(getattr(r, "explain_json", None), None)
    cfg = _pricing_config_service.get_config_dict(db, r.hotel_id)
    live_comp = None
    if cfg.get("comp_compare_enabled") and r.stay_date and r.room_type_id:
        try:
            params = cfg.get("params") or DEFAULT_PARAMS
            live_comp = _comp_median_guest(
                db,
                r.hotel_id,
                r.stay_date,
                r.room_type_id,
                "ota_ctrip",
                float(params.get("comp_w") or 1),
                params=params,
            )
        except Exception:
            live_comp = None
    if live_comp is not None:
        feat = {**feat, "comp_median": live_comp}
        sig = feat.get("signals")
        if isinstance(sig, dict):
            feat["signals"] = {**sig, "comp": live_comp}
    if not explain and feat:
        bar = db.query(RoomTypeBaseRate).filter_by(hotel_id=r.hotel_id, room_type_id=r.room_type_id).first()
        base = float(bar.base_rate) if bar else float(rt.base_price if rt else 380)
        explain = build_explain_json(
            base_rate=base,
            suggested_price=float(r.suggested_price or 0),
            suggested_base=float(r.suggested_base or 0),
            prev_price=float(r.current_price or base),
            pace_ratio=float((feat.get("pace") or {}).get("pace_ratio") or 1),
            tightness=float(feat.get("tightness") or 50),
            rem_rooms=int(feat.get("rem_rooms") or 10),
            event=feat.get("event") or {},
            comp_median=feat.get("comp_median"),
            comp_on=bool(cfg.get("comp_compare_enabled")),
            params=cfg.get("params") or DEFAULT_PARAMS,
            n_est=float(r.est_n or 0),
            is_event_day=bool((feat.get("event") or {}).get("uplift")),
        )
    elif explain is not None and live_comp is not None:
        factors = list(explain.get("factors") or [])
        patched = False
        new_factors = []
        for f in factors:
            if isinstance(f, dict) and f.get("key") == "comp":
                new_factors.append({**f, "name": t("竞品中位 ¥{price} vs 本店", price=f"{live_comp:.0f}")})
                patched = True
            else:
                new_factors.append(f)
        band = explain.get("fair_price_band")
        if isinstance(band, dict):
            band = {**band, "comp_median": live_comp}
        explain = {
            **explain,
            "factors": new_factors if patched else factors,
            "fair_price_band": band if isinstance(band, dict) else explain.get("fair_price_band"),
        }
    matrix = (explain or {}).get("channel_matrix") or feat.get("channel_matrix") or []
    try:
        archive = _pricing_config_service._commission_channels_for_ui(db)
        order = [str(x.get("code") or "") for x in archive if x.get("code")]
        allow = set(order)
    except Exception:
        order = list(DISPLAY_CHANNELS)
        allow = set(order)
    if matrix and allow:
        by_ch = {m.get("channel"): m for m in matrix if m.get("channel") in allow}
        matrix = [by_ch[c] for c in order if c in by_ch]
    if (not matrix or len(matrix) < len(order)) and r.suggested_base is not None:
        try:
            matrix = _pricing_channel_matrix_service.build_channel_matrix(
                float(r.suggested_base or 0),
                cfg,
                db=db,
                hotel_id=r.hotel_id,
                room_type_id=r.room_type_id,
                on_date=r.stay_date,
            )
        except Exception:
            pass
    if explain is not None and matrix:
        explain = {**explain, "channel_matrix": matrix}
    return {
        "id": r.id,
        "reco_id": r.reco_id,
        "hotel_id": r.hotel_id,
        "room_type_id": r.room_type_id,
        "room_type_name": rt.name if rt else "",
        "channel": r.channel,
        "stay_date": r.stay_date.isoformat() if r.stay_date else None,
        "current_price": float(r.current_price or 0),
        "suggested_price": float(r.suggested_price or 0),
        "suggested_base": float(r.suggested_base or 0),
        "est_n": float(r.est_n or 0),
        "calc_mode": "net_parity",
        "channel_matrix": matrix,
        "est_occ_pct": float(r.est_occ_pct or 0),
        "est_revpar_delta": float(r.est_revpar_delta or 0),
        "confidence": r.confidence,
        "top_reasons": _pricing_common._json_loads(r.top_reasons, []),
        "features_snapshot": feat,
        "explain_json": explain,
        "execution_mode": r.execution_mode,
        "status": r.status,
        "delta": _pricing_common._money(float(r.suggested_price or 0) - float(r.current_price or 0)),
        "delta_pct": round(
            (float(r.suggested_price or 0) - float(r.current_price or 0)) / max(float(r.current_price or 1), 1) * 100, 1
        ),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _reco_to_calendar_dict(r: PricingRecommendation, room_type_name: str = "") -> dict:
    """日历格子轻量序列化：不重建 channel_matrix / explain（打开推导时再拉详情）。"""
    cur = float(r.current_price or 0)
    sug = float(r.suggested_price or 0)
    return {
        "id": r.id,
        "reco_id": r.reco_id,
        "hotel_id": r.hotel_id,
        "room_type_id": r.room_type_id,
        "room_type_name": room_type_name,
        "channel": r.channel,
        "stay_date": r.stay_date.isoformat() if r.stay_date else None,
        "current_price": cur,
        "suggested_price": sug,
        "suggested_base": float(r.suggested_base or 0),
        "est_n": float(r.est_n or 0),
        "calc_mode": "net_parity",
        "channel_matrix": [],
        "est_occ_pct": float(r.est_occ_pct or 0),
        "est_revpar_delta": float(r.est_revpar_delta or 0),
        "confidence": r.confidence,
        "top_reasons": _pricing_common._json_loads(r.top_reasons, []),
        "features_snapshot": {},
        "explain_json": None,
        "execution_mode": r.execution_mode,
        "status": r.status,
        "delta": _pricing_common._money(sug - cur),
        "delta_pct": round((sug - cur) / max(cur, 1) * 100, 1),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "detail_lazy": True,
    }


def list_recommendations(
    db: Session,
    hotel_id: int,
    *,
    status: Optional[str] = None,
    room_type_id: Optional[int] = None,
    channel: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict]:
    q = db.query(PricingRecommendation).filter_by(hotel_id=hotel_id)
    if status:
        q = q.filter(PricingRecommendation.status == status)
    if room_type_id:
        q = q.filter(PricingRecommendation.room_type_id == room_type_id)
    if channel:
        q = q.filter(PricingRecommendation.channel == channel)
    if date_from:
        q = q.filter(PricingRecommendation.stay_date >= date_from)
    if date_to:
        q = q.filter(PricingRecommendation.stay_date <= date_to)
    rows = q.order_by(PricingRecommendation.stay_date, PricingRecommendation.room_type_id).all()
    if not rows or _comp_rates_stale_vs_recos(db, hotel_id, days=14):
        generate_recommendations(db, hotel_id, days=14, force=True, dense=True)
        db.commit()
        rows = q.order_by(PricingRecommendation.stay_date, PricingRecommendation.room_type_id).all()
    return [_reco_to_dict(db, r) for r in rows]


def get_recommendation(db: Session, reco_key: str) -> dict:
    r = db.query(PricingRecommendation).filter_by(reco_id=reco_key).first()
    if not r and reco_key.isdigit():
        r = db.get(PricingRecommendation, int(reco_key))
    if not r:
        raise NotFoundError("recommendation not found")
    out = _reco_to_dict(db, r)
    decisions = db.query(PricingDecision).filter_by(reco_id=r.reco_id).order_by(PricingDecision.id.desc()).all()
    out["decisions"] = [
        {
            "decision_id": d.decision_id,
            "decision": d.decision,
            "decided_by": d.decided_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "before_price": float(d.before_price or 0),
            "after_price": float(d.after_price or 0),
            "reason_note": d.reason_note,
            "audit_id": d.audit_id,
        }
        for d in decisions
    ]
    effects = db.query(PricingEffect).filter_by(reco_id=r.reco_id).all()
    out["effects"] = [
        {
            "effect_id": e.effect_id,
            "metric": e.metric,
            "baseline_value": float(e.baseline_value or 0),
            "actual_value": float(e.actual_value or 0),
            "delta_pct": float(e.delta_pct or 0),
        }
        for e in effects
    ]
    return out


def decide_recommendation(
    db: Session,
    reco_key: str,
    *,
    action: str,
    staff_no: str = "",
    staff_no2: str = "",
    note: str = "",
    audit_id: Optional[str] = None,
) -> dict:
    r = db.query(PricingRecommendation).filter_by(reco_id=reco_key).first()
    if not r and str(reco_key).isdigit():
        r = db.get(PricingRecommendation, int(reco_key))
    if not r:
        raise NotFoundError("recommendation not found")
    cfg = _pricing_config_service.get_config_dict(db, r.hotel_id)
    if action not in ("accept", "reject", "ignore"):
        raise InvalidStateError("action must be accept/reject/ignore")
    if action == "accept":
        if r.status == "blocked":
            raise InvalidStateError("该建议被护栏拦截，无法采纳")
        if r.status not in ("pending",):
            raise InvalidStateError(f"当前状态 {r.status} 不可采纳")
        staff = (staff_no or "").strip()
        staff2 = (staff_no2 or "").strip()
        if len(staff) < 4:
            raise InvalidStateError("采纳须工号 ≥4 位二次确认")
        if len(staff2) < 4:
            raise InvalidStateError("双签须值班经理工号 ≥4 位")
        if staff == staff2:
            raise InvalidStateError("双签工号不可相同")
        cur = float(r.current_price or 0)
        sug = float(r.suggested_price or 0)
        if cur > 0 and (cur - sug) / cur > 0.2:
            raise InvalidStateError("单次降幅超过 20%，已熔断，须人工特批流程")
    decision_map = {"accept": "accept", "reject": "reject", "ignore": "ignore"}
    did = _pricing_common._sid("dec_")
    audit = audit_id or _pricing_common._sid("aud_")
    before = float(r.current_price or 0)
    after = float(r.suggested_price or 0) if action == "accept" else before
    staff_note = (note or "").strip()
    if action == "accept" and staff_no2:
        staff_note = f"{staff_note} | 双签:{staff_no.strip()}/{staff_no2.strip()}".strip(" |")
    drow = PricingDecision(
        decision_id=did,
        reco_id=r.reco_id,
        hotel_id=r.hotel_id,
        decision=decision_map[action],
        decided_by=(staff_no or "").strip()[:32] or None,
        decided_at=datetime.now(),
        before_price=before,
        after_price=after,
        reason_note=staff_note[:255] if staff_note else None,
        audit_id=audit,
    )
    db.add(drow)
    if action == "accept":
        r.status = "accepted"
        for metric, base_v, act_v in (
            ("n", float(r.est_n or 0) * 0.95, float(r.est_n or 0)),
            ("occ", float(r.est_occ_pct or 70), float(r.est_occ_pct or 70)),
            ("revpar", float(r.current_price or 0), float(r.suggested_price or 0)),
        ):
            db.add(
                PricingEffect(
                    effect_id=_pricing_common._sid("eff_"),
                    decision_id=did,
                    reco_id=r.reco_id,
                    hotel_id=r.hotel_id,
                    stay_date=r.stay_date,
                    metric=metric,
                    baseline_value=base_v,
                    actual_value=act_v,
                    delta_pct=round((act_v - base_v) / max(abs(base_v), 1) * 100, 1) if base_v else 0,
                )
            )
    elif action == "reject":
        r.status = "rejected"
    else:
        r.status = "ignored"
    db.commit()
    return {
        "ok": True,
        "decision_id": did,
        "audit_id": audit,
        "status": r.status,
        "recommendation": _reco_to_dict(db, r),
        "wrote_pms": False,
        "wrote_ota": False,
        "note": "仅落审计三联单；不推 OTA、不自动跟价",
    }


def batch_decide(
    db: Session, hotel_id: int, *, reco_ids: list[str], action: str, staff_no: str, staff_no2: str = "", note: str = ""
) -> dict:
    if len(reco_ids) > 7:
        raise InvalidStateError("批量最多 7 条（≤7 天）")
    if action == "accept" and len((staff_no2 or "").strip()) < 4:
        raise InvalidStateError("批量采纳须双签工号 ≥4 位")
    audit = _pricing_common._sid("aud_")
    results = []
    for rid in reco_ids:
        try:
            results.append(
                decide_recommendation(
                    db, rid, action=action, staff_no=staff_no, staff_no2=staff_no2, note=note, audit_id=audit
                )
            )
        except HTTPException as e:
            results.append({"ok": False, "reco_id": rid, "error": e.detail})
    return {"audit_id": audit, "count": len(results), "results": results}
