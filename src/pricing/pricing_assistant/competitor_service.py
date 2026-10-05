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
from pricing.pricing_assistant import recommendation_service as _pricing_recommendation_service


def list_competitor_sets(db: Session, hotel_id: int) -> list[dict]:
    sets = db.query(CompetitorSet).filter_by(hotel_id=hotel_id).all()
    today = date.today()
    primary_rt = db.query(RoomType).filter_by(hotel_id=hotel_id).order_by(RoomType.id.asc()).first()
    primary_name = str(primary_rt.name).strip() if primary_rt and primary_rt.name else ""
    out = []
    for s in sets:
        props = db.query(CompetitorProperty).filter_by(set_id=s.set_id, is_active=True).all()
        prop_rows = []
        for p in props:
            preferred = None
            if primary_name:
                preferred = (
                    db.query(CompetitorRateSnapshot)
                    .filter_by(comp_id=p.comp_id, stay_date=today, room_type_eq=primary_name)
                    .order_by(CompetitorRateSnapshot.captured_at.desc())
                    .first()
                )
            today_snap = (
                preferred
                or db.query(CompetitorRateSnapshot)
                .filter_by(comp_id=p.comp_id, stay_date=today)
                .order_by(CompetitorRateSnapshot.captured_at.desc())
                .first()
            )
            last = (
                db.query(CompetitorRateSnapshot)
                .filter_by(comp_id=p.comp_id)
                .order_by(CompetitorRateSnapshot.captured_at.desc())
                .first()
            )
            snap = today_snap or last
            prop_rows.append(
                {
                    "comp_id": p.comp_id,
                    "comp_name": p.comp_name,
                    "comp_lat": float(p.comp_lat or 0),
                    "comp_lng": float(p.comp_lng or 0),
                    "star_rating": p.star_rating,
                    "review_score": float(p.review_score or 0),
                    "distance_km": float(p.distance_km or 0),
                    "data_source": p.data_source,
                    "ota_public_url": p.ota_public_url,
                    "address": p.address,
                    "latest_price": float(snap.observed_price) if snap and snap.observed_price is not None else None,
                    "latest_room_type_eq": str(snap.room_type_eq or "") if snap else None,
                }
            )
        out.append(
            {
                "set_id": s.set_id,
                "set_name": s.set_name,
                "segment_tag": s.segment_tag,
                "default_radius_km": float(s.default_radius_km or 3),
                "is_active": bool(s.is_active),
                "count": len(prop_rows),
                "properties": prop_rows,
            }
        )
    return out


def add_competitor(db: Session, hotel_id: int, payload: dict) -> dict:
    set_id = payload.get("set_id")
    if not set_id:
        s = db.query(CompetitorSet).filter_by(hotel_id=hotel_id, is_active=True).first()
        if not s:
            set_id = _pricing_common._sid("cs_")
            db.add(
                CompetitorSet(
                    set_id=set_id,
                    hotel_id=hotel_id,
                    set_name=payload.get("set_name") or "默认竞品集",
                    segment_tag="同档",
                    is_active=True,
                )
            )
        else:
            set_id = s.set_id
    n = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).count()
    if n >= 30:
        raise InvalidStateError("竞品上限 30 家，请先剔除")
    cid = _pricing_common._sid("cp_")
    db.add(
        CompetitorProperty(
            comp_id=cid,
            set_id=set_id,
            hotel_id=hotel_id,
            comp_name=payload.get("comp_name") or "未命名竞品",
            comp_lat=payload.get("comp_lat"),
            comp_lng=payload.get("comp_lng"),
            address=payload.get("address"),
            star_rating=payload.get("star_rating"),
            review_score=payload.get("review_score"),
            distance_km=payload.get("distance_km"),
            data_source=payload.get("data_source") or "manual",
            source_ref=payload.get("source_ref") or "manager",
            ota_public_url=payload.get("ota_public_url"),
            is_active=True,
        )
    )
    db.commit()
    return {"comp_id": cid, "set_id": set_id}


def list_room_maps(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(CompetitorRoomMap).filter_by(hotel_id=hotel_id, is_active=True).all()
    props = {p.comp_id: p for p in db.query(CompetitorProperty).filter_by(hotel_id=hotel_id).all()}
    out = []
    for m in rows:
        rt = db.get(RoomType, m.self_room_type_id)
        p = props.get(m.comp_id)
        out.append(
            {
                "map_id": m.map_id,
                "comp_id": m.comp_id,
                "comp_name": p.comp_name if p else m.comp_id,
                "comp_room_type_raw": m.comp_room_type_raw,
                "self_room_type_id": m.self_room_type_id,
                "self_room_type_name": rt.name if rt else "",
                "weight": float(getattr(m, "weight", None) or 1.0),
            }
        )
    return out


def add_room_map(db: Session, hotel_id: int, payload: dict) -> dict:
    mid = _pricing_common._sid("crm_")
    w = float(payload.get("weight") if payload.get("weight") is not None else 1.0)
    w = max(0.1, min(1.0, w))
    db.add(
        CompetitorRoomMap(
            map_id=mid,
            comp_id=payload["comp_id"],
            self_room_type_id=int(payload["self_room_type_id"]),
            hotel_id=hotel_id,
            comp_room_type_raw=payload.get("comp_room_type_raw"),
            weight=w,
            mapped_by=payload.get("mapped_by") or "manager",
            is_active=True,
        )
    )
    db.commit()
    return {"map_id": mid, "weight": w}


def deactivate_competitor(db: Session, hotel_id: int, comp_id: str) -> dict:
    prop = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, comp_id=comp_id).first()
    if not prop:
        raise NotFoundError("competitor not found")
    prop.is_active = False
    db.commit()
    return {"ok": True, "comp_id": comp_id}


def upsert_competitor_rate(db: Session, hotel_id: int, payload: dict) -> dict:
    """P1 手工录入：竞品 OTA 公开客付挂牌价（按竞品×入住日×渠道×房型）。"""
    import re

    stay = date.fromisoformat(payload["stay_date"])
    channel = payload.get("channel") or "ota_ctrip"
    room_eq = str(payload.get("room_type_eq") or "大床房").strip() or "大床房"
    rt_key = re.sub("[^\\w\\u4e00-\\u9fff]+", "_", room_eq)[:40] or "room"
    snap_id = f"crs_{payload['comp_id']}_{stay.isoformat()}_{channel}_{rt_key}"
    row = db.query(CompetitorRateSnapshot).filter_by(snapshot_id=snap_id).first()
    if not row:
        legacy_id = f"crs_{payload['comp_id']}_{stay.isoformat()}_{channel}"
        row = db.query(CompetitorRateSnapshot).filter_by(snapshot_id=legacy_id).first()
        if row and (not row.room_type_eq or row.room_type_eq == room_eq):
            row.snapshot_id = snap_id
        else:
            row = None
    if not row:
        row = CompetitorRateSnapshot(snapshot_id=snap_id, comp_id=payload["comp_id"], hotel_id=hotel_id, stay_date=stay)
        db.add(row)
    row.room_type_eq = room_eq
    row.channel = channel
    row.observed_price = float(payload["observed_price"])
    row.rate_plan_code = payload.get("rate_plan_code") or "BAR"
    row.captured_at = datetime.now()
    prop = db.query(CompetitorProperty).filter_by(comp_id=payload["comp_id"]).first()
    if prop and prop.data_source != "rate_shopping":
        prop.data_source = payload.get("data_source") or "manual"
    db.commit()
    return {"snapshot_id": snap_id, "ok": True}


def list_competitor_rates(db: Session, hotel_id: int, stay_date: str, channel: Optional[str] = None) -> list[dict]:
    """按入住日列出已录竞品公开价，供编辑网格回填。"""
    stay = date.fromisoformat(str(stay_date).strip())
    q = db.query(CompetitorRateSnapshot).filter_by(hotel_id=hotel_id, stay_date=stay)
    if channel:
        q = q.filter_by(channel=str(channel))
    rows = q.order_by(CompetitorRateSnapshot.comp_id, CompetitorRateSnapshot.id).all()
    out = []
    for r in rows:
        out.append(
            {
                "snapshot_id": r.snapshot_id,
                "comp_id": r.comp_id,
                "stay_date": r.stay_date.isoformat() if r.stay_date else None,
                "channel": r.channel,
                "room_type_eq": r.room_type_eq,
                "observed_price": float(r.observed_price) if r.observed_price is not None else None,
                "captured_at": r.captured_at.isoformat() if r.captured_at else None,
            }
        )
    return out


def import_competitor_rates_csv(db: Session, hotel_id: int, text: str) -> dict:
    """P2b：CSV 文本导入。格式: comp_id,stay_date,observed_price,channel,room_type_eq"""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        raise InvalidStateError("empty import")
    start = 1 if "comp_id" in lines[0] else 0
    n = 0
    for ln in lines[start:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 3:
            continue
        payload = {
            "comp_id": parts[0],
            "stay_date": parts[1],
            "observed_price": parts[2],
            "channel": parts[3] if len(parts) > 3 else "ota_ctrip",
            "room_type_eq": parts[4] if len(parts) > 4 else "大床房",
            "data_source": "manual",
        }
        upsert_competitor_rate(db, hotel_id, payload)
        n += 1
    if n:
        _pricing_recommendation_service.generate_recommendations(db, hotel_id, days=14, force=True, dense=True)
        db.commit()
    return {"imported": n, "regenerated": bool(n)}
