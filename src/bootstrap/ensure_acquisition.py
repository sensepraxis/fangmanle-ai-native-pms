# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""获客闭环：内容 + 线索表结构与种子（无真实小红书账号亦可跑通）。"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from models import (
    AcquisitionContent,
    AcquisitionLead,
    Base,
    Campaign,
    Channel,
    Guest,
    GuestIdentity,
    Hotel,
)

STAGE_ORDER = ("new", "claimed", "private", "booked", "arrived")

CONTENT_SEED = [
    {
        "title": "秋日微度假｜私汤治愈周末",
        "topic": "#周末微度假",
        "impressions": 42000,
        "engagements": 3100,
        "spend": 2800,
    },
    {"title": "带毛孩子逃离城市计划", "topic": "#宠物友好", "impressions": 28500, "engagements": 2200, "spend": 1500},
    {
        "title": "打工人充电站·静音大床房实测",
        "topic": "#打工人周末",
        "impressions": 16800,
        "engagements": 980,
        "spend": 900,
    },
]

LEAD_SEED = [
    {"nickname": "旅行的柿子", "intent": "high", "stage": "new", "note_i": 0},
    {"nickname": "阿柚在上海", "intent": "high", "stage": "new", "note_i": 0},
    {"nickname": "周末不加班", "intent": "mid", "stage": "claimed", "note_i": 1},
    {"nickname": "毛孩子家长小陈", "intent": "high", "stage": "private", "note_i": 1},
    {"nickname": "静音控Lisa", "intent": "mid", "stage": "private", "note_i": 2},
    {"nickname": "探店达人阿K", "intent": "low", "stage": "new", "note_i": 2},
    {"nickname": "两日一夜计划", "intent": "mid", "stage": "claimed", "note_i": 0},
    {"nickname": "私域老客回访", "intent": "high", "stage": "booked", "note_i": 0},
]


def ensure_acquisition_schema(engine: Engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "acquisition_contents" not in tables or "acquisition_leads" not in tables:
        Base.metadata.create_all(
            engine,
            tables=[
                AcquisitionContent.__table__,
                AcquisitionLead.__table__,
            ],
        )


def _ensure_xhs_channel(db: Session) -> Optional[Channel]:
    ch = db.query(Channel).filter_by(code="xiaohongshu").first()
    if ch:
        return ch
    ch = Channel(code="xiaohongshu", name="小红书", type="xiaohongshu", commission_rate=0.06, is_active=True)
    db.add(ch)
    db.flush()
    return ch


def _ensure_campaign(db: Session, hotel_id: int) -> Optional[Campaign]:
    c = db.query(Campaign).filter_by(hotel_id=hotel_id, channel="xiaohongshu").order_by(Campaign.id.asc()).first()
    if c:
        return c
    c = Campaign(
        hotel_id=hotel_id,
        channel="xiaohongshu",
        name="小红书种草笔记",
        status="active",
        spend=5200,
        attributed_rev=16800,
        roi=3.23,
        start_date=(datetime.now() - timedelta(days=20)).date(),
        end_date=(datetime.now() + timedelta(days=10)).date(),
    )
    db.add(c)
    db.flush()
    return c


def ensure_acquisition_seed(db: Session) -> dict:
    """幂等补种内容与线索；已有线索则不重复灌满量。"""
    added_c = 0
    added_l = 0
    _ensure_xhs_channel(db)

    for h in db.query(Hotel).all():
        camp = _ensure_campaign(db, h.id)
        existing_titles = {
            r[0] for r in db.query(AcquisitionContent.title).filter_by(hotel_id=h.id, channel="xiaohongshu").all()
        }
        content_rows: list[AcquisitionContent] = (
            db.query(AcquisitionContent)
            .filter_by(hotel_id=h.id, channel="xiaohongshu")
            .order_by(AcquisitionContent.id)
            .all()
        )
        for item in CONTENT_SEED:
            if item["title"] in existing_titles:
                continue
            row = AcquisitionContent(
                hotel_id=h.id,
                channel="xiaohongshu",
                title=item["title"],
                topic=item["topic"],
                status="published",
                impressions=item["impressions"],
                engagements=item["engagements"],
                spend=item["spend"],
                campaign_id=camp.id if camp else None,
            )
            db.add(row)
            db.flush()
            content_rows.append(row)
            added_c += 1

        lead_n = db.query(AcquisitionLead).filter_by(hotel_id=h.id).count()
        if lead_n >= 6:
            continue

        for i, spec in enumerate(LEAD_SEED):
            ext = f"xhs_demo_{h.id}_{i}"
            exists = db.query(AcquisitionLead).filter_by(hotel_id=h.id, external_id=ext).first()
            if exists:
                continue
            c_row = content_rows[spec["note_i"] % max(len(content_rows), 1)] if content_rows else None
            guest_id = None
            if spec["stage"] in ("claimed", "private", "booked"):
                g = Guest(
                    one_id=f"ONE-XHS-{h.id}-{i}",
                    name=spec["nickname"],
                    phone=f"138{h.id:02d}{i:06d}"[:11],
                    vip_level="normal",
                    city=h.city or "上海",
                )
                db.add(g)
                db.flush()
                guest_id = g.id
                db.add(
                    GuestIdentity(
                        guest_id=g.id,
                        source="xiaohongshu",
                        external_id=ext,
                        confidence=0.92,
                    )
                )
            lead = AcquisitionLead(
                hotel_id=h.id,
                channel="xiaohongshu",
                external_id=ext,
                nickname=spec["nickname"],
                phone=f"138{h.id:02d}{i:06d}"[:11] if guest_id else None,
                stage=spec["stage"],
                intent=spec["intent"],
                note_title=c_row.title if c_row else spec.get("topic"),
                content_id=c_row.id if c_row else None,
                guest_id=guest_id,
                remark="种子线索",
            )
            db.add(lead)
            added_l += 1

        # 抖音线索（双轨之线索路）
        dy_n = db.query(AcquisitionLead).filter_by(hotel_id=h.id, channel="douyin").count()
        if dy_n < 3:
            dy_specs = [
                {"nickname": "@直播观众A", "stage": "new", "intent": "high", "note": "直播间咨询价格"},
                {"nickname": "@探店达人粉", "stage": "claimed", "intent": "mid", "note": "短视频私信留资"},
                {"nickname": "@本地推线索", "stage": "private", "intent": "high", "note": "本地推表单"},
            ]
            for j, spec in enumerate(dy_specs):
                ext = f"dy_demo_{h.id}_{j}"
                if db.query(AcquisitionLead).filter_by(hotel_id=h.id, external_id=ext).first():
                    continue
                db.add(
                    AcquisitionLead(
                        hotel_id=h.id,
                        channel="douyin",
                        external_id=ext,
                        nickname=spec["nickname"],
                        phone=f"139{h.id:02d}{j:06d}"[:11],
                        stage=spec["stage"],
                        intent=spec["intent"],
                        note_title=spec["note"],
                        remark="抖音种子线索",
                    )
                )
                added_l += 1

    db.commit()
    return {"contents_added": added_c, "leads_added": added_l}


def mock_ingest_leads(
    db: Session, hotel_id: int, count: int = 3, channel: str = "xiaohongshu"
) -> list[AcquisitionLead]:
    """模拟渠道拉入新线索（无需真实账号）。"""
    contents = (
        db.query(AcquisitionContent).filter_by(hotel_id=hotel_id, channel=channel).order_by(AcquisitionContent.id).all()
    )
    if not contents and channel == "xiaohongshu":
        ensure_acquisition_seed(db)
        contents = (
            db.query(AcquisitionContent)
            .filter_by(hotel_id=hotel_id, channel=channel)
            .order_by(AcquisitionContent.id)
            .all()
        )
    if channel == "douyin":
        nicknames = ["@探店小王", "@周末出游", "@直播观众", "@本地生活", "@达人粉丝"]
        note_titles = ["抖音探店短视频", "直播间挂券", "POI 到店咨询", "本地推留资"]
    else:
        nicknames = ["周末出发", "想住江景", "带娃出游", "静音控", "探店新人", "复购老粉", "宠物同行"]
        note_titles = []
    out: list[AcquisitionLead] = []
    ts = int(datetime.now().timestamp())
    prefix = "dy" if channel == "douyin" else "xhs"
    for i in range(max(1, min(count, 8))):
        c = random.choice(contents) if contents else None
        ext = f"{prefix}_mock_{hotel_id}_{ts}_{i}"
        lead = AcquisitionLead(
            hotel_id=hotel_id,
            channel=channel,
            external_id=ext,
            nickname=random.choice(nicknames) + ("" if channel == "douyin" else str(random.randint(1, 99))),
            stage="new",
            intent=random.choice(["high", "high", "mid", "low"]),
            note_title=(c.title if c else random.choice(note_titles) if note_titles else "模拟种草笔记"),
            content_id=c.id if c else None,
            remark="Mock 入库" if channel == "douyin" else "Mock 入库（无真实小红书账号）",
        )
        db.add(lead)
        out.append(lead)
    db.commit()
    for lead in out:
        db.refresh(lead)
    return out
