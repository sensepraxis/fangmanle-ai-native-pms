# SPDX-License-Identifier: Apache-2.0
"""房务工单状态机（State 模式）。"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class HKStatus(str, Enum):
    OPEN = "open"  # 初始态：未派
    ASSIGNED = "assigned"  # 已派工，未开始
    IN_PROGRESS = "in_progress"  # 保洁已开始
    PENDING_INSPECT = "pending_inspect"  # 清洁完成 → 待查房
    REWORK = "rework"  # 查房不通过 → 返工
    DONE = "done"  # 查房通过 → 完成
    IGNORED = "ignored"  # 标记 / 不作申诉


# 终态集合（业务上不可再启动）——模块级避免污染 enum 成员数
TERMINAL = frozenset({HKStatus.DONE, HKStatus.IGNORED})


# 合法转换
ALLOWED_TRANSITIONS: dict[HKStatus, FrozenSet[HKStatus]] = {
    HKStatus.OPEN: frozenset(
        {HKStatus.ASSIGNED, HKStatus.IN_PROGRESS, HKStatus.IGNORED, HKStatus.PENDING_INSPECT, HKStatus.REWORK}
    ),
    HKStatus.ASSIGNED: frozenset({HKStatus.IN_PROGRESS, HKStatus.IGNORED, HKStatus.PENDING_INSPECT, HKStatus.REWORK}),
    HKStatus.IN_PROGRESS: frozenset({HKStatus.PENDING_INSPECT, HKStatus.IGNORED, HKStatus.REWORK}),
    HKStatus.PENDING_INSPECT: frozenset({HKStatus.DONE, HKStatus.REWORK}),
    HKStatus.REWORK: frozenset({HKStatus.IN_PROGRESS, HKStatus.IGNORED, HKStatus.PENDING_INSPECT}),
    HKStatus.DONE: frozenset(),
    HKStatus.IGNORED: frozenset(),
}


# "开作业中"（含 IGNORED）：用于 `_openish_for_room` 这类"房间里是否有未完成工单"的判断。
# 业务原义见 housekeeping_service.py line 282-285。
HK_OPENISH = frozenset(
    {
        HKStatus.OPEN,
        HKStatus.ASSIGNED,
        HKStatus.IN_PROGRESS,
        HKStatus.PENDING_INSPECT,
        HKStatus.REWORK,
        HKStatus.IGNORED,
    }
)

# "可执行中工单"（不含 IGNORED）：用于"班次未完成"等业务判断——已 ignore 的不再算"未完成"。
HK_OPENISH_ACTIVE = frozenset(
    {
        HKStatus.OPEN,
        HKStatus.ASSIGNED,
        HKStatus.IN_PROGRESS,
        HKStatus.PENDING_INSPECT,
        HKStatus.REWORK,
    }
)


def is_terminal(st: HKStatus) -> bool:
    return st in TERMINAL


def can_transition(src: HKStatus, dst: HKStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())


def all_statuses() -> list[str]:
    return [s.value for s in HKStatus]
