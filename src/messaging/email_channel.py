# SPDX-License-Identifier: Apache-2.0
"""Email 兜底通道（欧美酒店常用）。

骨架实现：记录发送意图；生产可接 SMTP / SendGrid。
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class EmailChannel:
    vendor = "email"

    def send_text(
        self,
        *,
        hotel_id: int,
        content: str,
        external_userid: str | None = None,
        guest_id: int | None = None,
        **kwargs: Any,
    ) -> dict:
        to = (external_userid or kwargs.get("email") or "").strip()
        db = kwargs.get("db")
        if not to and guest_id and db is not None:
            try:
                from models import Guest

                g = db.query(Guest).filter_by(id=int(guest_id)).first()
                to = str(getattr(g, "email", None) or "")
            except Exception:
                to = ""
        log.info(
            "[EmailChannel] demo send hotel=%s guest=%s to=%s len=%s",
            hotel_id,
            guest_id,
            to or "-",
            len(content or ""),
        )
        return {
            "ok": True,
            "vendor": "email",
            "demo": True,
            "guest_id": guest_id,
            "email": to or None,
            "note": "Email provider 未接入，已记录发送意图（demo）",
        }

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        log.info("[EmailChannel] notify_staff hotel=%s %s", hotel_id, (content or "")[:120])
        return {"ok": True, "vendor": "email", "demo": True, "userid": userid}

    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "email", "synced": 0, "note": "Email 无联系人同步"}

    def create_bind_ticket(self, *, hotel_id: int, **kwargs: Any) -> dict:
        return {"ok": False, "vendor": "email", "note": "Email 不提供扫码绑定票"}

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        return {"ok": False, "vendor": "email", "token": token, "phone": phone}

    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "email", "queued": False}

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "email", "event_id": event_id}


__all__ = ["EmailChannel"]
