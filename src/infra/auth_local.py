# SPDX-License-Identifier: Apache-2.0
"""单体酒店本地鉴权：用户名密码 + 签名 Token + RBAC scopes。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from models import Hotel, Role, User

# 与 docker-compose 演示默认值对齐；生产必须改成随机值。
JWT_SECRET_DEFAULT = "please-change-this-jwt-secret"
JWT_SECRET = os.environ.get("FML_JWT_SECRET") or JWT_SECRET_DEFAULT
TOKEN_TTL_HOURS = int(os.environ.get("FML_TOKEN_TTL_HOURS", "24"))
DEFAULT_HOTEL_ID = int(os.environ.get("FML_DEFAULT_HOTEL_ID", "1"))
SKIP_AUTH = os.environ.get("FML_SKIP_AUTH", "").lower() in ("1", "true", "yes")
_PBKDF2_ITERS = int(os.environ.get("FML_PBKDF2_ITERATIONS") or "120000")
_PBKDF2_SCHEME = "pbkdf2_sha256"

# 旧角色码兼容（勿收录可被自定义角色占用的短码，如 hk/fin）
ROLE_ALIASES = {
    "mgr": "gm",
    "manager": "gm",
    "store": "gm",
    "housekeeping": "fd",
    "finance": "gm",
    "boss": "gm",
    "owner": "gm",
}


def normalize_role(code: str) -> str:
    c = (code or "").strip().lower()
    return ROLE_ALIASES.get(c, c)


def jwt_uses_demo_secret() -> bool:
    return JWT_SECRET == JWT_SECRET_DEFAULT


def hash_password(password: str) -> str:
    """加盐 PBKDF2-SHA256。旧库里的裸 SHA-256 hex 仍可由 verify_password 校验。"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERS)
    return f"{_PBKDF2_SCHEME}${_PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    if stored.startswith(_PBKDF2_SCHEME + "$"):
        try:
            _, iters_s, salt_hex, dk_hex = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iters_s),
            )
            return hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def password_needs_rehash(stored: str | None) -> bool:
    return bool(stored) and not stored.startswith(_PBKDF2_SCHEME + "$")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_token(*, user_id: int, hotel_id: int, username: str, role: str = "", hours: int = TOKEN_TTL_HOURS) -> str:
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "hotel_id": hotel_id,
        "username": username,
        "role": normalize_role(role),
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
class AppContext:
    user_id: int
    hotel_id: int
    username: str
    role: str
    full_name: str
    hotel_name: str
    menus: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=frozenset)

    def can(self, *codes: str) -> bool:
        if self.role == "admin":
            return True
        have = self.menus | self.scopes
        return all(c in have for c in codes)


def get_hotel_id() -> int:
    """单体部署：固定返回本店 hotel_id。"""
    return DEFAULT_HOTEL_ID


def assert_hotel_access(hotel_id: Optional[int]) -> int:
    """校验资源归属本店。"""
    hid = get_hotel_id()
    if hotel_id is not None and int(hotel_id) != hid:
        raise AuthorizationError("无权访问该资源")
    return hid


def _attach_rbac(db: Session, ctx: AppContext) -> AppContext:
    from infra.rbac_service import get_role_permission_sets

    menus, actions = get_role_permission_sets(db, ctx.role)
    ctx.menus = menus
    ctx.scopes = actions
    return ctx


def authenticate_user(db: Session, username: str, password: str) -> AppContext:
    user = db.query(User).filter_by(username=username.strip()).first()
    if not user or not user.is_active:
        raise AuthenticationError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("用户名或密码错误")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()
    hotel = db.get(Hotel, user.hotel_id or DEFAULT_HOTEL_ID)
    if not hotel:
        raise BusinessError("酒店配置缺失")
    role = db.get(Role, user.role_id) if user.role_id else None
    ctx = AppContext(
        user_id=user.id,
        hotel_id=hotel.id,
        username=user.username,
        role=normalize_role(role.code if role else ""),
        full_name=user.full_name or user.username,
        hotel_name=hotel.name,
    )
    return _attach_rbac(db, ctx)


def _dev_context(db: Session) -> AppContext:
    """开发模式免登录上下文。"""
    hotel = db.query(Hotel).order_by(Hotel.id).first()
    if not hotel:
        raise BusinessError("请先初始化酒店数据（deploy/dev/start.bat 或 deploy/docker）")
    user = db.query(User).filter_by(username="admin", is_active=True).first()
    if not user:
        user = db.query(User).filter_by(hotel_id=hotel.id, is_active=True).first()
    if not user:
        user = db.query(User).filter_by(is_active=True).first()
    role = db.get(Role, user.role_id) if user and user.role_id else None
    ctx = AppContext(
        user_id=user.id if user else 0,
        hotel_id=hotel.id,
        username=user.username if user else "dev",
        role=normalize_role(role.code if role else "admin"),
        full_name=user.full_name if user else "开发模式",
        hotel_name=hotel.name,
    )
    return _attach_rbac(db, ctx)


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> AppContext:
    if SKIP_AUTH:
        return _dev_context(db)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("未登录：请先使用账号密码登录")
    token = authorization.split(" ", 1)[1].strip()
    payload = parse_token(token)
    user_id = int(payload.get("user_id") or 0)
    hotel_id = int(payload.get("hotel_id") or DEFAULT_HOTEL_ID)
    user = db.get(User, user_id) if user_id else None
    hotel = db.get(Hotel, hotel_id)
    if not hotel:
        raise AuthorizationError("酒店配置无效")
    if user and not user.is_active:
        raise AuthorizationError("账号已停用")
    role = db.get(Role, user.role_id) if user and user.role_id else None
    role_code = normalize_role(role.code if role else str(payload.get("role") or ""))
    ctx = AppContext(
        user_id=user.id if user else user_id,
        hotel_id=hotel.id,
        username=user.username if user else str(payload.get("username") or ""),
        role=role_code,
        full_name=(user.full_name or user.username) if user else str(payload.get("username") or ""),
        hotel_name=hotel.name,
    )
    return _attach_rbac(db, ctx)


def require_scopes(*need: str):
    """接口级权限依赖：缺任一 scope/menu 即 403。admin 全过。"""

    def _dep(ctx: AppContext = Depends(get_current_user)) -> AppContext:
        if not need:
            return ctx
        if ctx.role == "admin":
            return ctx
        have = ctx.menus | ctx.scopes
        missing = [n for n in need if n not in have]
        if missing:
            raise AuthorizationError(f"无权操作：缺少 {', '.join(missing)}")
        return ctx

    return _dep
