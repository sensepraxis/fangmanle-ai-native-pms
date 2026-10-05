# SPDX-License-Identifier: Apache-2.0
"""评价回复写操作（从 Fat Controller 下沉）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import NotFoundError
from models import Review


def list_reviews(db: Session, hotel_id: int) -> list[dict]:
    rows = db.query(Review).filter(Review.hotel_id == hotel_id).all()
    return [row_to_dict(r) for r in rows]


def patch_review(
    db: Session,
    hotel_id: int,
    review_id: int,
    *,
    replied: bool = True,
    reply_content: Optional[str] = None,
) -> dict:
    r = db.get(Review, review_id)
    if not r or r.hotel_id != hotel_id:
        raise NotFoundError("评价不存在")
    r.replied = bool(replied)
    if reply_content is not None:
        r.reply_content = reply_content
    db.flush()
    return row_to_dict(r)
