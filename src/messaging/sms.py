# SPDX-License-Identifier: Apache-2.0
"""SMS 兜底通道（国际私域几乎必开）。

当前为可插拔骨架：记录发送意图；配置 Twilio 等后可替换为真实 API。
不作为 primary IM，仅作 fallback。
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class SmsChannel:
    vendor = "sms"

    def send_text(
        self,
        *,
        hotel_id: int,
        content: str,
        external_userid: str | None = None,
        guest_id: int | None = None,
        **kwargs: Any,
    ) -> dict:
        to = (external_userid or kwargs.get("phone") or "").strip()
        db = kwargs.get("db")
        if not to and guest_id and db is not None:
            try:
                from models import Guest

                g = db.query(Guest).filter_by(id=int(guest_id)).first()
                to = str(getattr(g, "phone", None) or getattr(g, "mobile", None) or "")
            except Exception:
                to = ""
        log.info(
            "[SmsChannel] demo send hotel=%s guest=%s to=%s len=%s",
            hotel_id,
            guest_id,
            to or "-",
            len(content or ""),
        )
        return {
            "ok": True,
            "vendor": "sms",
            "demo": True,
            "guest_id": guest_id,
            "phone": to or None,
            "note": "SMS provider 未接入，已记录发送意图（demo）",
        }

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        log.info("[SmsChannel] notify_staff hotel=%s %s", hotel_id, (content or "")[:120])
        return {"ok": True, "vendor": "sms", "demo": True, "userid": userid}

    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "sms", "synced": 0, "note": "SMS 无联系人同步"}

    def create_bind_ticket(self, *, hotel_id: int, **kwargs: Any) -> dict:
        return {"ok": False, "vendor": "sms", "note": "SMS 不提供扫码绑定票"}

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        return {"ok": False, "vendor": "sms", "token": token, "phone": phone}

    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "sms", "queued": False}

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "sms", "event_id": event_id}


__all__ = ["SmsChannel"]
