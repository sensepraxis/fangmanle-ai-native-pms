# SPDX-License-Identifier: Apache-2.0
"""押金领域服务 Facade：兼容 re-export（实现已绞杀至 board / ops / lookup / common）。"""

from __future__ import annotations

from finance.deposit_board import board, detect_anomalies  # noqa: F401
from finance.deposit_common import (  # noqa: F401
    VALID_ORDER_STATUSES,
    _digits,
    _mask_guest_name,
    _next_deposit_id,
    _serialize_order_for_collect,
    _write_ledger,
    credit_preview,
    deposits_for_order,
    serialize_deposit,
    to_cents,
    yuan,
)
from finance.deposit_lookup import (  # noqa: F401
    lookup_by_guest,
    lookup_by_phone,
    lookup_by_room,
)
from finance.deposit_ops import (  # noqa: F401
    capture,
    collect,
    dispute,
    get_detail,
    list_collectable_orders,
    reauthorize,
    release,
)

__all__ = [
    "yuan",
    "to_cents",
    "deposits_for_order",
    "credit_preview",
    "serialize_deposit",
    "detect_anomalies",
    "board",
    "get_detail",
    "collect",
    "capture",
    "release",
    "reauthorize",
    "dispute",
    "list_collectable_orders",
    "lookup_by_phone",
    "lookup_by_guest",
    "lookup_by_room",
    "_write_ledger",
    "_next_deposit_id",
]
