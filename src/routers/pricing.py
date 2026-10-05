# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)
from models import PriceSuggestion, RoomType

router = APIRouter(tags=["pricing"])


@router.get("/pricing")
def list_pricing(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import list_price_suggestions

    return ok(list_price_suggestions(db, hotel_id))


@router.post("/pricing/{pid}/decide")
def decide_pricing(pid: int, payload: dict, db: Session = Depends(get_db)):
    from application.pricing import decide_price_suggestion

    return ok(decide_price_suggestion(db, pid, action=payload.get("action")))


# ---------------- 价格助手（3 页 + 顶部竞品面板 · 合规建议引擎） ----------------
@router.get("/pricing-assistant/config")
def pa_config(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import get_config_dict

    return ok(get_config_dict(db, hotel_id))


@router.put("/pricing-assistant/config")
def pa_config_put(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import update_config

    return ok(update_config(db, hotel_id, payload or {}))


@router.get("/pricing-assistant/amap/status")
@router.get("/pricing-assistant/map/status")
def pa_amap_status(db: Session = Depends(get_db)):
    """地图能力探测（密钥来自系统配置·地图配置，环境变量兜底）。"""
    from extensions.map.facade import map_status

    return ok(map_status(db))


@router.post("/pricing-assistant/amap/geocode")
@router.post("/pricing-assistant/map/geocode")
def pa_amap_geocode(payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """手动输入地址 → 经纬度（天地图/高德/）。"""
    from application.pricing import update_config
    from extensions.map.facade import enrich_hotel_default_location, geocode_address

    payload = payload or {}
    hint = enrich_hotel_default_location(db, hotel_id)
    address = str(payload.get("address") or "").strip() or str(hint.get("address") or "").strip()
    city = str(payload.get("city") or hint.get("city") or "").strip() or None
    if payload.get("hint_only"):
        return ok({"hotel_hint": hint, "address": hint.get("address")})
    if not address:
        raise HTTPException(400, "请输入本店地址")
    try:
        loc = geocode_address(address, city=city, db=db)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    if payload.get("save", True):
        update_config(
            db,
            hotel_id,
            {
                "params": {
                    "self_location": {
                        "address": loc.get("address"),
                        "lng": loc.get("lng"),
                        "lat": loc.get("lat"),
                        "city": loc.get("city"),
                        "source": loc.get("source"),
                    }
                },
                "staff_no": str(payload.get("staff_no") or "map"),
            },
        )
    return ok({**loc, "hotel_hint": hint})


@router.post("/pricing-assistant/amap/nearby")
@router.post("/pricing-assistant/map/nearby")
def pa_amap_nearby(payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """以本店为圆心检索周边酒店（天地图/高德/）。"""
    from application.pricing import get_config_dict
    from extensions.map.facade import nearby_hotels

    payload = payload or {}
    cfg = get_config_dict(db, hotel_id)
    loc = cfg.get("self_location") or {}
    lng = payload.get("lng", loc.get("lng"))
    lat = payload.get("lat", loc.get("lat"))
    if lng is None or lat is None:
        raise HTTPException(400, "请先设置本店位置（输入地址并解析）")
    radius_km = float(payload.get("radius_km") or cfg.get("comp_radius_km") or 3)
    if radius_km not in (3.0, 5.0):
        radius_km = 3.0 if radius_km < 4 else 5.0
    try:
        data = nearby_hotels(float(lng), float(lat), radius_m=int(radius_km * 1000), db=db)
    except Exception as e:
        raise HTTPException(502, f"周边检索失败：{e}") from e
    data["radius_km"] = radius_km
    return ok(data)


@router.get("/pricing-assistant/overview")
def pa_overview(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import build_overview

    return ok(build_overview(db, hotel_id))


@router.get("/pricing-assistant/alerts")
def pa_alerts(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import list_alerts

    return ok(list_alerts(db, hotel_id))


@router.get("/pricing-assistant/recommendations")
def pa_recommendations(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = None,
    room_type_id: Optional[int] = None,
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from application.pricing import list_recommendations

    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None
    return ok(
        list_recommendations(
            db,
            hotel_id,
            status=status,
            room_type_id=room_type_id,
            channel=channel,
            date_from=df,
            date_to=dt,
        )
    )


@router.post("/pricing-assistant/recommendations/generate")
def pa_generate(
    payload: dict = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.pricing import generate_recommendations_tx

    payload = payload or {}
    result = generate_recommendations_tx(
        db,
        hotel_id,
        days=int(payload.get("days") or 14),
        channels=payload.get("channels"),
        force=bool(payload.get("force", True)),
        dense=bool(payload.get("dense", False)),
    )
    return ok(result)


@router.post("/pricing-assistant/recommendations/batch-decide")
def pa_batch_decide(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import batch_decide

    return ok(
        batch_decide(
            db,
            hotel_id,
            reco_ids=list(payload.get("reco_ids") or []),
            action=payload.get("action") or "accept",
            staff_no=str(payload.get("staff_no") or ""),
            staff_no2=str(payload.get("staff_no2") or ""),
            note=str(payload.get("note") or ""),
        )
    )


@router.get("/pricing-assistant/recommendations/{reco_id}")
def pa_reco_detail(reco_id: str, db: Session = Depends(get_db)):
    from application.pricing import get_recommendation

    return ok(get_recommendation(db, reco_id))


@router.post("/pricing-assistant/recommendations/{reco_id}/decide")
def pa_decide(reco_id: str, payload: dict, db: Session = Depends(get_db)):
    from application.pricing import decide_recommendation

    return ok(
        decide_recommendation(
            db,
            reco_id,
            action=payload.get("action") or "",
            staff_no=str(payload.get("staff_no") or ""),
            staff_no2=str(payload.get("staff_no2") or ""),
            note=str(payload.get("note") or ""),
        )
    )


@router.get("/pricing-assistant/calendar")
def pa_calendar(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(30, ge=14, le=90),
    db: Session = Depends(get_db),
):
    from application.pricing import build_calendar

    return ok(build_calendar(db, hotel_id, days=days))


@router.get("/pricing-assistant/trend")
def pa_trend(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import build_trend

    return ok(build_trend(db, hotel_id))


@router.post("/pricing-assistant/simulate")
def pa_simulate(payload: dict = None, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import run_simulate

    payload = payload or {}
    return ok(run_simulate(db, hotel_id, scenario=payload.get("scenario") or "balanced"))


@router.get("/pricing-assistant/competitor-sets")
def pa_comp_sets(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import list_competitor_sets

    return ok(list_competitor_sets(db, hotel_id))


@router.post("/pricing-assistant/competitors")
def pa_add_comp(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import add_competitor

    return ok(add_competitor(db, hotel_id, payload or {}))


@router.post("/pricing-assistant/competitors/{comp_id}/deactivate")
def pa_deactivate_comp(comp_id: str, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import deactivate_competitor

    return ok(deactivate_competitor(db, hotel_id, comp_id))


@router.get("/pricing-assistant/room-maps")
def pa_room_maps(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import list_room_maps

    return ok(list_room_maps(db, hotel_id))


@router.post("/pricing-assistant/room-maps")
def pa_add_room_map(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import add_room_map

    return ok(add_room_map(db, hotel_id, payload or {}))


@router.get("/pricing-assistant/competitor-rates")
def pa_list_comp_rates(
    stay_date: str,
    channel: str | None = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.pricing import list_competitor_rates

    return ok(list_competitor_rates(db, hotel_id, stay_date, channel=channel))


@router.post("/pricing-assistant/competitor-rates")
def pa_comp_rate(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import upsert_competitor_rate

    return ok(upsert_competitor_rate(db, hotel_id, payload or {}))


@router.post("/pricing-assistant/competitor-rates/import")
def pa_comp_rate_import(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import import_competitor_rates_csv

    return ok(import_competitor_rates_csv(db, hotel_id, str(payload.get("text") or "")))


@router.get("/pricing-assistant/data-sources")
def pa_data_sources(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import list_data_sources

    return ok(list_data_sources(db, hotel_id))


@router.get("/pricing-assistant/events")
def pa_list_events(
    hotel_id: int = Depends(hotel_scope),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
):
    from application.pricing import list_events

    return ok(list_events(db, hotel_id, include_inactive=include_inactive))


@router.post("/pricing-assistant/events")
def pa_create_event(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import create_event

    return ok(create_event(db, hotel_id, payload or {}))


@router.put("/pricing-assistant/events/{event_id}")
def pa_update_event(
    event_id: str,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.pricing import update_event

    return ok(update_event(db, hotel_id, event_id, payload or {}))


@router.post("/pricing-assistant/events/{event_id}/deactivate")
def pa_deactivate_event(event_id: str, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import deactivate_event

    return ok(deactivate_event(db, hotel_id, event_id))


@router.delete("/pricing-assistant/events/{event_id}")
def pa_delete_event(event_id: str, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.pricing import delete_event

    return ok(delete_event(db, hotel_id, event_id))


@router.get("/pricing-assistant/map-candidates")
def pa_map_candidates(hotel_id: int = Depends(hotel_scope)):
    from bootstrap.ensure_pricing_assistant import mock_map_candidates

    return ok(mock_map_candidates(hotel_id))


@router.post("/pricing-assistant/recommendations/{reco_id}/narrate")
def pa_reco_narrate(reco_id: str, db: Session = Depends(get_db)):
    """用系统配置的 LLM（本地/云端可切换）生成店长可读的价格推导说明（基于 explain_json 快照）。"""
    from application.pricing import narrate_explain_with_llm

    return ok(narrate_explain_with_llm(db, reco_id))


# ---------------- 客户 360 ----------------


@router.get("/pricing/{pid}")
def pricing_detail(pid: int, db: Session = Depends(get_db)):
    """价格推导详情：单条建议 + 推导因子 + 护栏原理 + 影响预测。"""
    p = db.get(PriceSuggestion, pid)
    if not p:
        raise HTTPException(404, "suggestion not found")
    rt = db.get(RoomType, p.room_type_id) if p.room_type_id else None
    base = float(rt.base_price) if rt and rt.base_price else 0
    out = row_to_dict(p)
    out["room_type_name"] = rt.name if rt else ""
    out["base_price"] = base
    out["delta_pct"] = round((float(p.suggested_price) - base) / base * 100, 1) if base else 0
    out["guardrail_reasons"] = (
        ("低于最低保护价" if float(p.suggested_price) < base * 0.85 else None),
        ("高于 OTA 最低展示价 1.15 倍" if float(p.suggested_price) > base * 1.25 else None),
        ("同渠道当日已发过同类调整" if False else None),
    )
    out["guardrail_reasons"] = [x for x in out["guardrail_reasons"] if x]
    return ok(out)


# ---------------- 营销活动 ----------------
