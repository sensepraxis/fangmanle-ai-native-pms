# SPDX-License-Identifier: BUSL-1.1
"""AI 问数 · 会话状态（session touch / turns 加载）。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models import AiAskQuery, AiAskSession

MAX_CLARIFY_ROUNDS = 3
MAX_HISTORY_TURNS = 2


def _touch_session(db: Session, session_id: str, hotel_id: int) -> None:
    row = db.get(AiAskSession, session_id)
    now = datetime.utcnow()
    if not row:
        db.add(AiAskSession(session_id=session_id, hotel_id=hotel_id, created_at=now, last_active_at=now))
    else:
        row.last_active_at = now
        row.hotel_id = hotel_id
    db.commit()


def load_session_turns(
    db: Session, session_id: str, hotel_id: int, limit: int = MAX_HISTORY_TURNS
) -> list[dict[str, Any]]:
    rows = (
        db.query(AiAskQuery)
        .filter(
            AiAskQuery.session_id == session_id,
            AiAskQuery.hotel_id == hotel_id,
            AiAskQuery.confirmed_at.isnot(None),
            AiAskQuery.answer_json.isnot(None),
        )
        .order_by(AiAskQuery.id.desc())
        .limit(limit)
        .all()
    )
    turns: list[dict[str, Any]] = []
    for r in reversed(rows):
        try:
            ans = json.loads(r.answer_json or "{}")
        except Exception:
            ans = {}
        try:
            slots = json.loads(r.slots_json or "{}")
        except Exception:
            slots = {}
        turns.append(
            {
                "query_id": r.id,
                "q": r.resolved_question or r.raw_question,
                "intent_id": r.intent_id,
                "intent_label": r.intent_label,
                "slots": {k: v for k, v in slots.items() if not str(k).startswith("_")},
                "result_summary": ans.get("summary") or "",
            }
        )
    return turns
