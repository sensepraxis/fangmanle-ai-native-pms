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

from infra.i18n import t
from pricing.pricing_assistant import _common as _pricing_common


def _intensity_heat_preset(intensity: Optional[str], params: dict) -> float:
    """选档＝把 heat 预设到对应档位。"""
    mapping = {
        "弱": float(params.get("ev_weak", 15)),
        "中": float(params.get("ev_mid", 30)),
        "强": float(params.get("ev_strong", 50)),
        "爆": float(params.get("ev_boom", 80)),
    }
    return mapping.get(intensity or "中", float(params.get("ev_mid", 30)))


def _infer_heat_score(ev: EventCalendar, params: dict) -> float:
    """热度分：单事件字段覆盖 > Demo 主事件覆盖 > 档位锚点 > 名称启发。"""
    raw = getattr(ev, "heat_score", None)
    if raw is not None:
        return max(0.0, min(100.0, float(raw)))
    name = str(ev.event_name or "")
    if "周杰伦" in name:
        return max(0.0, min(100.0, float(params.get("ev_heat_demo", 95))))
    return _intensity_heat_preset(ev.intensity, params)


def _holiday_length_pct(start_d: date, end_d: date, params: dict) -> float:
    days = max(1, (end_d - start_d).days + 1)
    if days <= 1:
        return float(params.get("hol_short", 15))
    if days <= 3:
        return float(params.get("hol_mid", 30))
    return float(params.get("hol_long", 45))


def _holiday_day_shape(stay: date, start_d: date, end_d: date) -> float:
    """假日内逐日形状：首尾高、中间略低。"""
    span = max(1, (end_d - start_d).days)
    pos = max(0.0, min(1.0, (stay - start_d).days / span))
    return 0.85 + 0.15 * abs(2 * pos - 1)


def get_event_uplift(db: Session, hotel_id: int, stay: date, params: Optional[dict] = None) -> dict:
    """同晚只取最强事件。
    活动/演唱会：系数 = heat × ev_heat_map（%/分），受活动因子硬上限约束。
    节假日：假期长度基准 × 假日形状，同样受硬上限约束。
    """
    params = {**DEFAULT_PARAMS, **(params or {})}
    cap = min(float(params.get("ev_cap", 100)), 100.0) / 100.0
    ev_km = float(params.get("ev_km", 5))
    heat_map = float(params.get("ev_heat_map", 1.0))
    events = (
        db.query(EventCalendar).filter((EventCalendar.hotel_id == hotel_id) | EventCalendar.hotel_id.is_(None)).all()
    )
    best = None
    best_u = 0.0
    for ev in events:
        if getattr(ev, "is_active", True) is False:
            continue
        start_d = ev.start_at.date() if isinstance(ev.start_at, datetime) else ev.start_at
        end_d = ev.end_at.date() if isinstance(ev.end_at, datetime) else ev.end_at
        if not start_d - timedelta(days=7) <= stay <= end_d + timedelta(days=1):
            continue
        dist = float(ev.distance_km) if ev.distance_km is not None else None
        if ev.event_type != "holiday":
            if dist is None:
                continue
            if dist > ev_km:
                continue
        heat = _infer_heat_score(ev, params)
        if ev.event_type == "holiday":
            base_pct = _holiday_length_pct(start_d, end_d, params)
            shape = _holiday_day_shape(stay, start_d, end_d) if start_d <= stay <= end_d else 0.9
            raw_pct = base_pct * shape
            model = "holiday_length"
            source = t(
                "节假日系数 · 假期长度基准 +{base}% × 形状 {shape}（受活动因子硬上限 +{cap}% 约束）",
                base=f"{base_pct:.0f}",
                shape=f"{shape:.2f}",
                cap=f"{cap * 100:.0f}",
            )
        else:
            raw_pct = heat * heat_map
            model = "heat"
            source = t(
                "活动日历 · 热度 {heat} · 距本店 {dist}km → 系数 +{coef}%（档位锚点不封顶，受硬上限 +{cap}% 约束）",
                heat=f"{heat:.0f}",
                dist=f"{dist:.1f}",
                coef=f"{raw_pct:.1f}",
                cap=f"{cap * 100:.0f}",
            )
        row_cap = float(ev.price_uplift_max) if ev.price_uplift_max is not None else cap
        row_cap = min(max(row_cap, 0.0), cap)
        u = min(raw_pct / 100.0, row_cap, cap)
        if u > best_u:
            best_u = u
            best = {
                "event_id": ev.event_id,
                "event_name": ev.event_name,
                "event_type": ev.event_type,
                "intensity": ev.intensity,
                "heat_score": heat,
                "heat_map": heat_map,
                "raw_uplift_pct": round(raw_pct, 1),
                "distance_km": dist,
                "venue_lat": float(ev.venue_lat) if getattr(ev, "venue_lat", None) is not None else None,
                "venue_lng": float(ev.venue_lng) if getattr(ev, "venue_lng", None) is not None else None,
                "venue_address": getattr(ev, "venue_address", None),
                "uplift": u,
                "model": model,
                "source": source,
            }
    return best or {"uplift": 0.0}


def _parse_event_dt(value: Any, *, end: bool = False) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date) and (not isinstance(value, datetime)):
        t = datetime.max.time().replace(microsecond=0) if end else datetime.min.time()
        return datetime.combine(value, t)
    s = str(value or "").strip()
    if not s:
        raise InvalidStateError("请填写起止日期")
    if "T" in s or " " in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0])
    d = date.fromisoformat(s[:10])
    t = datetime.max.time().replace(microsecond=0) if end else datetime.min.time()
    return datetime.combine(d, t)


def _event_to_dict(ev: EventCalendar, *, ev_km: float = 5.0) -> dict:
    start_d = ev.start_at.date() if isinstance(ev.start_at, datetime) else ev.start_at
    end_d = ev.end_at.date() if isinstance(ev.end_at, datetime) else ev.end_at
    dist = float(ev.distance_km) if ev.distance_km is not None else None
    active = bool(getattr(ev, "is_active", True))
    needs_location = ev.event_type != "holiday" and dist is None
    in_radius = True
    if ev.event_type != "holiday":
        in_radius = dist is not None and dist <= ev_km
    return {
        "event_id": ev.event_id,
        "hotel_id": ev.hotel_id,
        "event_type": ev.event_type or "other",
        "event_name": ev.event_name,
        "start_date": start_d.isoformat() if start_d else None,
        "end_date": end_d.isoformat() if end_d else None,
        "distance_km": dist,
        "intensity": ev.intensity or "中",
        "heat_score": float(ev.heat_score) if getattr(ev, "heat_score", None) is not None else None,
        "price_uplift_max": float(ev.price_uplift_max) if ev.price_uplift_max is not None else 1.0,
        "source": ev.source or "manual",
        "source_ref": ev.source_ref,
        "venue_address": getattr(ev, "venue_address", None),
        "venue_lat": float(ev.venue_lat) if getattr(ev, "venue_lat", None) is not None else None,
        "venue_lng": float(ev.venue_lng) if getattr(ev, "venue_lng", None) is not None else None,
        "note": getattr(ev, "note", None),
        "is_active": active,
        "needs_location": needs_location,
        "affects_pricing": active and in_radius and (not needs_location),
        "in_radius": in_radius,
        "ev_km": ev_km,
    }


def list_events(db: Session, hotel_id: int, *, include_inactive: bool = True) -> list[dict]:
    cfg = db.query(PricingAssistantConfig).filter_by(hotel_id=hotel_id).first()
    params = {**DEFAULT_PARAMS, **_pricing_common._json_loads(getattr(cfg, "params_json", None) if cfg else None, {})}
    ev_km = float(params.get("ev_km", 5))
    q = db.query(EventCalendar).filter((EventCalendar.hotel_id == hotel_id) | EventCalendar.hotel_id.is_(None))
    rows = q.order_by(EventCalendar.start_at.asc()).all()
    out = []
    for ev in rows:
        if not include_inactive and getattr(ev, "is_active", True) is False:
            continue
        out.append(_event_to_dict(ev, ev_km=ev_km))
    return out


def _self_location(db: Session, hotel_id: int) -> dict:
    cfg = db.query(PricingAssistantConfig).filter_by(hotel_id=hotel_id).first()
    params = {**DEFAULT_PARAMS, **_pricing_common._json_loads(getattr(cfg, "params_json", None) if cfg else None, {})}
    return params.get("self_location") or {}


def _resolve_event_geo(
    db: Session, hotel_id: int, payload: dict, *, etype: str, existing: Optional[EventCalendar] = None
) -> dict:
    """解析活动场馆坐标并相对本店算距。非节假日无坐标/距离时保持 None（不默认 0）。"""
    from extensions.map.facade import geocode_address
    from infra.geo import haversine_km

    venue = str(
        payload.get("venue_address") if "venue_address" in payload else getattr(existing, "venue_address", None) or ""
    ).strip()
    lat = payload.get("venue_lat") if "venue_lat" in payload else getattr(existing, "venue_lat", None)
    lng = payload.get("venue_lng") if "venue_lng" in payload else getattr(existing, "venue_lng", None)
    if lat is not None and lat != "":
        lat = float(lat)
    else:
        lat = None
    if lng is not None and lng != "":
        lng = float(lng)
    else:
        lng = None
    dist_raw = payload.get("distance_km") if "distance_km" in payload else getattr(existing, "distance_km", None)
    distance_km = None if dist_raw is None or dist_raw == "" else float(dist_raw)
    if etype == "holiday":
        return {
            "venue_address": venue or None,
            "venue_lat": lat,
            "venue_lng": lng,
            "distance_km": distance_km,
            "geo_note": None,
        }
    self_loc = _self_location(db, hotel_id)
    geo_note = None
    if venue and (lat is None or lng is None):
        try:
            loc = geocode_address(venue, city=self_loc.get("city"), db=db)
            lng = float(loc["lng"])
            lat = float(loc["lat"])
            if not venue:
                venue = str(loc.get("address") or venue)
            geo_note = f"已用地图解析场馆（{loc.get('source') or 'map'}）"
        except Exception as e:
            geo_note = f"场馆定位失败：{e}"
    auto_dist = payload.get("auto_distance", True)
    if (
        auto_dist
        and lat is not None
        and (lng is not None)
        and (self_loc.get("lat") is not None)
        and (self_loc.get("lng") is not None)
    ):
        distance_km = haversine_km(float(self_loc["lng"]), float(self_loc["lat"]), float(lng), float(lat))
        geo_note = (geo_note or "") + (f"；距本店 {distance_km}km" if geo_note else f"距本店 {distance_km}km")
    elif distance_km is None and (lat is None or lng is None):
        if not self_loc.get("lat"):
            geo_note = (geo_note or "未定位") + "；请先在竞品圈选中锚定本店位置"
        else:
            geo_note = geo_note or "缺少场馆地址，无法自动算距（暂不计入定价）"
    return {
        "venue_address": venue or None,
        "venue_lat": lat,
        "venue_lng": lng,
        "distance_km": distance_km,
        "geo_note": geo_note,
    }


def create_event(db: Session, hotel_id: int, payload: dict) -> dict:
    name = str(payload.get("event_name") or "").strip()
    if not name:
        raise InvalidStateError("请填写活动名称")
    etype = str(payload.get("event_type") or "other").strip()
    if etype not in EVENT_TYPES:
        raise InvalidStateError(f"活动类型无效，可选：{'/'.join(EVENT_TYPES)}")
    start_at = _parse_event_dt(payload.get("start_date") or payload.get("start_at"), end=False)
    end_at = _parse_event_dt(payload.get("end_date") or payload.get("end_at"), end=True)
    if end_at.date() < start_at.date():
        raise InvalidStateError("结束日不能早于开始日")
    intensity = str(payload.get("intensity") or "中").strip()
    if intensity not in INTENSITY_HEAT:
        intensity = "中"
    heat = payload.get("heat_score")
    if heat is None or heat == "":
        heat_score = INTENSITY_HEAT[intensity]
    else:
        heat_score = max(0.0, min(100.0, float(heat)))
    geo = _resolve_event_geo(db, hotel_id, payload, etype=etype)
    uplift = payload.get("price_uplift_max")
    price_uplift_max = 1.0 if uplift is None or uplift == "" else float(uplift)
    is_active = payload.get("is_active")
    if is_active is None:
        is_active = True
    eid = _pricing_common._sid("ev_")
    db.add(
        EventCalendar(
            event_id=eid,
            hotel_id=hotel_id,
            event_type=etype,
            event_name=name,
            start_at=start_at,
            end_at=end_at,
            distance_km=geo["distance_km"],
            intensity=intensity,
            heat_score=heat_score,
            price_uplift_max=price_uplift_max,
            source=str(payload.get("source") or "manual"),
            source_ref=str(payload.get("source_ref") or "manager"),
            venue_address=geo["venue_address"],
            venue_lat=geo["venue_lat"],
            venue_lng=geo["venue_lng"],
            note=str(payload.get("note") or "").strip() or None,
            is_active=bool(is_active),
        )
    )
    db.commit()
    out = next(e for e in list_events(db, hotel_id) if e["event_id"] == eid)
    if geo.get("geo_note"):
        out["geo_note"] = geo["geo_note"]
    return out


def update_event(db: Session, hotel_id: int, event_id: str, payload: dict) -> dict:
    ev = (
        db.query(EventCalendar)
        .filter(
            EventCalendar.event_id == event_id, (EventCalendar.hotel_id == hotel_id) | EventCalendar.hotel_id.is_(None)
        )
        .first()
    )
    if not ev:
        raise NotFoundError("活动不存在")
    if "event_name" in payload:
        name = str(payload.get("event_name") or "").strip()
        if not name:
            raise InvalidStateError("活动名称不能为空")
        ev.event_name = name
    if "event_type" in payload:
        etype = str(payload.get("event_type") or "").strip()
        if etype not in EVENT_TYPES:
            raise InvalidStateError(f"活动类型无效，可选：{'/'.join(EVENT_TYPES)}")
        ev.event_type = etype
    if "start_date" in payload or "start_at" in payload:
        ev.start_at = _parse_event_dt(payload.get("start_date") or payload.get("start_at"), end=False)
    if "end_date" in payload or "end_at" in payload:
        ev.end_at = _parse_event_dt(payload.get("end_date") or payload.get("end_at"), end=True)
    if ev.end_at and ev.start_at and (ev.end_at.date() < ev.start_at.date()):
        raise InvalidStateError("结束日不能早于开始日")
    if "intensity" in payload:
        intensity = str(payload.get("intensity") or "中").strip()
        if intensity not in INTENSITY_HEAT:
            intensity = "中"
        ev.intensity = intensity
        if "heat_score" not in payload:
            ev.heat_score = INTENSITY_HEAT[intensity]
    if "heat_score" in payload:
        heat = payload.get("heat_score")
        if heat is None or heat == "":
            ev.heat_score = INTENSITY_HEAT.get(ev.intensity or "中", 40.0)
        else:
            ev.heat_score = max(0.0, min(100.0, float(heat)))
    if "note" in payload:
        ev.note = str(payload.get("note") or "").strip() or None
    if "price_uplift_max" in payload:
        uplift = payload.get("price_uplift_max")
        ev.price_uplift_max = 1.0 if uplift is None or uplift == "" else float(uplift)
    if "is_active" in payload:
        ev.is_active = bool(payload.get("is_active"))
    geo_keys = {"venue_address", "venue_lat", "venue_lng", "distance_km", "auto_distance"}
    if geo_keys & set(payload.keys()) or payload.get("regeocode"):
        geo = _resolve_event_geo(db, hotel_id, payload, etype=ev.event_type or "other", existing=ev)
        ev.venue_address = geo["venue_address"]
        ev.venue_lat = geo["venue_lat"]
        ev.venue_lng = geo["venue_lng"]
        ev.distance_km = geo["distance_km"]
    elif "distance_km" in payload:
        dist = payload.get("distance_km")
        ev.distance_km = None if dist is None or dist == "" else float(dist)
    db.commit()
    out = next(e for e in list_events(db, hotel_id) if e["event_id"] == event_id)
    return out


def deactivate_event(db: Session, hotel_id: int, event_id: str) -> dict:
    """软下线：不再纳入定价影响，仍可在列表（含停用）中看到。"""
    return update_event(db, hotel_id, event_id, {"is_active": False})


def delete_event(db: Session, hotel_id: int, event_id: str) -> dict:
    """硬删除：仅允许手工来源；内置节假日请用停用。"""
    ev = (
        db.query(EventCalendar)
        .filter(
            EventCalendar.event_id == event_id, (EventCalendar.hotel_id == hotel_id) | EventCalendar.hotel_id.is_(None)
        )
        .first()
    )
    if not ev:
        raise NotFoundError("活动不存在")
    if (ev.source or "") == "builtin":
        raise InvalidStateError("内置节假日不可删除，请改用「不纳入定价」")
    db.delete(ev)
    db.commit()
    return {"ok": True, "event_id": event_id}
