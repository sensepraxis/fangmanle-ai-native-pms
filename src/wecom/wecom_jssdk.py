# SPDX-License-Identifier: Apache-2.0
"""企业微信 JS-SDK 签名（聊天工具栏 sendChatMessage）。"""

from __future__ import annotations

import hashlib
import secrets
import time
import urllib.parse

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from wecom.wecom_service import QYAPI, _http_json, get_access_token, load_wecom_config

_jsapi_ticket_cache: dict = {"ticket": "", "expires_at": 0.0}
_agent_ticket_cache: dict = {"ticket": "", "expires_at": 0.0}


def _sign_ticket(ticket: str, url: str) -> dict:
    nonce = secrets.token_urlsafe(12)
    ts = int(time.time())
    plain = f"jsapi_ticket={ticket}&noncestr={nonce}&timestamp={ts}&url={url}"
    sig = hashlib.sha1(plain.encode("utf-8")).hexdigest()
    return {"timestamp": ts, "nonceStr": nonce, "signature": sig}


def _get_jsapi_ticket(token: str) -> str:
    now = time.time()
    if _jsapi_ticket_cache["ticket"] and _jsapi_ticket_cache["expires_at"] > now + 120:
        return _jsapi_ticket_cache["ticket"]
    qs = urllib.parse.urlencode({"access_token": token})
    data = _http_json("GET", f"{QYAPI}/get_jsapi_ticket?{qs}")
    err = int(data.get("errcode") or 0)
    if err != 0:
        raise BusinessError(f"get_jsapi_ticket 失败：{data.get('errmsg') or data}")
    ticket = str(data.get("ticket") or "")
    if not ticket:
        raise BusinessError("get_jsapi_ticket 未返回 ticket")
    _jsapi_ticket_cache["ticket"] = ticket
    _jsapi_ticket_cache["expires_at"] = now + int(data.get("expires_in") or 7200)
    return ticket


def _get_agent_config_ticket(token: str) -> str:
    now = time.time()
    if _agent_ticket_cache["ticket"] and _agent_ticket_cache["expires_at"] > now + 120:
        return _agent_ticket_cache["ticket"]
    qs = urllib.parse.urlencode({"access_token": token, "type": "agent_config"})
    data = _http_json("GET", f"{QYAPI}/ticket/get?{qs}")
    err = int(data.get("errcode") or 0)
    if err != 0:
        raise BusinessError(f"get agent_config ticket 失败：{data.get('errmsg') or data}")
    ticket = str(data.get("ticket") or "")
    if not ticket:
        raise BusinessError("agent_config ticket 为空")
    _agent_ticket_cache["ticket"] = ticket
    _agent_ticket_cache["expires_at"] = now + int(data.get("expires_in") or 7200)
    return ticket


def build_jssdk_signatures(db, page_url: str) -> dict:
    """返回 ww.register / wx.config 所需 corp 级与 agent 级签名。"""
    cfg = load_wecom_config(db)
    if not cfg.get("enabled", True):
        raise InvalidStateError("企微集成已禁用")
    corp_id = str(cfg.get("corp_id") or "").strip()
    agent_id = str(cfg.get("agent_id") or "").strip()
    if not corp_id or not agent_id:
        raise InvalidStateError("请先配置 corp_id 与 agent_id")

    url = (page_url or "").strip()
    if not url:
        raise ValidationError("缺少 page url")
    # 企微要求：参与签名的 url 不含 # 及后面部分
    url = url.split("#", 1)[0]

    token = get_access_token(cfg)
    corp_ticket = _get_jsapi_ticket(token)
    agent_ticket = _get_agent_config_ticket(token)
    return {
        "corpId": corp_id,
        "agentId": agent_id,
        "url": url,
        "config": _sign_ticket(corp_ticket, url),
        "agent": _sign_ticket(agent_ticket, url),
        "jsApiList": ["getContext", "getCurExternalContact", "sendChatMessage"],
    }
