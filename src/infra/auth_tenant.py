# SPDX-License-Identifier: Apache-2.0
"""多租户鉴权：凭证哈希、签名 Token、租户上下文。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from infra.auth_local import JWT_SECRET_DEFAULT, hash_password, verify_password
from models import Hotel, Tenant, TenantCredential

JWT_SECRET = os.environ.get("FML_JWT_SECRET") or JWT_SECRET_DEFAULT
TOKEN_TTL_HOURS = int(os.environ.get("FML_TOKEN_TTL_HOURS", "12"))


def hash_secret(secret: str) -> str:
    return hash_password(secret)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_token(*, tenant_id: int, hotel_id: int, client_id: str, hours: int = TOKEN_TTL_HOURS) -> str:
    now = datetime.utcnow()
    payload = {
        "tenant_id": tenant_id,
        "hotel_id": hotel_id,
        "client_id": client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(JWT_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_token(token: str) -> dict:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        raise AuthenticationError("无效的访问令牌")
    expect = hmac.new(JWT_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        raise AuthenticationError("访问令牌签名校验失败")
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception:
        raise AuthenticationError("访问令牌无法解析")
    if int(payload.get("exp") or 0) < int(datetime.utcnow().timestamp()):
        raise AuthenticationError("访问令牌已过期，请重新登录")
    return payload


@dataclass
class TenantContext:
    tenant_id: int
    hotel_id: int
    tenant_code: str
    hotel_name: str
    client_id: str


def _tenant_window_ok(t: Tenant, now: datetime) -> bool:
    if t.status != "active":
        return False
    if t.valid_from and now < t.valid_from:
        return False
    if t.valid_until and now > t.valid_until:
        return False
    return True


def _cred_window_ok(c: TenantCredential, now: datetime) -> bool:
    if not c.is_active:
        return False
    if c.valid_from and now < c.valid_from:
        return False
    if c.valid_until and now > c.valid_until:
        return False
    return True


def authenticate_credential(db: Session, client_id: str, client_secret: str) -> TenantContext:
    now = datetime.utcnow()
    cred = db.query(TenantCredential).filter_by(client_id=client_id).first()
    if not cred:
        raise AuthenticationError("client_id 或密钥错误")
    if not verify_password(client_secret, cred.client_secret_hash):
        raise AuthenticationError("client_id 或密钥错误")
    if not _cred_window_ok(cred, now):
        raise AuthorizationError("租户凭证已过期或未生效")
    tenant = db.get(Tenant, cred.tenant_id)
    if not tenant or not _tenant_window_ok(tenant, now):
        raise AuthorizationError("租户订阅已过期或未激活")
    hotel = db.query(Hotel).filter_by(tenant_id=tenant.id).first()
    if not hotel:
        raise BusinessError("租户未绑定酒店")
    return TenantContext(
        tenant_id=tenant.id,
        hotel_id=hotel.id,
        tenant_code=tenant.code,
        hotel_name=hotel.name,
        client_id=cred.client_id,
    )


def get_tenant_ctx(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> TenantContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("未登录：请先使用租户凭证登录")
    token = authorization.split(" ", 1)[1].strip()
    payload = parse_token(token)
    tenant_id = int(payload["tenant_id"])
    hotel_id = int(payload["hotel_id"])
    now = datetime.utcnow()
    tenant = db.get(Tenant, tenant_id)
    if not tenant or not _tenant_window_ok(tenant, now):
        raise AuthorizationError("租户订阅已过期或未激活")
    hotel = db.get(Hotel, hotel_id)
    if not hotel or hotel.tenant_id != tenant_id:
        raise AuthorizationError("令牌与酒店租户不匹配")
    return TenantContext(
        tenant_id=tenant_id,
        hotel_id=hotel_id,
        tenant_code=tenant.code,
        hotel_name=hotel.name,
        client_id=str(payload.get("client_id") or ""),
    )


def resolve_hotel_id(ctx: TenantContext, hotel_id: Optional[int] = None) -> int:
    """业务 API：禁止跨租户传入他人 hotel_id。"""
    if hotel_id is not None and int(hotel_id) != int(ctx.hotel_id):
        raise AuthorizationError("跨租户访问被拒绝")
    return ctx.hotel_id
