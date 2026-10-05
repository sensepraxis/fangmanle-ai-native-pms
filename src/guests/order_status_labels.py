# SPDX-License-Identifier: Apache-2.0
"""订单状态 H5/客档展示 msgid（与企微无关）。"""

from __future__ import annotations

ORDER_ST_CN_H5: dict[str, str] = {
    "pending": "待入住",
    "confirmed": "已确认",
    "checked_in": "在住",
    "checked_out": "已离店",
    "cancelled": "已取消",
    "no_show": "未到",
    "in_house": "在住",
    "reserved": "已预订",
}
