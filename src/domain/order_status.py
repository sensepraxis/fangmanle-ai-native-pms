# SPDX-License-Identifier: Apache-2.0
"""订单状态机（State 模式）。

把字符串状态 + 散落 if/elif 抽成 enum + 显式转换规则。model 自身
携带 can_xxx 与 xxx() 行为（详见 models/orders.py 给 Order 加的方法）。

主路径约定：service 禁止 ``o.status = "..."``，统一走
``confirm / checkin / checkout / cancel / mark_no_show / transition_to``。
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class OrderStatus(str, Enum):
    """订单 6 个标准状态。

    用 str + Enum 混合继承，保证序列化仍是 str（与 DB / 路由层兼容），
    可直接 str(OrderStatus.CHECKED_IN) == "checked_in"。
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# 合法转换（源 → 目标集合）。空集合 = 终态。
ALLOWED_TRANSITIONS: dict[OrderStatus, FrozenSet[OrderStatus]] = {
    OrderStatus.PENDING: frozenset(
        {
            OrderStatus.CONFIRMED,
            OrderStatus.CHECKED_IN,
            OrderStatus.CANCELLED,
            OrderStatus.NO_SHOW,
        }
    ),
    OrderStatus.CONFIRMED: frozenset(
        {
            OrderStatus.CHECKED_IN,
            OrderStatus.CANCELLED,
            OrderStatus.NO_SHOW,
        }
    ),
    OrderStatus.CHECKED_IN: frozenset({OrderStatus.CHECKED_OUT}),
    OrderStatus.CHECKED_OUT: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.NO_SHOW: frozenset(),
}


def can_transition(src: OrderStatus, dst: OrderStatus) -> bool:
    """判断 src → dst 是否合法。"""
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())


def all_statuses() -> list[str]:
    """返回所有合法 status 字符串（用于校验 / 状态机不变量测试）。"""
    return [s.value for s in OrderStatus]
