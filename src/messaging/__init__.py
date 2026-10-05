# SPDX-License-Identifier: Apache-2.0
"""私域通道门面（messaging facade）。

背景：原 ``wecom/`` 包是企业微信协议的实现，被业务模块当通用 helper import，
**业务模块不该感知具体通道**（企业微信 / Line / WhatsApp / Telegram）。
本包以 Protocol 接口形式定义"私域通道"的能力契约，并按当前租户配置
（AppSetting 中 ``private_channel.vendor``，当前默认 wecom）路由到具体实现。

使用：
    from messaging import get_channel, send_text, sync_external_contacts, ...

    ch = get_channel()
    ch.send_text(hotel_id=1, content="你好", guest_id=42, db=db)

    # 或走模块级便捷函数（内部同样 get_channel）
    send_text(hotel_id=1, content="你好", guest_id=42, db=db)

约定：
- Protocol 方法签名尽量保持与底层 SDK 一致，命名用业务语义
  （send_text / notify_staff / sync_external_contacts / bind / callback）。
- 委派实现内部 import wecom_service / line 等；不动原 wecom_service。
- 企微专属能力（JS-SDK、加解密、配置页）仍留在 ``wecom/``，不经本门面。
"""

from __future__ import annotations

from typing import Any

from messaging.factory import (
    current_vendor,
    get_channel,
    get_fallback_channels,
    reset_channel_cache,
)
from messaging.protocol import PrivateChannel


def send_text(
    *,
    hotel_id: int,
    content: str,
    external_userid: str | None = None,
    guest_id: int | None = None,
    **kwargs: Any,
) -> dict:
    return get_channel().send_text(
        hotel_id=hotel_id,
        content=content,
        external_userid=external_userid,
        guest_id=guest_id,
        **kwargs,
    )


def notify_staff(
    *,
    hotel_id: int,
    content: str,
    userid: str | None = None,
    **kwargs: Any,
) -> dict:
    return get_channel().notify_staff(
        hotel_id=hotel_id,
        content=content,
        userid=userid,
        **kwargs,
    )


def sync_external_contacts(hotel_id: int, **kwargs: Any) -> dict:
    return get_channel().sync_external_contacts(hotel_id, **kwargs)


def create_bind_ticket(
    *,
    hotel_id: int,
    external_userid: str | None = None,
    nickname: str | None = None,
    welcome_mode: str = "default",
    **kwargs: Any,
) -> dict:
    return get_channel().create_bind_ticket(
        hotel_id=hotel_id,
        external_userid=external_userid,
        nickname=nickname,
        welcome_mode=welcome_mode,
        **kwargs,
    )


def submit_bind_phone(token: str, phone: str, **kwargs: Any) -> dict:
    return get_channel().submit_bind_phone(token, phone, **kwargs)


def enqueue_callback(payload: dict, **kwargs: Any) -> dict:
    return get_channel().enqueue_callback(payload, **kwargs)


def process_callback(event_id: int, **kwargs: Any) -> dict:
    return get_channel().process_callback(event_id, **kwargs)


__all__ = [
    "PrivateChannel",
    "get_channel",
    "get_fallback_channels",
    "current_vendor",
    "reset_channel_cache",
    "send_text",
    "notify_staff",
    "sync_external_contacts",
    "create_bind_ticket",
    "submit_bind_phone",
    "enqueue_callback",
    "process_callback",
]
