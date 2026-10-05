# SPDX-License-Identifier: Apache-2.0
"""EventBus 实现：同步发布 + 可选异步发布。

设计原则：
- 简单：synchronous publish（handler 同步执行，错误隔离）；
- 零依赖：仅 stdlib（threading + collections）；
- 可扩展：未来可加 EventBusAsync / EventBusRedis 不破坏现有调用。

使用：
    from events import publish, subscribe

    @subscribe("order.created")
    def notify_erp(payload: dict):
        ...

    publish("order.created", {"order_id": 42, "hotel_id": 1})
"""

from __future__ import annotations

import logging
import threading
import traceback
from collections import defaultdict
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

# 一个 handler 的签名：def handler(event: str, payload: dict) -> None
HandlerT = Callable[[str, dict], None]


class EventBus:
    """线程安全的进程内事件总线。"""

    _subscribers: dict[str, list[HandlerT]] = defaultdict(list)
    _lock = threading.RLock()
    # 中间件链（按顺序执行；默认 = [logging_middleware]）
    _middlewares: list[Callable[[str, dict], None]] = []

    @classmethod
    def subscribe(cls, event: str, handler: HandlerT) -> HandlerT:
        """订阅一个事件（可重复；返回 handler 方便装饰器用法）。

        使用：
            EventBus.subscribe("order.created", my_handler)
            # 或装饰器：
            @EventBus.subscribe.register("order.created")
            def my_handler(event, payload): ...
        """
        with cls._lock:
            if handler not in cls._subscribers[event]:
                cls._subscribers[event].append(handler)
        return handler

    @classmethod
    def unsubscribe(cls, event: str, handler: HandlerT) -> bool:
        """取消订阅。返回 True 表示成功移除。"""
        with cls._lock:
            subs = cls._subscribers.get(event, [])
            if handler in subs:
                subs.remove(handler)
                return True
        return False

    @classmethod
    def get_subscribers(cls, event: str) -> list[HandlerT]:
        """调试用：返回某事件的订阅者列表（副本）。"""
        with cls._lock:
            return list(cls._subscribers.get(event, []))

    @classmethod
    def clear(cls) -> None:
        """测试用：清空所有订阅。"""
        with cls._lock:
            cls._subscribers.clear()

    @classmethod
    def publish(cls, event: str, payload: dict | None = None) -> dict:
        """同步发布一个事件（所有 handler 立即执行，错误隔离）。

        返回 ``{"event": ..., "delivered": n, "failed": m, "errors": [...]}``。
        """
        payload = payload or {}
        results = {"event": event, "delivered": 0, "failed": 0, "errors": []}
        # 在锁外取订阅者快照，避免 handler 内 subscribe 死锁
        with cls._lock:
            handlers = list(cls._subscribers.get(event, []))
        for mw in cls._middlewares:
            try:
                mw(event, payload)
            except Exception as e:
                log.warning("EventBus middleware error event=%s err=%s", event, e)
        for handler in handlers:
            try:
                handler(event, payload)
                results["delivered"] += 1
            except Exception as e:
                results["failed"] += 1
                err_msg = f"{type(e).__name__}: {e}"
                results["errors"].append(
                    {
                        "handler": getattr(handler, "__qualname__", str(handler)),
                        "error": err_msg,
                        "tb": traceback.format_exc()[:500],
                    }
                )
                log.warning(
                    "EventBus handler error event=%s handler=%s err=%s",
                    event,
                    getattr(handler, "__qualname__", "?"),
                    err_msg,
                )
        return results

    @classmethod
    def async_publish(cls, event: str, payload: dict | None = None) -> threading.Thread:
        """异步发布：开一个 daemon 线程触发 handlers，调用方立即返回。

        注意：异步线程中 handler 抛异常会被吞掉，只记日志。
        适合 webhook fan-out、邮件通知等"fire-and-forget"场景。
        """

        def _run():
            try:
                cls.publish(event, payload)
            except Exception as e:
                log.warning("EventBus.async_publish crashed event=%s err=%s", event, e)

        t = threading.Thread(target=_run, name=f"event-bus-{event}", daemon=True)
        t.start()
        return t


# 便捷函数（最常用接口）
def publish(event: str, payload: dict | None = None) -> dict:
    return EventBus.publish(event, payload)


def subscribe(event: str) -> Callable[[HandlerT], HandlerT]:
    """装饰器形式的 subscribe：
    @subscribe("order.created")
    def my_handler(event, payload): ...
    """

    def deco(handler: HandlerT) -> HandlerT:
        return EventBus.subscribe(event, handler)

    return deco


def unsubscribe(event: str, handler: HandlerT) -> bool:
    return EventBus.unsubscribe(event, handler)


def async_publish(event: str, payload: dict | None = None) -> threading.Thread:
    return EventBus.async_publish(event, payload)


def get_subscribers(event: str) -> list[HandlerT]:
    return EventBus.get_subscribers(event)
