# SPDX-License-Identifier: Apache-2.0
"""Event Bus：业务生命周期事件的发布/订阅基础设施。

背景：开源 SaaS 的标配——n8n / Odoo / Saleor / Metabase 都内置 event bus，
让"开单时推 Slack"、"客人入住时加好友"等扩展不必改源码。

本模块提供：
- ``EventBus`` 单例：线程安全的 subscribe / publish / unsubscribe
- ``publish(event, payload)``：底层同步发布
- ``emit(event, payload)``：业务埋点推荐入口（失败只记日志，不拖垮业务）
- ``subscribe(event)``：业务扩展订阅（装饰器）
- ``async_publish(event, payload)``：可选异步触发（fire-and-forget）
- ``get_subscribers(event)``：调试用
- ``install_webhook_integration()``：启动时把 lifecycle 事件桥到 WebHook

**当前埋点**（业务路径已接通）：
- order.created             — 订单创建
- guest.checked_in          — 客人入住
- guest.checked_out         — 客人离店
- coupon.redeemed           — 券核销
- deposit.created           — 押金创建
- room.status_changed       — 房态变更
- hk.task_completed         — 房务任务完成（查房通过）
- shift.handover_completed  — 班次交接完成
- wecom.friend_added        — 新加企业微信好友
- night_audit.completed     — 夜审跑批完成
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Callable

from events.bus import EventBus, async_publish, get_subscribers, publish, subscribe, unsubscribe
from events.integration import emit, install_webhook_integration

__all__ = [
    "EventBus",
    "publish",
    "subscribe",
    "unsubscribe",
    "async_publish",
    "get_subscribers",
    "emit",
    "install_webhook_integration",
]
