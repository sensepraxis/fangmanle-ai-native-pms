# SPDX-License-Identifier: Apache-2.0
"""退款用例专用数据常量：手机号 / 房间号 / 订单号前缀。

从原 `bootstrap.ensure_refund_adjust` 抽离；ensure / seed_* 仍在
`bootstrap.ensure_refund_adjust` 里。
"""

from __future__ import annotations

# 退款用例专用手机号（手机号优先路径）
REFUND_CASE_PHONE = "13900008821"
REFUND_CASE_ROOM = "RF8801"
REFUND_CASE_ORDERS = {
    "wx": "RF-WX-001",
    "ali": "RF-ALI-002",
    "full": "RF-FULL-003",
    "cancel": "RF-CANCEL-004",
}
