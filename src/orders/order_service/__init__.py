# SPDX-License-Identifier: Apache-2.0
"""orders.order_service 子包 — 保留外部 import 兼容。

原 orders/order_service.py（1616 行）按业务子域拆为：
  - lifecycle_service : create/checkin/checkout/cancel + 序列化
  - list_service      : list/compat/work_summary
  - group_service     : 团体订单
  - voucher_service   : 券/即时入住/OTA 同步

外部 `from orders.order_service import xxx` 走这里 re-export，零改动。
"""

from __future__ import annotations

from orders.order_service import group_service as __group_service
from orders.order_service import lifecycle_service as __lifecycle_service
from orders.order_service import list_service as __list_service
from orders.order_service import voucher_service as __voucher_service

# Public re-exports
from orders.order_service.group_service import assign_group_line, checkin_group_line, create_group_order
from orders.order_service.lifecycle_service import (
    cancel_order,
    checkin_order,
    checkout_order,
    create_order_record,
    order_detail_dict,
    row_to_dict,
)
from orders.order_service.list_service import list_orders_compat, orders_work_summary, query_orders_list
from orders.order_service.voucher_service import (
    detect_voucher_platform,
    lookup_voucher,
    sync_ota_order,
    verify_voucher_and_order,
    walk_in_checkin,
)

__all__ = [
    "assign_group_line",
    "cancel_order",
    "checkin_group_line",
    "checkin_order",
    "checkout_order",
    "create_group_order",
    "create_order_record",
    "detect_voucher_platform",
    "list_orders_compat",
    "lookup_voucher",
    "order_detail_dict",
    "orders_work_summary",
    "query_orders_list",
    "row_to_dict",
    "sync_ota_order",
    "verify_voucher_and_order",
    "walk_in_checkin",
]
