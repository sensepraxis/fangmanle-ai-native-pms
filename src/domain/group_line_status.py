# SPDX-License-Identifier: Apache-2.0
"""团体房行状态机。"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class GroupLineStatus(str, Enum):
    HELD = "held"
    ASSIGNED = "assigned"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[GroupLineStatus, FrozenSet[GroupLineStatus]] = {
    GroupLineStatus.HELD: frozenset(
        {
            GroupLineStatus.ASSIGNED,
            GroupLineStatus.CHECKED_IN,
            GroupLineStatus.CANCELLED,
        }
    ),
    GroupLineStatus.ASSIGNED: frozenset(
        {
            GroupLineStatus.CHECKED_IN,
            GroupLineStatus.HELD,
            GroupLineStatus.CANCELLED,
        }
    ),
    GroupLineStatus.CHECKED_IN: frozenset(
        {
            GroupLineStatus.CHECKED_OUT,
            GroupLineStatus.CANCELLED,
        }
    ),
    GroupLineStatus.CHECKED_OUT: frozenset(),
    GroupLineStatus.CANCELLED: frozenset(),
}


def can_transition(src: GroupLineStatus, dst: GroupLineStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())
