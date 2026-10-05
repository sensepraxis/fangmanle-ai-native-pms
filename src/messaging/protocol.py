# SPDX-License-Identifier: Apache-2.0
"""私域通道抽象协议（Protocol）。

定义了"一个私域通道"应该提供的能力，**与具体厂商无关**。
业务模块应该面向这个 Protocol 编程，而不是直接 import 某个厂家的 SDK。

当前覆盖能力：
- ``send_text``              — 给客户发文本消息（按 guest_id 或 external_userid）
- ``notify_staff``           — 通知内部员工（保洁派单、管家交接等）
- ``sync_external_contacts`` — 同步外部联系人
- ``create_bind_ticket``     — 渠道码/H5 绑定票据
- ``submit_bind_phone``      — 客人提交手机号完成绑定
- ``enqueue_callback``       — 接收并入队厂家回调
- ``process_callback``       — 处理已入队回调
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PrivateChannel(Protocol):
    """私域通道抽象协议：与具体厂商无关的能力契约。"""

    vendor: str  # 厂商标识，如 "wecom" / "line"

    # ---------- 一对一消息 ----------
    def send_text(
        self,
        *,
        hotel_id: int,
        content: str,
        external_userid: str | None = None,
        guest_id: int | None = None,
        **kwargs: Any,
    ) -> dict:
        """向客户发送一条文本消息。

        实现应至少支持 ``guest_id`` + ``db``，或 ``external_userid`` + ``db``。
        """
        ...

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """向内部员工发送应用/渠道通知（如保洁派单提醒）。"""
        ...

    # ---------- 联系人同步 ----------
    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        """拉取外部联系人档案；返回结构因厂商而异，由实现层标准化。"""
        ...

    # ---------- 渠道码绑定票据 ----------
    def create_bind_ticket(
        self,
        *,
        hotel_id: int,
        external_userid: str | None = None,
        nickname: str | None = None,
        welcome_mode: str = "default",
        **kwargs: Any,
    ) -> dict:
        """创建一条「扫码 → 填写手机号 → 档案绑定」的票据；返回票据及 H5 链接。"""
        ...

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        """客人通过 H5 提交手机号后，通道侧完成档案绑定（事务级）。"""
        ...

    # ---------- 回调处理 ----------
    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        """接收厂商回调（加/删好友、消息回执等），入审计队列。"""
        ...

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        """处理一条已入队的回调（生成券、归档票据等）。"""
        ...
