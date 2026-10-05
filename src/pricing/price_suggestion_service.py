# SPDX-License-Identifier: Apache-2.0
"""经典 PriceSuggestion 列表 / 决策（从 Fat Controller 下沉）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import InvalidStateError, NotFoundError, ValidationError
from models import PriceSuggestion, RoomType


def list_price_suggestions(db: Session, hotel_id: int) -> list[dict]:
    rows = (
        db.query(PriceSuggestion, RoomType.name.label("room_type_name"))
        .join(RoomType, PriceSuggestion.room_type_id == RoomType.id)
        .filter(PriceSuggestion.hotel_id == hotel_id)
        .order_by(PriceSuggestion.biz_date, RoomType.name)
        .all()
    )
    out = []
    for p, rtname in rows:
        d = row_to_dict(p)
        d["room_type_name"] = rtname
        out.append(d)
    return out


def decide_price_suggestion(db: Session, pid: int, *, action: str) -> dict:
    p = db.get(PriceSuggestion, pid)
    if not p:
        raise NotFoundError("suggestion not found")
    if action == "accept":
        if p.status == "blocked":
            raise InvalidStateError("该建议被护栏拦截，无法采纳：" + str(p.guardrail_msg))
        p.status = "accepted"
    elif action == "reject":
        p.status = "rejected"
    else:
        raise ValidationError("action must be accept/reject")
    p.decided_at = datetime.now()
    db.flush()
    return row_to_dict(p)
