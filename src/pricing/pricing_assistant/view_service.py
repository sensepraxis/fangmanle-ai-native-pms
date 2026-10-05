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

from infra.i18n import t
from pricing.pricing_assistant import _common as _pricing_common
from pricing.pricing_assistant import booking_pace_service as _pricing_booking_pace_service
from pricing.pricing_assistant import channel_matrix_service as _pricing_channel_matrix_service
from pricing.pricing_assistant import config_service as _pricing_config_service
from pricing.pricing_assistant import event_service as _pricing_event_service
from pricing.pricing_assistant import recommendation_service as _pricing_recommendation_service


def build_overview(db: Session, hotel_id: int) -> dict:
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    params = cfg.get("params") or DEFAULT_PARAMS
    today = date.today()
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    primary = room_types[0] if room_types else None
    base = float(primary.base_price) if primary else 400.0
    self_guest = _pricing_channel_matrix_service._guest_price_from_base(base, "ota_ctrip", cfg)
    comp_med = (
        _pricing_recommendation_service._comp_median_guest(
            db, hotel_id, today, primary.id if primary else None, params=params
        )
        or self_guest
    )
    pace = _pricing_booking_pace_service.get_pace(db, hotel_id, today, primary.id if primary else None)
    event = _pricing_event_service.get_event_uplift(db, hotel_id, today, params)
    forecast = build_revenue_forecast(db, hotel_id)
    today_row = next((d for d in forecast.get("daily", []) if d.get("is_today")), None)
    occ = float((today_row or {}).get("occ_forecast") or 72)
    tightness = _pricing_recommendation_service.compute_tightness(
        db, hotel_id, today, primary.id if primary else None, pace["pace_ratio"], event.get("uplift", 0), occ
    )
    n_avg = _pricing_channel_matrix_service._est_n(base, "ota_ctrip", cfg)
    snaps = db.query(CompetitorRateSnapshot).filter_by(hotel_id=hotel_id, stay_date=today).all()
    prices = sorted([float(s.observed_price) for s in snaps if s.observed_price] + [self_guest])
    rank = prices.index(self_guest) + 1 if self_guest in prices else max(1, len(prices) // 2)
    trend = []
    for i in range(7):
        d = today - timedelta(days=6 - i)
        self_adr = _pricing_booking_pace_service._self_adr_for_date(db, hotel_id, d)
        cm = (
            _pricing_recommendation_service._comp_median_guest(
                db, hotel_id, d, params=cfg.get("params") or DEFAULT_PARAMS
            )
            if cfg.get("comp_compare_enabled")
            else None
        )
        ota_min = (
            _pricing_booking_pace_service._ota_min_for_date(db, hotel_id, d)
            if cfg.get("comp_compare_enabled")
            else None
        )
        trend.append({"date": d.isoformat(), "self": self_adr, "comp_median": cm, "ota_min": ota_min})
    ranking = []
    props = {p.comp_id: p for p in db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).all()}
    for s in snaps:
        p = props.get(s.comp_id)
        ranking.append(
            {
                "name": p.comp_name if p else s.comp_id,
                "price": float(s.observed_price or 0),
                "star": p.star_rating if p else None,
                "score": float(p.review_score) if p and p.review_score else None,
            }
        )
    ranking.append({"name": "本店", "price": self_guest, "star": None, "score": None, "is_self": True})
    ranking.sort(key=lambda x: x["price"])
    open_alerts = (
        db.query(ParityAlert)
        .filter_by(hotel_id=hotel_id, status="open")
        .order_by(ParityAlert.detected_at.desc())
        .limit(5)
        .all()
    )
    return {
        "kpis": [
            {
                "key": "competitiveness",
                "label": "价格竞争力指数",
                "value": round(self_guest / max(comp_med, 1) * 100, 1),
                "unit": "%",
                "hint": "本店 ADR / 竞品中位 ×100%",
                "delta": round((self_guest / max(comp_med, 1) - 1) * 100, 1),
            },
            {
                "key": "pace",
                "label": "Pace（7 天预订进度）",
                "value": pace["pace_ratio"],
                "unit": "",
                "hint": f"已订 {pace['booked']} / 应有 {pace['expected']}",
                "delta": round((pace["pace_ratio"] - 1) * 100, 1),
            },
            {
                "key": "tightness",
                "label": "Tightness（紧张度）",
                "value": tightness,
                "unit": "",
                "hint": "OCC+库存+Pace+活动",
                "delta": 0,
            },
            {
                "key": "net_n",
                "label": "净到手 N（估算）",
                "value": n_avg,
                "unit": "¥",
                "hint": "按当前基准价与渠道佣金估算",
                "delta": None,
            },
            {
                "key": "rank",
                "label": "当前价位排名",
                "value": rank,
                "unit": f"/ {len(ranking)}",
                "hint": "1 = 最便宜",
                "delta": 0,
            },
        ],
        "trend_7d": trend,
        "ranking_today": ranking,
        "ai_hints": [
            f"竞争力指数 {round(self_guest / max(comp_med, 1) * 100, 1)}%，"
            + ("偏高，平日可观察 Pace" if self_guest > comp_med * 1.05 else "处于合理区间"),
            f"Pace {pace['pace_ratio']}，"
            + ("建议查看近端溢价机会" if pace["pace_ratio"] > 1.1 else "关注低 Pace 日期"),
            f"开放告警 {len(open_alerts)} 条，点此去变价告警排查",
        ],
        "open_alert_count": len(open_alerts),
        "execution_mode": cfg["execution_mode"],
        "price_basis_note": "竞品比价使用同渠道客付挂牌价，不可用本店结算底价 B 比竞品 OTA 价",
    }


def list_alerts(db: Session, hotel_id: int) -> dict:
    rows = db.query(ParityAlert).filter_by(hotel_id=hotel_id).order_by(ParityAlert.detected_at.desc()).limit(50).all()
    out = []
    for a in rows:
        out.append(
            {
                "alert_id": a.alert_id,
                "severity": a.severity,
                "alert_type": a.alert_type,
                "title": a.title,
                "detail": a.detail,
                "suggested_action": a.suggested_action,
                "status": a.status,
                "stay_date": a.stay_date.isoformat() if a.stay_date else None,
                "delta_pct": float(a.delta_pct or 0),
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                "channel_a": a.channel_a,
                "channel_b": a.channel_b,
            }
        )
    order = {"red": 0, "yellow": 1, "blue": 2}
    out.sort(key=lambda x: (0 if x["status"] == "open" else 1, order.get(x["severity"], 9)))
    return {
        "alerts": out,
        "counts": {
            "red": sum(1 for x in out if x["severity"] == "red" and x["status"] == "open"),
            "yellow": sum(1 for x in out if x["severity"] == "yellow" and x["status"] == "open"),
            "blue": sum(1 for x in out if x["severity"] == "blue" and x["status"] == "open"),
            "open": sum(1 for x in out if x["status"] == "open"),
        },
        "compliance_note": "变价告警仅提示；所有处置须经店长在「AI 定价建议」人工采纳，禁止系统自动调价。",
    }


def build_compare(db: Session, hotel_id: int, days: int = 7) -> dict:
    today = date.today()
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    primary = room_types[0] if room_types else None
    props = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).limit(10).all()
    dates = [today + timedelta(days=i) for i in range(days)]
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    base = float(primary.base_price) if primary else 400
    matrix = []
    self_row = {"name": "本店", "is_self": True, "cells": []}
    for d in dates:
        g = _pricing_channel_matrix_service._guest_price_from_base(
            base * (1.02 if d.weekday() >= 4 else 1.0), "ota_ctrip", cfg
        )
        n = _pricing_channel_matrix_service._est_n(
            _pricing_channel_matrix_service._base_from_guest(g, "ota_ctrip", cfg), "ota_ctrip", cfg
        )
        self_row["cells"].append({"date": d.isoformat(), "guest_price": g, "est_n": n})
    matrix.append(self_row)
    for p in props:
        row = {"name": p.comp_name, "comp_id": p.comp_id, "is_self": False, "cells": []}
        for d in dates:
            snap = db.query(CompetitorRateSnapshot).filter_by(comp_id=p.comp_id, stay_date=d).first()
            gp = float(snap.observed_price) if snap and snap.observed_price else None
            est_n = (
                _pricing_channel_matrix_service._est_n(
                    _pricing_channel_matrix_service._base_from_guest(gp, "ota_ctrip", cfg), "ota_ctrip", cfg
                )
                if gp
                else None
            )
            row["cells"].append({"date": d.isoformat(), "guest_price": gp, "est_n": est_n, "n_estimated": True})
        matrix.append(row)
    medians = []
    for i, d in enumerate(dates):
        vals = [r["cells"][i]["guest_price"] for r in matrix if r["cells"][i]["guest_price"]]
        medians.append(_pricing_common._money(statistics.median(vals)) if vals else None)
    self_today = self_row["cells"][0]["guest_price"]
    med0 = medians[0] or self_today
    return {
        "dates": [d.isoformat() for d in dates],
        "matrix": matrix,
        "comp_median": medians,
        "self_vs_median_pct": round((self_today / max(med0, 1) - 1) * 100, 1),
        "ai_read": [
            f"本店相对竞品中位 {('偏高' if self_today > med0 else '偏低')} {abs(round((self_today / max(med0, 1) - 1) * 100, 1))}%",
            "风险：平日段若 Pace 走弱，高位价可能抑制预订",
            "机会：活动/周末日可维持或小幅溢价，不必盲目跟降",
        ],
        "price_basis_note": "矩阵展示同渠道客付挂牌价；净到手 N 对竞品为估算（按本店佣金假设）",
    }


def build_calendar(db: Session, hotel_id: int, days: int = 30) -> dict:
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    "未来 30 天建议价日历：必须返回稠密 date_axis × 全房型格子（对齐原型）。"
    today = date.today()
    span = min(max(int(days), 14), 30)
    date_axis = [(today + timedelta(days=i)).isoformat() for i in range(span)]
    _pricing_recommendation_service.ensure_recommendations_fresh(db, hotel_id, days=span, channels=["direct"])
    db.commit()
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).order_by(RoomType.id).all()
    events = (
        db.query(EventCalendar).filter((EventCalendar.hotel_id == hotel_id) | EventCalendar.hotel_id.is_(None)).all()
    )
    event_marks = []
    for ev in events:
        if getattr(ev, "is_active", True) is False:
            continue
        start_d = ev.start_at.date() if isinstance(ev.start_at, datetime) else ev.start_at
        end_d = ev.end_at.date() if isinstance(ev.end_at, datetime) else ev.end_at
        icon = "🎤"
        name = str(ev.event_name or "")
        if ev.event_type == "holiday" or any(x in name for x in ("中秋", "国庆", "春节", "端午")):
            icon = "🌕" if "中秋" in name else "🇳🇱"
        elif ev.event_type == "concert" or "演唱" in name:
            icon = "🎤"
        elif ev.event_type == "exhibition":
            icon = "🏛"
        elif ev.event_type == "sport":
            icon = "⚽"
        elif ev.event_type == "school":
            icon = "🎓"
        event_marks.append(
            {
                "event_id": ev.event_id,
                "name": ev.event_name,
                "type": ev.event_type,
                "icon": icon,
                "start": start_d.isoformat(),
                "end": end_d.isoformat(),
                "intensity": ev.intensity,
                "distance_km": float(ev.distance_km) if ev.distance_km is not None else None,
                "uplift_max": float(ev.price_uplift_max if ev.price_uplift_max is not None else 1.0),
                "heat_score": float(ev.heat_score) if getattr(ev, "heat_score", None) is not None else None,
                "is_active": True,
            }
        )

    def _icon_on(stay: date) -> str:
        for em in event_marks:
            s = date.fromisoformat(em["start"])
            e = date.fromisoformat(em["end"])
            if s <= stay <= e:
                return em["icon"]
        return ""

    def _short_room(name: str) -> str:
        s = str(name or "").replace("套房", "").replace("房", "").replace("套", "")
        return s[:2] if s else "房"

    rt_name = {int(rt.id): rt.name for rt in room_types}
    recos = (
        db.query(PricingRecommendation)
        .filter(
            PricingRecommendation.hotel_id == hotel_id,
            PricingRecommendation.stay_date >= today,
            PricingRecommendation.stay_date < today + timedelta(days=span),
            PricingRecommendation.status.in_(["pending", "accepted", "blocked"]),
            PricingRecommendation.channel == "direct",
        )
        .order_by(PricingRecommendation.id.desc())
        .all()
    )
    by_key: dict[str, dict] = {}
    for r in recos:
        key = f"{r.room_type_id}|{(r.stay_date.isoformat() if r.stay_date else '')}"
        if key not in by_key:
            by_key[key] = _pricing_recommendation_service._reco_to_calendar_dict(
                r, room_type_name=rt_name.get(int(r.room_type_id), "")
            )
    cells: list[dict] = []
    change_events: list[dict] = []
    holiday_dates: set[str] = set()
    for rt in room_types:
        bar = db.query(RoomTypeBaseRate).filter_by(hotel_id=hotel_id, room_type_id=rt.id).first()
        base = float(bar.base_rate) if bar else float(rt.base_price or 380)
        for i, iso in enumerate(date_axis):
            stay = date.fromisoformat(iso)
            key = f"{rt.id}|{iso}"
            d = by_key.get(key)
            if not d:
                guest = _pricing_channel_matrix_service._guest_price_from_base(base, "direct", cfg)
                guest = _pricing_common._money(guest * (1.02 if stay.weekday() >= 4 else 1.0))
                d = {
                    "reco_id": None,
                    "room_type_id": rt.id,
                    "room_type_name": rt.name,
                    "channel": "direct",
                    "stay_date": iso,
                    "current_price": guest,
                    "suggested_price": guest,
                    "suggested_base": base,
                    "delta": 0,
                    "delta_pct": 0,
                    "status": "pending",
                    "top_reasons": [],
                    "est_n": _pricing_common._money(guest),
                    "est_occ_pct": None,
                    "est_revpar_delta": 0,
                    "confidence": "中",
                    "features_snapshot": {},
                    "explain_json": None,
                    "channel_matrix": [],
                    "calc_mode": "net_parity",
                    "detail_lazy": True,
                }
            delta = float(d.get("delta") or float(d["suggested_price"]) - float(d["current_price"]))
            delta_pct = float(d.get("delta_pct") or 0)
            icon = _icon_on(stay)
            tags: list[str] = []
            if icon == "🎤":
                tags.append("concert")
            if icon in ("🌕", "🇳🇱"):
                tags.append("holiday")
                holiday_dates.add(iso)
            if icon == "🇳🇱":
                tags.append("national")
            if abs(delta) >= 3 or abs(delta_pct) >= 8:
                tags.append("ai")
            if abs(delta_pct) >= 45 or icon == "🇳🇱":
                tags.append("cap")
            cell = {
                **d,
                "room_type_name": d.get("room_type_name") or rt.name,
                "tags": tags,
                "icons": [icon] if icon else ["💡"] if "ai" in tags else [],
                "strength": "red" if abs(delta) >= 25 else "yellow" if abs(delta) >= 3 else "green",
            }
            cells.append(cell)
            if d.get("status") == "pending" and abs(delta) >= 3 and d.get("reco_id"):
                change_events.append(
                    {
                        "reco_id": d["reco_id"],
                        "stay_date": d["stay_date"],
                        "room_type_name": cell["room_type_name"],
                        "room_type_id": d.get("room_type_id") or rt.id,
                        "current_price": d["current_price"],
                        "suggested_price": d["suggested_price"],
                        "delta_pct": d.get("delta_pct") or 0,
                        "reasons": " · ".join(d.get("top_reasons") or []),
                        "explain_json": d.get("explain_json"),
                        "features_snapshot": d.get("features_snapshot"),
                        "channel": d.get("channel"),
                        "est_n": d.get("est_n"),
                        "est_occ_pct": d.get("est_occ_pct"),
                        "est_revpar_delta": d.get("est_revpar_delta"),
                        "confidence": d.get("confidence"),
                        "status": d.get("status"),
                        "suggested_base": d.get("suggested_base"),
                        "top_reasons": d.get("top_reasons"),
                    }
                )
    change_events = sorted(change_events, key=lambda x: abs(float(x.get("delta_pct") or 0)), reverse=True)[:8]
    pending_n = sum(1 for c in cells if c.get("status") == "pending" and abs(float(c.get("delta") or 0)) >= 3)
    net_impact = sum(float(c.get("est_revpar_delta") or 0) for c in cells if c.get("status") == "pending")
    rooms_out = []
    for rt in room_types:
        cnt = sum(1 for c in cells if c.get("room_type_id") == rt.id)
        rooms_out.append({"name": rt.name, "count": cnt, "short": _short_room(rt.name), "room_type_id": rt.id})
    concert_name = next(
        (e["name"] for e in event_marks if e.get("type") == "concert" or "演唱" in str(e.get("name") or "")), None
    )
    holiday_name = next(
        (e["name"] for e in event_marks if e.get("icon") in ("🌕", "🇳🇱") or e.get("type") == "holiday"), None
    )
    cap_ranges = []
    for em in event_marks:
        if em.get("icon") == "🇳🇱" or "国庆" in str(em.get("name") or ""):
            cap_ranges.append(
                {
                    "start": em["start"],
                    "end": em["end"],
                    "label": t(
                        "活动因子硬上限 +{ev}%", ev=int(float((cfg.get("params") or DEFAULT_PARAMS).get("ev_cap", 100)))
                    ),
                }
            )
    params = cfg.get("params") or DEFAULT_PARAMS
    ev_cap = int(float(params.get("ev_cap", 100)))
    cap_pct = int(float(params.get("cap_pct", 50)))
    return {
        "days": span,
        "date_axis": date_axis,
        "cells": cells,
        "events": event_marks,
        "change_events": change_events,
        "cap_ranges": cap_ranges,
        "rooms": rooms_out,
        "commission": cfg.get("commission") or DEFAULT_COMMISSION,
        "commission_channels": cfg.get("commission_channels")
        or _pricing_config_service._commission_channels_for_ui(db),
        "calc_mode": "net_parity",
        "params_snapshot": {"ev_cap": ev_cap, "cap_pct": cap_pct},
        "kpis": {
            "cells": len(cells),
            "cells_hint": t("含 {n} 个节假日日期", n=len(holiday_dates)) if holiday_dates else t("未来 {n} 天", n=span),
            "ai_changes": pending_n,
            "ai_hint": t("待采纳") if pending_n else t("暂无待采纳"),
            "event_count": len(event_marks),
            # event_hint：活动名来自库数据，不翻译；无活动时用 UI 文案
            "event_hint": concert_name or holiday_name or (t("暂无活动") if not event_marks else t("活动日历")),
            "net_impact": _pricing_common._money(net_impact),
            "net_hint": t("预估每间可售房收入影响合计") if net_impact else t("暂无预估影响"),
        },
        "uplift_cap_note": t("活动因子硬上限 +{ev}%（日环比涨幅 +{cap}% 为独立闸门）", ev=ev_cap, cap=cap_pct),
    }


def build_trend(db: Session, hotel_id: int) -> dict:
    today = date.today()
    cfg = _pricing_config_service.get_config_dict(db, hotel_id)
    params = cfg.get("params") or DEFAULT_PARAMS
    comp_on = bool(cfg.get("comp_compare_enabled"))
    series = {"7": [], "14": [], "30": []}
    total_rooms = _pricing_booking_pace_service._rooms_count(db, hotel_id)
    occ_series = []
    for key, n in (("7", 7), ("14", 14), ("30", 30)):
        for i in range(n):
            d = today - timedelta(days=n - 1 - i)
            self_adr = _pricing_booking_pace_service._self_adr_for_date(db, hotel_id, d)
            cm = _pricing_recommendation_service._comp_median_guest(db, hotel_id, d, params=params) if comp_on else None
            ota_min = _pricing_booking_pace_service._ota_min_for_date(db, hotel_id, d) if comp_on else None
            series[key].append({"date": d.isoformat(), "self_adr": self_adr, "comp_median": cm, "ota_min": ota_min})
    for i in range(7):
        d = today - timedelta(days=6 - i)
        booked = _pricing_booking_pace_service._booked_for_date(db, hotel_id, d)
        occ = round(booked / max(total_rooms, 1) * 100, 1)
        rem = max(0, total_rooms - booked)
        occ_series.append({"date": d.isoformat(), "occ": occ, "rem": rem})
    events = []
    if comp_on:
        props = {p.comp_id: p for p in db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, is_active=True).all()}
        for cid, p in list(props.items())[:6]:
            snaps = (
                db.query(CompetitorRateSnapshot)
                .filter_by(comp_id=cid)
                .order_by(CompetitorRateSnapshot.stay_date)
                .limit(40)
                .all()
            )
            for a, b in zip(snaps, snaps[1:]):
                pa, pb = (float(a.observed_price or 0), float(b.observed_price or 0))
                if pa and abs(pb - pa) / pa >= 0.05:
                    events.append(
                        {
                            "date": b.stay_date.isoformat(),
                            "comp_name": p.comp_name,
                            "from": pa,
                            "to": pb,
                            "delta_pct": round((pb - pa) / pa * 100, 1),
                            "inferred_reason": "公开价上调" if pb > pa else "公开价下调",
                        }
                    )
        events = sorted(events, key=lambda x: x["date"], reverse=True)[:10]

    def _last_adr(points: list) -> Optional[float]:
        for p in reversed(points or []):
            if p.get("self_adr") is not None:
                return p["self_adr"]
        return None

    def _first_adr(points: list) -> Optional[float]:
        for p in points or []:
            if p.get("self_adr") is not None:
                return p["self_adr"]
        return None

    adr7 = _last_adr(series["7"])
    adr14 = _last_adr(series["14"])
    adr30 = _last_adr(series["30"])
    comp_last = None
    if comp_on and series["30"]:
        for p in reversed(series["30"]):
            if p.get("comp_median") is not None:
                comp_last = p["comp_median"]
                break
    self_points = [p["self_adr"] for p in series["30"] if p.get("self_adr") is not None]
    empty_self = len(self_points) == 0
    if empty_self:
        ai_summary = "近 30 天暂无可用的本店平均房价样本（订单单价/建议价）。有入住订单或生成定价建议后将自动展示走势。"
    elif comp_on and events:
        ai_summary = f"近窗内监测到 {len(events)} 条竞品公开价变动（≥5%）。请结合本店预订进度与库存再决定是否调价，系统不自动跟价。"
    elif comp_on:
        ai_summary = "竞品对比已开启：折线为本店真实 ADR（或建议价回退）与竞品公开价中位/最低。暂无显著竞品变价事件。"
    else:
        ai_summary = "当前为内部基准模式：仅展示本店 ADR 与房态库存。配置竞品并开启对比后可叠加竞品中位与公开最低价。"
    return {
        "comp_compare_enabled": comp_on,
        "empty_self_series": empty_self,
        "params_snapshot": {
            "ev_cap": int(float(params.get("ev_cap", 100))),
            "cap_pct": int(float(params.get("cap_pct", 50))),
        },
        "kpis": [
            {
                "label": "近 7 天平均房价",
                "value": adr7 if adr7 is not None else "—",
                "delta": _pricing_booking_pace_service._pct_delta(adr7, _first_adr(series["7"])),
            },
            {
                "label": "近 14 天平均房价",
                "value": adr14 if adr14 is not None else "—",
                "delta": _pricing_booking_pace_service._pct_delta(adr14, _first_adr(series["14"])),
            },
            {
                "label": "近 30 天平均房价",
                "value": adr30 if adr30 is not None else "—",
                "delta": _pricing_booking_pace_service._pct_delta(adr30, _first_adr(series["30"])),
            },
            {
                "label": "竞品中位平均房价" if comp_on else "内部基准模式",
                "value": comp_last if comp_on and comp_last is not None else "—",
                "delta": None,
                "hint": None if comp_on else "开启竞品对比后可见",
            },
        ],
        "series": series,
        "occ_series": occ_series,
        "comp_events": events,
        "ai_summary": ai_summary,
    }


def run_simulate(db: Session, hotel_id: int, scenario: str = "balanced") -> dict:
    """历史回测三情景（规则化 demo）。"""
    scenarios = {
        "conservative": {
            "label": "保守（仅尾端）",
            "revpar_lift": 2.1,
            "occ_lift": 0.8,
            "net_lift": 3.5,
            "horizon": "0-3天",
        },
        "balanced": {
            "label": "平衡（尾端+近端）",
            "revpar_lift": 5.4,
            "occ_lift": 1.6,
            "net_lift": 7.2,
            "horizon": "0-14天",
        },
        "aggressive": {
            "label": "激进（尾端+近端+中期）",
            "revpar_lift": 8.9,
            "occ_lift": -0.5,
            "net_lift": 9.1,
            "horizon": "0-30天",
        },
    }
    rows = []
    for key, meta in scenarios.items():
        rows.append(
            {
                "key": key,
                **meta,
                "selected": key == scenario,
                "vs_actual_revpar": meta["revpar_lift"],
                "vs_actual_occ": meta["occ_lift"],
                "vs_actual_net": meta["net_lift"],
            }
        )
    return {
        "window": "过去 90 天",
        "scenarios": rows,
        "sensitivity": [
            {"factor": "Pace ±10%", "revpar_impact": "±2.1%"},
            {"factor": "竞品中位 ±5%", "revpar_impact": "±1.4%"},
            {"factor": "活动强度 弱→强", "revpar_impact": "+3.8%（封顶约束内）"},
        ],
        "note": "回测为规则化仿真，不构成自动改价授权",
    }
