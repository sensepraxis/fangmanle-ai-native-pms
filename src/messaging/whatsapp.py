# SPDX-License-Identifier: Apache-2.0
"""WhatsApp Cloud API 私域通道（海外酒店主通道之一）。

- 配置了 WHATSAPP_ACCESS_TOKEN + phone_number_id（或 AppSetting）时走 Cloud API
- 未配密钥时 demo 模式：写日志并返回 ok，不阻断看板 / 发券流程
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from domain import ValidationError

log = logging.getLogger(__name__)


def _wa_cfg(db=None) -> dict[str, str]:
    token = (os.environ.get("WHATSAPP_ACCESS_TOKEN") or "").strip()
    phone_id = (os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    if db is not None:
        try:
            from infra.private_channel import load_private_channel_config

            cfg = load_private_channel_config(db) or {}
            wa = cfg.get("whatsapp") if isinstance(cfg.get("whatsapp"), dict) else {}
            token = token or str(wa.get("access_token") or "").strip()
            phone_id = phone_id or str(wa.get("phone_number_id") or "").strip()
        except Exception:
            pass
    return {"access_token": token, "phone_number_id": phone_id}


def _push_wa_text(token: str, phone_number_id: str, to: str, text: str) -> dict:
    body = json.dumps(
        {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"body": (text or "")[:4096]},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode() or "{}"
            return {
                "ok": True,
                "vendor": "whatsapp",
                "http_status": resp.status,
                "body": json.loads(raw),
            }
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise ValidationError(f"WhatsApp API 错误 {e.code}: {detail[:300]}") from e


class WhatsappChannel:
    vendor = "whatsapp"

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
        cfg = _wa_cfg(db)
        token, phone_id = cfg["access_token"], cfg["phone_number_id"]
        to = (external_userid or "").strip()
        if not to and guest_id and db is not None:
            from models import GuestIdentity

            ident = (
                db.query(GuestIdentity)
                .filter_by(guest_id=int(guest_id), source="whatsapp")
                .order_by(GuestIdentity.linked_at.desc())
                .first()
            )
            if ident:
                to = str(ident.external_id or "")
        if token and phone_id and to:
            return _push_wa_text(token, phone_id, to, content or "")
        log.info(
            "[WhatsappChannel] demo send_text hotel=%s guest=%s to=%s len=%s",
            hotel_id,
            guest_id,
            to or "-",
            len(content or ""),
        )
        return {
            "ok": True,
            "vendor": "whatsapp",
            "demo": True,
            "queued": False,
            "note": "WhatsApp token 未配置，已按 demo 模式记录（未实际上送）",
            "guest_id": guest_id,
            "external_userid": to or None,
        }

    def notify_staff(
        self,
        *,
        hotel_id: int,
        content: str,
        userid: str | None = None,
        **kwargs: Any,
    ) -> dict:
        log.info(
            "[WhatsappChannel] notify_staff hotel=%s user=%s %s",
            hotel_id,
            userid,
            (content or "")[:120],
        )
        return {"ok": True, "vendor": "whatsapp", "demo": True, "userid": userid}

    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        return {
            "ok": True,
            "vendor": "whatsapp",
            "synced": 0,
            "note": "WhatsApp 无企微式外部联系人全量同步；请用 opt-in / 绑定沉淀身份",
        }

    def create_bind_ticket(
        self,
        *,
        hotel_id: int,
        external_userid: str | None = None,
        nickname: str | None = None,
        welcome_mode: str = "default",
        **kwargs: Any,
    ) -> dict:
        base = (kwargs.get("public_base_url") or "").rstrip("/") or ""
        token = f"wa-demo-{hotel_id}-{(external_userid or 'guest')[:16]}"
        return {
            "ok": True,
            "vendor": "whatsapp",
            "demo": True,
            "token": token,
            "bind_url": f"{base}/private/bind?t={token}" if base else f"/private/bind?t={token}",
            "external_userid": external_userid,
            "nickname": nickname,
            "welcome_mode": welcome_mode,
        }

    def submit_bind_phone(self, token: str, phone: str, **kwargs: Any) -> dict:
        return {
            "ok": True,
            "vendor": "whatsapp",
            "demo": True,
            "token": token,
            "phone": phone,
            "note": "demo 绑定：接 WhatsApp opt-in 后写入 GuestIdentity(source=whatsapp)",
        }

    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        return {
            "ok": True,
            "vendor": "whatsapp",
            "queued": True,
            "payload_keys": list((payload or {}).keys()),
        }

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "whatsapp", "event_id": event_id, "demo": True}


__all__ = ["WhatsappChannel"]
