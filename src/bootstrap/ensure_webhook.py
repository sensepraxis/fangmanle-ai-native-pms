# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""Webhook 多租户绑定表与种子。"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from mkt.xhs_webhook import new_binding_token
from models import Base, Hotel, HotelChannelBinding


def ensure_webhook_schema(engine: Engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    needed = {"hotel_channel_bindings", "webhook_event_logs"}
    if not needed.issubset(tables):
        from models import HotelChannelBinding, WebhookEventLog

        Base.metadata.create_all(
            engine,
            tables=[
                HotelChannelBinding.__table__,
                WebhookEventLog.__table__,
            ],
        )


def ensure_webhook_bindings_seed(db: Session) -> dict:
    """每家酒店幂等创建一条小红书绑定。"""
    added = 0
    for h in db.query(Hotel).all():
        exists = db.query(HotelChannelBinding).filter_by(hotel_id=h.id, channel="xiaohongshu").first()
        if exists:
            continue
        token = new_binding_token()
        db.add(
            HotelChannelBinding(
                hotel_id=h.id,
                channel="xiaohongshu",
                label=f"{h.name} · 聚光绑定",
                xhs_ad_account_id=f"xhs_ad_demo_{h.id}",
                xhs_professional_id=f"xhs_pro_demo_{h.id}",
                binding_token=token,
                webhook_secret=f"demo-secret-h{h.id}",
                status="active",
            )
        )
        added += 1
    db.commit()
    return {"bindings_added": added}
