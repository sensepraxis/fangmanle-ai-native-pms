# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: shift_window_service。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from infra.i18n import t
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

SHIFT_WINDOWS = {1: (8, 20, "1 班（早班）"), 2: (20, 24, "2 班（晚班）"), 3: (0, 8, "3 班（夜班）")}


def _current_shift(now: datetime | None = None) -> tuple[int, datetime, datetime, datetime, str]:
    now = now or datetime.now()
    h = now.hour
    d = now.date()
    if 8 <= h < 20:
        no, start_h, end_h, label = (1, 8, 20, t("1 班（早班）"))
        start = datetime.combine(d, datetime.min.time().replace(hour=start_h))
        end = datetime.combine(d, datetime.min.time().replace(hour=end_h))
    elif h >= 20:
        no, start_h, end_h, label = (2, 20, 24, t("2 班（晚班）"))
        start = datetime.combine(d, datetime.min.time().replace(hour=start_h))
        end = datetime.combine(d + timedelta(days=1), datetime.min.time().replace(hour=0))
        end = datetime.combine(d, datetime.min.time().replace(hour=23, minute=59))
    else:
        no, label = (3, t("3 班（夜班）"))
        start = datetime.combine(d - timedelta(days=1), datetime.min.time().replace(hour=0))
        start = datetime.combine(d, datetime.min.time().replace(hour=0))
        end = datetime.combine(d, datetime.min.time().replace(hour=8))
    scheduled = end
    return (no, start, end, scheduled, label)


def _shift_window(handover: ShiftHandover, now: datetime | None = None) -> tuple[datetime, datetime]:
    """本班统计窗口：班次开始 → min(当前, 计划结束)。"""
    now = now or datetime.now()
    start = handover.start_at or now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_cap = handover.end_at or now
    end = min(now, end_cap) if end_cap else now
    if end <= start:
        end = start + timedelta(minutes=1)
    return (start, end)
