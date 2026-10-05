# SPDX-License-Identifier: Apache-2.0
"""入住登记（PmsCheckin）状态机。"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class CheckinStatus(str, Enum):
    INHOUSE = "inhouse"
    CHECKED_OUT = "checked_out"
    TRANSFERRED = "transferred"


ALLOWED_TRANSITIONS: dict[CheckinStatus, FrozenSet[CheckinStatus]] = {
    CheckinStatus.INHOUSE: frozenset(
        {
            CheckinStatus.CHECKED_OUT,
            CheckinStatus.TRANSFERRED,
        }
    ),
    CheckinStatus.CHECKED_OUT: frozenset(),
    CheckinStatus.TRANSFERRED: frozenset(),
}


def can_transition(src: CheckinStatus, dst: CheckinStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())
