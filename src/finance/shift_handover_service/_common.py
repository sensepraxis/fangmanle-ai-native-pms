# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: 跨域共用 helper（_money / _f / _mask_name）。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    Channel,
    Deposit,
    DepositLedgerEntry,
    FinanceReport,
    Guest,
    GuestTag,
    Order,
    Payment,
    Reservation,
    Room,
    ServiceRequest,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    Supply,
    TagDefinition,
    User,
)


def _money(v: Any) -> Decimal:
    return Decimal(str(round(float(v or 0), 2)))


def _f(v: Any) -> float:
    return round(float(v or 0), 2)


def _mask_name(name: str) -> str:
    n = (name or "").strip()
    if len(n) <= 1:
        return n + "**" if n else "—"
    return n[0] + "**"


def _log(
    db: Session,
    handover_id: int,
    hotel_id: int,
    action: str,
    actor_id: int | None,
    actor_name: str,
    payload: dict | None = None,
):
    """写一条审计日志（ShiftAuditLog）；子模块通用 helper。"""
    db.add(
        ShiftAuditLog(
            handover_id=handover_id,
            hotel_id=hotel_id,
            action=action,
            actor_user_id=actor_id,
            actor_name=actor_name,
            payload=json.dumps(payload or {}, ensure_ascii=False),
        )
    )


_EMPTY_AI_STATUS = {
    "has_draft": False,
    "has_approved": False,
    "draft": None,
    "narrative": "",
    "takeover_brief": "",
    "takeover_advice": [],
    "takeover_guest_focus": [],
    "takeover_claim_hints": [],
    "confirmed_at": None,
    "ai_session_id": None,
}


def guest_situations_for_display(db: Session, hotel_id: int, handover: ShiftHandover) -> list:
    from finance.shift_handover_service.task_service import guest_situations_for_display as _impl

    return _impl(db, hotel_id, handover)


def tasks_for_display(db: Session, hotel_id: int, handover: ShiftHandover) -> list:
    from finance.shift_handover_service.task_service import tasks_for_display as _impl

    return _impl(db, hotel_id, handover)


def ai_status_for_handover(row: ShiftHandover) -> dict:
    from infra.commercial_pack import optional_call

    return optional_call(
        "commercial.finance.shift_ai_harness",
        "ai_status_for_handover",
        dict(_EMPTY_AI_STATUS),
        row,
    )
