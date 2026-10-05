# SPDX-License-Identifier: Apache-2.0
"""Event Bus 与现有组件的集成点。

本模块负责把 Event Bus 与 WebHook Channel、Plugin 系统等"出口"接上：
- ``install_webhook_integration()`` —— 让 WebHook Channel 订阅所有 lifecycle 事件，
  第三方只需配置 webhook URL 就能自动接收。

**集成调用方**：
- 在 app 启动时调用一次 ``install_webhook_integration()``；
- 在 router / 服务需要的地方手动 ``publish("event.name", payload)``。
"""

from __future__ import annotations

import logging
from typing import Optional

from events.bus import publish, subscribe

log = logging.getLogger(__name__)


# Event Bus → WebHook Channel 桥接：所有 lifecycle 事件自动 fan-out 到订阅方
_BRIDGE_INSTALLED = False


def install_webhook_integration() -> None:
    """把 messaging.WebhookChannel 接上 Event Bus：所有 publish 都会 fan-out webhook。

    只需要启动时调一次。
    """
    global _BRIDGE_INSTALLED
    if _BRIDGE_INSTALLED:
        return
    try:
        from messaging.webhook import WebhookChannel, WebhookSubscriberRegistry
    except ImportError as e:
        log.warning("install_webhook_integration: messaging.webhook 不可用: %s", e)
        return

    bridge = _WebhookBridge(WebhookChannel())
    # 当前阶段：订阅所有典型 lifecycle 事件（新增事件只需加一行）
    for event in [
        "order.created",
        "order.cancelled",
        "guest.checked_in",
        "guest.checked_out",
        "payment.settled",
        "refund.succeeded",
        "coupon.redeemed",
        "deposit.created",
        "deposit.captured",
        "deposit.released",
        "room.status_changed",
        "hk.task_completed",
        "hk.task_assigned",
        "hk.batch_dispatched",
        "shift.handover_completed",
        "wecom.friend_added",
        "night_audit.completed",
    ]:
        subscribe(event)(bridge.on_event)
    _BRIDGE_INSTALLED = True
    log.info("EventBus ↔ WebHookChannel bridge installed (%d lifecycle events)", 17)


class _WebhookBridge:
    """把 EventBus payload 投递给所有 WebHook 订阅方。"""

    def __init__(self, channel) -> None:
        self._channel = channel

    def on_event(self, event: str, payload: dict) -> None:
        # WebHookChannel.dispatch_event 已经做 fan-out，直接调用
        try:
            self._channel.dispatch_event(event, payload)
        except Exception as e:  # 永不抛出，避免污染 publish 链路
            log.warning("webhook bridge failed event=%s err=%s", event, e)


# 业务埋点 helper：统一 publish 调用（带异常隔离，避免埋点错误拖垮业务）
def emit(event: str, payload: dict | None = None) -> None:
    """业务代码统一的 publish helper：失败不抛，只记日志。

    使用：
        from events import emit
        emit("order.created", {"order_id": o.id, "hotel_id": o.hotel_id})
    """
    try:
        publish(event, payload or {})
    except Exception as e:
        log.warning("events.emit failed event=%s err=%s", event, e)
