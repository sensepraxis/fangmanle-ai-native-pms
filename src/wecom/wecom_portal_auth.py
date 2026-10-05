# SPDX-License-Identifier: Apache-2.0
"""客人会员中心专属会话：签名 Cookie + 企微网页授权识别 external_userid。"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.auth_local import JWT_SECRET, _b64url, _b64url_decode

PORTAL_COOKIE = "fml_portal_sess"
PORTAL_TTL_SEC = 90 * 24 * 3600  # 90 天


def issue_portal_session(
    *,
    external_userid: str,
    guest_id: int,
    ticket_token: str,
    ttl_sec: int = PORTAL_TTL_SEC,
) -> str:
    """领券成功后签发；绑定企微外部联系人 ID，防止链接被他人打开。"""
    now = int(time.time())
    payload = {
        "eid": (external_userid or "").strip(),
        "gid": int(guest_id),
        "tt": hashlib.sha256((ticket_token or "").encode("utf-8")).hexdigest()[:16],
        "iat": now,
        "exp": now + int(ttl_sec),
    }
    if not payload["eid"] or not payload["gid"]:
        raise InvalidStateError("无法签发会员中心会话：缺少企微身份或客人")
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(JWT_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_portal_session(raw: str | None) -> dict | None:
    if not raw or "." not in raw:
        return None
    try:
        body, sig = raw.split(".", 1)
    except ValueError:
        return None
    expect = hmac.new(JWT_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        return None
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload


def session_matches_ticket(session: dict | None, *, external_userid: str, guest_id: int, ticket_token: str) -> bool:
    if not session:
        return False
    if str(session.get("eid") or "") != str(external_userid or "").strip():
        return False
    if int(session.get("gid") or 0) != int(guest_id or 0):
        return False
    expect_tt = hashlib.sha256((ticket_token or "").encode("utf-8")).hexdigest()[:16]
    if str(session.get("tt") or "") != expect_tt:
        return False
    return True


def build_wecom_oauth_url(cfg: dict, *, redirect_uri: str, state: str) -> str:
    """企微网页授权：在个人微信打开时可识别外部联系人。"""
    corp_id = str(cfg.get("corp_id") or "").strip()
    agent_id = str(cfg.get("agent_id") or "").strip()
    if not corp_id or not agent_id:
        raise InvalidStateError("未配置 corp_id / agent_id，无法做微信身份校验")
    qs = urllib.parse.urlencode(
        {
            "appid": corp_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_base",
            "agentid": agent_id,
            "state": state,
        }
    )
    return f"https://open.weixin.qq.com/connect/oauth2/authorize?{qs}#wechat_redirect"


def exchange_oauth_identity(cfg: dict, code: str, http_json) -> dict[str, Any]:
    """
    code → 访问用户身份。
    企业成员返回 userid；客户（外部联系人）优先取 external_userid。
    http_json: wecom_service._http_json
    """
    from wecom.wecom_service import get_access_token

    token = get_access_token(cfg)
    qs = urllib.parse.urlencode({"access_token": token, "code": code})
    # 新版 auth/getuserinfo；失败再试旧版 user/getuserinfo
    data = http_json("GET", f"https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo?{qs}")
    err = int(data.get("errcode") or 0)
    if err != 0:
        data = http_json("GET", f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?{qs}")
        err = int(data.get("errcode") or 0)
        if err != 0:
            raise BusinessError(f"企微身份授权失败：{data.get('errmsg') or data}")

    external = data.get("external_userid") or data.get("ExternalUserId") or data.get("external_user_id") or ""
    userid = data.get("userid") or data.get("UserId") or ""
    openid = data.get("openid") or data.get("OpenId") or ""
    return {
        "external_userid": str(external).strip(),
        "userid": str(userid).strip(),
        "openid": str(openid).strip(),
        "raw": data,
    }
