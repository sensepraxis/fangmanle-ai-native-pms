# SPDX-License-Identifier: Apache-2.0
"""企业微信通道实现：把 wecom_service 的协议层能力包装成 PrivateChannel。

**不复制业务代码**，内部委托给 wecom.wecom_service 现有函数——确保两边行为
始终一致；业务入口应通过 ``messaging.get_channel()`` 调用本适配器。
"""

from __future__ import annotations

from typing import Any

from domain import ValidationError


class WecomChannel:
    vendor = "wecom"

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
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.send_text 需要 kwargs['db']")
        if guest_id is None:
            raise ValidationError("wecom.send_text 需要 guest_id（企微一对一发消息按客人身份解析）")
        from wecom.wecom_service import send_single_message

        _ = external_userid  # 由 send_single_message 内部按 guest 身份解析
        return send_single_message(db, hotel_id, int(guest_id), content)

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """向企业内部成员发送应用文本消息。"""
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.notify_staff 需要 kwargs['db']")
        from wecom.wecom_service import (
            _send_agent_text_message,
            get_access_token,
            load_wecom_config,
        )

        cfg = load_wecom_config(db)
        if not cfg.get("enabled", True):
            return {"pushed": False, "hint": "企微未启用", "hotel_id": hotel_id}
        touser = (userid or "").strip() or (cfg.get("follow_userid") or "").strip()
        if not touser:
            return {"pushed": False, "hint": "无企微 userid", "hotel_id": hotel_id}
        token = get_access_token(cfg)
        data = _send_agent_text_message(cfg, token, str(touser), content)
        err = int(data.get("errcode") or 0)
        return {
            "pushed": err == 0,
            "touser": touser,
            "hotel_id": hotel_id,
            "hint": None if err == 0 else str(data.get("errmsg") or data)[:120],
            "raw": data,
        }

    # ---------- 联系人同步 ----------
    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.sync_external_contacts 需要 kwargs['db']")
        from wecom.wecom_service import sync_external_contacts

        return sync_external_contacts(db, hotel_id)

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
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.create_bind_ticket 需要 kwargs['db']")
        eid = (external_userid or "").strip()
        if not eid:
            raise ValidationError("wecom.create_bind_ticket 需要 external_userid")
        from wecom.wecom_service import create_bind_ticket, load_wecom_config

        cfg = load_wecom_config(db)
        follow = (kwargs.get("follow_userid") or cfg.get("follow_userid") or "").strip()
        ticket = create_bind_ticket(
            db,
            hotel_id=hotel_id,
            external_userid=eid,
            follow_userid=follow,
            nickname=nickname or "",
            state=kwargs.get("state") or "lobby",
        )
        _ = welcome_mode
        return {
            "id": ticket.id,
            "token": ticket.token,
            "hotel_id": ticket.hotel_id,
            "external_userid": ticket.external_userid,
            "status": ticket.status,
            "vendor": self.vendor,
        }

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.submit_bind_phone 需要 kwargs['db']")
        from wecom.wecom_service import submit_bind_phone as _submit

        return _submit(db, token, phone)

    # ---------- 回调处理 ----------
    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        db = kwargs.get("db")
        hotel_id = kwargs.get("hotel_id")
        if db is None:
            raise ValidationError("wecom.enqueue_callback 需要 kwargs['db']")
        if hotel_id is None:
            raise ValidationError("wecom.enqueue_callback 需要 kwargs['hotel_id']")
        from wecom.wecom_service import enqueue_wecom_callback

        row = enqueue_wecom_callback(db, hotel_id=int(hotel_id), event=payload or {})
        if row is None:
            return {"ok": True, "skipped": True}
        return {
            "ok": True,
            "event_id": row.id,
            "status": row.status,
            "change_type": row.change_type,
        }

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        db = kwargs.get("db")
        if db is None:
            raise ValidationError("wecom.process_callback 需要 kwargs['db']")
        from wecom.wecom_service import process_wecom_callback_event

        return process_wecom_callback_event(db, event_id)


__all__ = ["WecomChannel"]
