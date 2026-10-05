# SPDX-License-Identifier: Apache-2.0
"""账单 Folio 状态机（open / partial / closed）。"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class FolioStatus(str, Enum):
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


ALLOWED_TRANSITIONS: dict[FolioStatus, FrozenSet[FolioStatus]] = {
    FolioStatus.OPEN: frozenset({FolioStatus.PARTIAL, FolioStatus.CLOSED, FolioStatus.OPEN}),
    FolioStatus.PARTIAL: frozenset({FolioStatus.OPEN, FolioStatus.CLOSED, FolioStatus.PARTIAL}),
    FolioStatus.CLOSED: frozenset({FolioStatus.OPEN, FolioStatus.PARTIAL}),  # 反结账可重开
}


def derive_status(*, balance, payment_total) -> str:
    """按余额/已收推导状态（与历史 recalc_folio 语义一致）。"""
    from decimal import Decimal

    bal = Decimal(str(balance or 0))
    pay = Decimal(str(payment_total or 0))
    if bal <= 0 and pay > 0:
        return FolioStatus.CLOSED.value
    if pay > 0:
        return FolioStatus.PARTIAL.value
    return FolioStatus.OPEN.value


def can_transition(src: FolioStatus, dst: FolioStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())
