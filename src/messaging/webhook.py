# SPDX-License-Identifier: Apache-2.0
"""Webhook 通道（对外可订阅事件）。

背景：开源 SaaS 的标配——"对外暴露 webhook"，让第三方系统能订阅 PMS
关键事件（订单创建、券核销、班次交接等）。本模块提供：
- ``WebhookChannel`` 实现 ``messaging.protocol.PrivateChannel`` 协议
- ``WebhookSubscriberRegistry`` —— 第三方注册 webhook URL + event 订阅
- ``dispatch_event(event, payload)`` —— 把事件 fan-out 到所有订阅者

**当前状态（骨架）**：
- 已实现订阅注册 + dispatch POST（用 stdlib urllib，无额外依赖）
- 暂未集成 Event Bus——目前 dispatch_event 只能由代码主动调用
- 未来 Event Bus 上线后，所有 lifecycle 事件自动触发 webhook 投递

**使用示例**（未来 router 侧）：
    from messaging.webhook import WebhookChannel
    wc = WebhookChannel()
    wc.subscribe(event="order.created", url="https://foo.com/hook", secret="...")
    # 在订单创建处：
    wc.dispatch_event("order.created", {"order_id": 42, "hotel_id": 1})
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from messaging.protocol import PrivateChannel


@dataclass
class WebhookSubscriber:
    event: str  # 事件名（如 "order.created"）
    url: str  # 订阅方 webhook URL
    secret: str = ""  # HMAC 签名用（可选）
    active: bool = True
    # 重试
    max_retries: int = 3
    # 失败回看（最近一次投递状态）
    last_status: int | None = None
    last_error: str | None = None
    delivered_count: int = 0


class WebhookSubscriberRegistry:
    """Webhook 订阅方注册表（in-memory + DB-backed 即将支持）。"""

    _subscribers: dict[str, list[WebhookSubscriber]] = {}
    _lock = threading.Lock()

    @classmethod
    def subscribe(cls, event: str, url: str, secret: str = "", max_retries: int = 3) -> WebhookSubscriber:
        sub = WebhookSubscriber(event=event, url=url, secret=secret, max_retries=max_retries)
        with cls._lock:
            cls._subscribers.setdefault(event, []).append(sub)
        return sub

    @classmethod
    def unsubscribe(cls, event: str, url: str) -> bool:
        """按 url 取消订阅（用于管理 API）。"""
        with cls._lock:
            subs = cls._subscribers.get(event, [])
            before = len(subs)
            cls._subscribers[event] = [s for s in subs if s.url != url]
            return len(cls._subscribers[event]) < before

    @classmethod
    def list_subscribers(cls, event: str | None = None) -> list[WebhookSubscriber]:
        if event is None:
            out = []
            for subs in cls._subscribers.values():
                out.extend(subs)
            return out
        return list(cls._subscribers.get(event, []))

    @classmethod
    def clear(cls) -> None:
        """测试用：清空所有订阅。"""
        with cls._lock:
            cls._subscribers.clear()


def _sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 签名（订阅方可用 'X-Fml-Signature' 验证来源）。"""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class WebhookChannel(PrivateChannel):
    """对外可订阅事件的 webhook 通道。"""

    vendor = "webhook"

    # ---------- PrivateChannel 协议占位 ----------
    # webhook 通道不直接实现 send_text 等私域方法；
    # 但实现 Protocol 以便 messaging.factory 注册（让 ISV 可选 webhook 作回执通道）。
    def send_text(
        self,
        *,
        hotel_id: int,
        content: str,
        external_userid: str | None = None,
        guest_id: int | None = None,
        **kwargs: Any,
    ) -> dict:
        # webhook 不直接"发文本"，而是把"发文本"事件 fan-out 给订阅方
        return self.dispatch_event(
            "text_message_sent",
            {
                "hotel_id": hotel_id,
                "external_userid": external_userid,
                "guest_id": guest_id,
                "content": content,
            },
        )

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        return self.dispatch_event(
            "staff_notified",
            {"hotel_id": hotel_id, "userid": userid, "content": content},
        )

    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        return self.dispatch_event("contacts_synced", {"hotel_id": hotel_id})

    def create_bind_ticket(
        self,
        *,
        hotel_id: int,
        external_userid: str | None = None,
        nickname: str | None = None,
        welcome_mode: str = "default",
        **kwargs: Any,
    ) -> dict:
        return self.dispatch_event(
            "bind_ticket_created",
            {
                "hotel_id": hotel_id,
                "external_userid": external_userid,
                "nickname": nickname,
                "welcome_mode": welcome_mode,
            },
        )

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        return self.dispatch_event("bind_phone_submitted", {"token": token, "phone": phone})

    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        return self.dispatch_event("callback_enqueued", {"payload": payload})

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        return self.dispatch_event("callback_processed", {"event_id": event_id})

    # ---------- Webhook 特有 ----------
    def subscribe(self, event: str, url: str, secret: str = "", max_retries: int = 3) -> WebhookSubscriber:
        """注册一个新的 webhook 订阅。"""
        return WebhookSubscriberRegistry.subscribe(event, url, secret, max_retries)

    def unsubscribe(self, event: str, url: str) -> bool:
        return WebhookSubscriberRegistry.unsubscribe(event, url)

    def list_subscribers(self, event: str | None = None) -> list[WebhookSubscriber]:
        return WebhookSubscriberRegistry.list_subscribers(event)

    def dispatch_event(self, event: str, payload: dict) -> dict:
        """把事件 fan-out 到所有订阅方（每个订阅方 POST 一次，HMAC 签名）。

        返回 ``{"event": ..., "delivered": n, "failed": m}`` 摘要。
        """
        import json as _json

        body = _json.dumps({"event": event, "payload": payload}, ensure_ascii=False).encode("utf-8")
        results = {"event": event, "delivered": 0, "failed": 0, "errors": []}

        for sub in WebhookSubscriberRegistry.list_subscribers(event):
            if not sub.active:
                continue
            headers = {"Content-Type": "application/json"}
            if sub.secret:
                headers["X-Fml-Signature"] = _sign(sub.secret, body)
            req = urllib.request.Request(sub.url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    sub.last_status = resp.status
                    sub.last_error = None
                    sub.delivered_count += 1
                    if 200 <= resp.status < 300:
                        results["delivered"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({"url": sub.url, "status": resp.status})
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                sub.last_status = None
                sub.last_error = str(e)
                results["failed"] += 1
                results["errors"].append({"url": sub.url, "error": str(e)})

        return results


__all__ = [
    "WebhookChannel",
    "WebhookSubscriber",
    "WebhookSubscriberRegistry",
]
