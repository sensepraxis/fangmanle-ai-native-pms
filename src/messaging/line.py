# SPDX-License-Identifier: Apache-2.0
"""LINE 私域通道：最小可用实现（海外酒店默认选型）。

- 配置了 LINE_CHANNEL_ACCESS_TOKEN / AppSetting.private_channel.line 时走 Messaging API 推送
- 未配密钥时进入 demo 模式：写审计日志并返回 ok，不抛错（便于海外 demo 跑通看板）
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


def _line_token(db=None) -> str:
    env = (os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if env:
        return env
    if db is not None:
        try:
            from infra.private_channel import load_private_channel_config

            cfg = load_private_channel_config(db) or {}
            line = cfg.get("line") if isinstance(cfg.get("line"), dict) else {}
            return str(line.get("channel_access_token") or "").strip()
        except Exception:
            return ""
    return ""


def _push_line_text(token: str, to: str, text: str) -> dict:
    body = json.dumps(
        {"to": to, "messages": [{"type": "text", "text": text[:5000]}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
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
            return {"ok": True, "vendor": "line", "http_status": resp.status, "body": json.loads(raw)}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise ValidationError(f"LINE API 错误 {e.code}: {detail[:300]}") from e


class LineChannel:
    vendor = "line"

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
        token = _line_token(db)
        to = (external_userid or "").strip()
        if not to and guest_id and db is not None:
            from models import GuestIdentity

            ident = (
                db.query(GuestIdentity)
                .filter_by(guest_id=int(guest_id), source="line")
                .order_by(GuestIdentity.linked_at.desc())
                .first()
            )
            if ident:
                to = str(ident.external_id or "")
        if token and to:
            return _push_line_text(token, to, content or "")
        # demo / 未配密钥：不阻断业务流程
        log.info(
            "[LineChannel] demo send_text hotel=%s guest=%s to=%s len=%s",
            hotel_id,
            guest_id,
            to or "-",
            len(content or ""),
        )
        return {
            "ok": True,
            "vendor": "line",
            "demo": True,
            "queued": False,
            "note": "LINE token 未配置，已按 demo 模式记录（未实际上送）",
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
        # LINE 无统一员工应用消息；记日志即可
        log.info("[LineChannel] notify_staff hotel=%s user=%s %s", hotel_id, userid, (content or "")[:120])
        return {"ok": True, "vendor": "line", "demo": True, "userid": userid}

    def sync_external_contacts(self, hotel_id: int, **kwargs: Any) -> dict:
        return {
            "ok": True,
            "vendor": "line",
            "synced": 0,
            "note": "LINE OA 不提供企微式外部联系人全量同步；请用 LINE Login / 扫码绑定沉淀身份",
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
        # 复用绑定票表结构时由上层 wecom_service 承担；此处返回可配置的 H5 占位
        base = (kwargs.get("public_base_url") or "").rstrip("/") or ""
        token = f"line-demo-{hotel_id}-{(external_userid or 'guest')[:16]}"
        return {
            "ok": True,
            "vendor": "line",
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
            "vendor": "line",
            "demo": True,
            "token": token,
            "phone": phone,
            "note": "demo 绑定：接 LINE Login 后写入 GuestIdentity(source=line)",
        }

    def enqueue_callback(self, payload: dict, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "line", "queued": True, "payload_keys": list((payload or {}).keys())}

    def process_callback(self, event_id: int, **kwargs: Any) -> dict:
        return {"ok": True, "vendor": "line", "event_id": event_id, "demo": True}


__all__ = ["LineChannel"]
