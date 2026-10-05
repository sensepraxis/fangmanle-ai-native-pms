# SPDX-License-Identifier: Apache-2.0
"""私域通道工厂：按配置选择 primary / fallback vendor。

primary：wecom / line / whatsapp / webhook
fallback：sms / email（及 webhook）— 见 ``infra.private_channel.resolve_fallback``
"""

from __future__ import annotations

from typing import Optional

from messaging.protocol import PrivateChannel

_channel_cache: dict[str, PrivateChannel] = {}


def current_vendor() -> str:
    """返回当前激活的主私域通道厂商标识。"""
    from infra.private_channel import resolve_vendor

    return resolve_vendor()


def _build_channel(name: str) -> PrivateChannel:
    if name == "wecom":
        from messaging.wecom import WecomChannel

        return WecomChannel()
    if name == "line":
        from messaging.line import LineChannel

        return LineChannel()
    if name == "whatsapp":
        from messaging.whatsapp import WhatsappChannel

        return WhatsappChannel()
    if name == "webhook":
        from messaging.webhook import WebhookChannel

        return WebhookChannel()
    if name == "sms":
        from messaging.sms import SmsChannel

        return SmsChannel()
    if name == "email":
        from messaging.email_channel import EmailChannel

        return EmailChannel()
    raise ValueError(f"不支持的私域通道 vendor: {name}")


def get_channel(vendor: Optional[str] = None) -> PrivateChannel:
    """根据 vendor 名称获取对应通道实例（带缓存）。"""
    from infra.private_channel import resolve_vendor

    name = resolve_vendor(vendor)
    if name in _channel_cache:
        return _channel_cache[name]
    inst = _build_channel(name)
    _channel_cache[name] = inst
    return inst


def get_fallback_channels() -> list[PrivateChannel]:
    from infra.private_channel import resolve_fallback

    out: list[PrivateChannel] = []
    for name in resolve_fallback():
        if name in _channel_cache:
            out.append(_channel_cache[name])
            continue
        try:
            inst = _build_channel(name)
        except ValueError:
            continue
        _channel_cache[name] = inst
        out.append(inst)
    return out


def reset_channel_cache() -> None:
    """测试用：清空通道缓存，强制下次重新构造。"""
    _channel_cache.clear()


__all__ = [
    "get_channel",
    "get_fallback_channels",
    "current_vendor",
    "reset_channel_cache",
]
