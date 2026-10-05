# SPDX-License-Identifier: Apache-2.0
"""价格助手：建表 + Demo 种子（竞品/事件/Pace/建议）。

价格助手默认值 / Mock 数据已抽到 `pricing.defaults`；本文件保留 schema 保活与种子函数。
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from models import (
    Base,
    CompetitorProperty,
    CompetitorRateSnapshot,
    CompetitorRoomMap,
    CompetitorSet,
    EventCalendar,
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
from pricing.defaults import MOCK_COMPETITORS, MOCK_MAP_CANDIDATES, PRICING_MODELS


def _sid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def ensure_pricing_assistant_schema(engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = [m.__table__ for m in PRICING_MODELS if m.__tablename__ not in tables]
    if need:
        Base.metadata.create_all(engine, tables=need)
    # 增量列（已有表时 create_all 不会补列）
    with engine.begin() as conn:
        insp_conn = inspect(conn)
        cols_cfg = (
            {c["name"] for c in insp_conn.get_columns("pricing_assistant_config")}
            if "pricing_assistant_config" in tables or True
            else set()
        )
        try:
            cols_cfg = {c["name"] for c in insp_conn.get_columns("pricing_assistant_config")}
        except Exception:
            cols_cfg = set()
        alters = []
        if cols_cfg and "comp_compare_enabled" not in cols_cfg:
            alters.append("ALTER TABLE pricing_assistant_config ADD COLUMN comp_compare_enabled BOOLEAN DEFAULT FALSE")
        if cols_cfg and "params_json" not in cols_cfg:
            alters.append("ALTER TABLE pricing_assistant_config ADD COLUMN params_json TEXT")
        try:
            cols_reco = {c["name"] for c in insp_conn.get_columns("pricing_recommendation")}
        except Exception:
            cols_reco = set()
        if cols_reco and "explain_json" not in cols_reco:
            alters.append("ALTER TABLE pricing_recommendation ADD COLUMN explain_json TEXT")
        try:
            cols_map = {c["name"] for c in insp_conn.get_columns("competitor_room_map")}
        except Exception:
            cols_map = set()
        if cols_map and "weight" not in cols_map:
            alters.append("ALTER TABLE competitor_room_map ADD COLUMN weight NUMERIC(4,3) DEFAULT 1.000")
        try:
            cols_ev = {c["name"] for c in insp_conn.get_columns("event_calendar")}
        except Exception:
            cols_ev = set()
        if cols_ev and "heat_score" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN heat_score NUMERIC(5,2)")
        if cols_ev and "venue_address" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN venue_address VARCHAR(255)")
        if cols_ev and "note" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN note VARCHAR(255)")
        if cols_ev and "is_active" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
        if cols_ev and "venue_lat" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN venue_lat NUMERIC(10,6)")
        if cols_ev and "venue_lng" not in cols_ev:
            alters.append("ALTER TABLE event_calendar ADD COLUMN venue_lng NUMERIC(10,6)")
        for sql in alters:
            try:
                conn.exec_driver_sql(sql)
            except Exception:
                pass

    # 存量 Demo 事件对齐热度模型（幂等）
    try:
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(bind=engine)
        s = SessionLocal()
        try:
            for row in s.query(EventCalendar).all():
                name = str(row.event_name or "")
                if "周杰伦" in name:
                    row.intensity = "爆"
                    row.heat_score = 95
                    row.price_uplift_max = 1.0
                elif row.event_type == "holiday" and "国庆" in name:
                    row.intensity = "强"
                    row.price_uplift_max = 1.0
                elif row.price_uplift_max is not None and float(row.price_uplift_max) <= 0.5:
                    # 旧默认 0.5 升级为系统红线口径 1.0（事件自身不再比红线更严）
                    row.price_uplift_max = 1.0
            s.commit()
        finally:
            s.close()
    except Exception:
        pass


def seed_pricing_assistant_demo(db: Session, hotel_id: int = 1) -> dict[str, Any]:
    """幂等种子：已有 config 且已有建议则跳过。"""
    from pricing.pricing_assistant import generate_recommendations, get_or_create_config

    existing = get_or_create_config(db, hotel_id)
    if db.query(PricingRecommendation).filter_by(hotel_id=hotel_id).count() > 0:
        return {"skipped": True, "reason": "already_seeded"}

    today = date.today()
    room_types = db.query(RoomType).filter_by(hotel_id=hotel_id).all()
    if not room_types:
        return {"skipped": True, "reason": "no_room_types"}

    rooms_n = max(db.query(Room).filter_by(hotel_id=hotel_id).count(), 1)
    _ = existing  # config 已确保存在

    # BAR
    for rt in room_types:
        if db.query(RoomTypeBaseRate).filter_by(hotel_id=hotel_id, room_type_id=rt.id).first():
            continue
        base = float(rt.base_price or 380)
        db.add(
            RoomTypeBaseRate(
                room_type_id=rt.id,
                hotel_id=hotel_id,
                base_rate=base,
                bar_upper=round(base * 2.0, 2),
                bar_lower=round(base * 0.7, 2),
                n_floor=round(base * 0.7 * 0.85, 2),
                effective_from=today - timedelta(days=30),
            )
        )

    # 竞品集
    sets_meta = [
        ("同档经济型（默认）", "同档", True),
        ("高一档中端", "高一档", False),
        ("低一档", "低一档", False),
    ]
    set_ids: list[str] = []
    for name, tag, active in sets_meta:
        sid = _sid("cs_")
        set_ids.append(sid)
        if not db.query(CompetitorSet).filter_by(hotel_id=hotel_id, set_name=name).first():
            db.add(
                CompetitorSet(
                    set_id=sid,
                    hotel_id=hotel_id,
                    set_name=name,
                    segment_tag=tag,
                    default_radius_km=3.0,
                    is_active=active,
                )
            )
        else:
            row = db.query(CompetitorSet).filter_by(hotel_id=hotel_id, set_name=name).first()
            set_ids[-1] = row.set_id

    default_set = set_ids[0]
    primary_rt = room_types[0]
    comp_ids: list[str] = []

    for i, c in enumerate(MOCK_COMPETITORS[:7]):
        cid = _sid("cp_")
        comp_ids.append(cid)
        if db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, comp_name=c["name"]).first():
            row = db.query(CompetitorProperty).filter_by(hotel_id=hotel_id, comp_name=c["name"]).first()
            comp_ids[-1] = row.comp_id
            continue
        db.add(
            CompetitorProperty(
                comp_id=cid,
                set_id=default_set if i < 6 else set_ids[1],
                hotel_id=hotel_id,
                comp_name=c["name"],
                comp_lat=c["lat"],
                comp_lng=c["lng"],
                address=f"距本店约 {c['km']} km",
                star_rating=c["star"],
                review_score=c["score"],
                distance_km=c["km"],
                data_source=c["src"],
                source_ref="seed",
                ota_public_url=f"https://hotels.ctrip.com/search?keyword={c['name']}",
                is_active=True,
            )
        )
        # 房型映射
        raw_names = ["豪华大床房", "高级大床", "大床房A", "舒适大床"]
        db.add(
            CompetitorRoomMap(
                map_id=_sid("crm_"),
                comp_id=cid,
                self_room_type_id=primary_rt.id,
                hotel_id=hotel_id,
                comp_room_type_raw=raw_names[i % len(raw_names)],
                mapped_by="seed",
                is_active=True,
            )
        )

    # 竞品价快照（未来 14 天 + 过去 7 天）
    for cid in comp_ids[:6]:
        for offset in range(-7, 15):
            d = today + timedelta(days=offset)
            # 周末/演唱会附近抬价
            weekend = 1.08 if d.weekday() >= 4 else 1.0
            concert_boost = 1.28 if 2 <= offset <= 4 else 1.0
            base_p = 380 * weekend * concert_boost * random.uniform(0.92, 1.08)
            snap = f"crs_{cid}_{d.isoformat()}"
            if db.query(CompetitorRateSnapshot).filter_by(snapshot_id=snap).first():
                continue
            db.add(
                CompetitorRateSnapshot(
                    snapshot_id=snap,
                    comp_id=cid,
                    hotel_id=hotel_id,
                    stay_date=d,
                    room_type_eq=primary_rt.name or "大床房",
                    channel="ota_ctrip",
                    observed_price=round(base_p, 0),
                    rate_plan_code="BAR",
                    captured_at=datetime.now() - timedelta(hours=random.randint(1, 20)),
                )
            )

    # Pace 快照
    for rt in room_types[:3]:
        for offset in range(0, 14):
            d = today + timedelta(days=offset)
            pid = f"pace_{hotel_id}_{rt.id}_{d.isoformat()}"
            if db.query(PaceSnapshot).filter_by(pace_id=pid).first():
                continue
            expected = max(1, int(rooms_n / max(len(room_types), 1) * 0.75))
            booked = int(expected * random.uniform(0.75, 1.25))
            db.add(
                PaceSnapshot(
                    pace_id=pid,
                    hotel_id=hotel_id,
                    room_type_id=rt.id,
                    stay_date=d,
                    booked=booked,
                    expected=expected,
                    pace_ratio=round(booked / expected, 2),
                )
            )

    # 事件：节假日 + 演唱会（热度模型：heat × 斜率，硬上限 +100%）
    # 名称随 SEED_LOCALE；intensity 仍用算法码 弱/中/强/爆
    from seed.locale_pack import get_pack

    _ev_pack = get_pack()
    events = []
    for etype, ename, s_off, e_off, dist, intensity, heat, uplift in _ev_pack.PRICING_EVENTS:
        events.append(
            (
                etype,
                ename,
                today + timedelta(days=s_off),
                today + timedelta(days=e_off),
                dist,
                intensity,
                heat,
                uplift,
            )
        )
    for etype, ename, s, e, dist, intensity, heat, uplift in events:
        eid = _sid("ev_")
        if db.query(EventCalendar).filter_by(hotel_id=hotel_id, event_name=ename).first():
            continue
        db.add(
            EventCalendar(
                event_id=eid,
                hotel_id=hotel_id,
                event_type=etype,
                event_name=ename,
                start_at=datetime.combine(s, datetime.min.time()),
                end_at=datetime.combine(e, datetime.max.time().replace(microsecond=0)),
                distance_km=dist,
                intensity=intensity,
                heat_score=heat,
                price_uplift_max=uplift,
                source="manual" if etype != "holiday" else "builtin",
                venue_address=None,
                note=None,
                is_active=True,
            )
        )

    # 告警
    alerts = [
        (
            "red",
            "comp_drop",
            "竞品大幅降价：维也纳 同档大床降幅 -13.8%",
            "竞品降价 ≥8% 且持续 24h。建议在「AI 定价建议」人工复核，Pace 良好时不必跟降。",
            "去 AI 定价建议查看",
        ),
        (
            "yellow",
            "pace",
            "Pace 偏离基线：大床房近端 Pace +22%",
            "近端预订进度显著高于基线，可考虑尾端溢价。",
            "生成近端建议",
        ),
        (
            "red",
            "parity",
            "OTA 倒挂：携程展示价低于直订 6%",
            "监测到渠道 parity 异常，请人工核对渠道同步，勿自动反制。",
            "启动 parity 抽查",
        ),
        ("blue", "adr_gap", "本店 ADR 偏离竞品中位 +5.2%", "小幅偏高，平日段可观察 Pace 后再决定。", "查看价格对比"),
    ]
    for sev, atype, title, detail, action in alerts:
        aid = _sid("pa_")
        if db.query(ParityAlert).filter_by(hotel_id=hotel_id, title=title).first():
            continue
        db.add(
            ParityAlert(
                alert_id=aid,
                hotel_id=hotel_id,
                channel_a="ota_ctrip",
                channel_b="direct",
                room_type_id=primary_rt.id,
                stay_date=today + timedelta(days=2),
                price_a=448,
                price_b=478,
                delta_pct=-6.3 if sev == "red" else 5.2,
                duration_hours=26 if sev == "red" else 8,
                severity=sev,
                status="open",
                alert_type=atype,
                title=title,
                detail=detail,
                suggested_action=action,
            )
        )

    # 生成一批建议
    gen = generate_recommendations(db, hotel_id, days=7, force=True)
    db.commit()
    return {
        "skipped": False,
        "room_types": len(room_types),
        "competitors": len(comp_ids),
        "recommendations": gen.get("created", 0),
        "alerts": len(alerts),
    }


def mock_map_candidates(hotel_id: int = 1) -> list[dict]:
    """Mock 3km 周边酒店候选（AI 匹配需店长确认）。"""
    out = []
    for i, c in enumerate(MOCK_MAP_CANDIDATES):
        match = round(0.92 - i * 0.06, 2)
        out.append(
            {
                "candidate_id": f"mc_{hotel_id}_{i}",
                "comp_name": c["name"],
                "comp_lat": c["lat"],
                "comp_lng": c["lng"],
                "star_rating": c["star"],
                "review_score": c["score"],
                "distance_km": c["km"],
                "match_score": match,
                "match_dims": ["经纬度", "星级", "评分", "房型"],
                "confirmed": False,
            }
        )
    return out
