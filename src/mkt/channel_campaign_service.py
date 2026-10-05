# SPDX-License-Identifier: Apache-2.0
"""Legacy campaigns 表（获客渠道计划）CRUD — 与 MktCampaign 并行。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import ValidationError
from models import Campaign


def list_channel_campaigns(db: Session, hotel_id: int, *, limit: int = 40) -> list[dict]:
    rows = db.query(Campaign).filter_by(hotel_id=hotel_id).order_by(Campaign.id.desc()).limit(limit).all()
    return [row_to_dict(c) for c in rows]


def create_channel_campaign(db: Session, hotel_id: int, payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValidationError("name required")

    def _to_date(s) -> Optional[date]:
        if not s:
            return None
        if isinstance(s, date):
            return s
        try:
            return datetime.strptime(str(s), "%Y-%m-%d").date()
        except ValueError:
            return None

    c = Campaign(
        hotel_id=hotel_id,
        name=name,
        channel=payload.get("channel") or "全渠道",
        status=payload.get("status") or "draft",
        spend=payload.get("budget") or 0,
        start_date=_to_date(payload.get("start_date")),
        end_date=_to_date(payload.get("end_date")),
    )
    db.add(c)
    db.flush()
    db.refresh(c)
    return row_to_dict(c)
