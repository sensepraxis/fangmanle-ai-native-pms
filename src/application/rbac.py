# SPDX-License-Identifier: Apache-2.0
"""Facade module for RBAC / 用户管理。

生成器可产出上方透传包装；文末 ``# --- orchestrated ---`` 为手写编排，勿覆盖。

职责：
  - 调 infra.rbac_service + 透传 BusinessError
  - 写路径事务边界（commit）在此层
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.rbac_service import (
    create_custom_role as _create_custom_role,
)
from infra.rbac_service import (
    create_user_account as _create_user_account,
)
from infra.rbac_service import (
    delete_custom_role as _delete_custom_role,
)
from infra.rbac_service import (
    get_role_or_raise as _get_role_or_raise,
)
from infra.rbac_service import (
    list_roles_enriched as _list_roles_enriched,
)
from infra.rbac_service import (
    list_users_enriched as _list_users_enriched,
)
from infra.rbac_service import (
    permission_tree as _permission_tree,
)
from infra.rbac_service import (
    reset_role_defaults as _reset_role_defaults,
)
from infra.rbac_service import (
    role_codes_snapshot as _role_codes_snapshot,
)
from infra.rbac_service import (
    role_public_dict as _role_public_dict,
)
from infra.rbac_service import (
    set_role_permission_codes as _set_role_permission_codes,
)
from infra.rbac_service import (
    update_custom_role as _update_custom_role,
)
from infra.rbac_service import (
    update_user_account as _update_user_account,
)


def list_roles(db: Session) -> list:
    return _list_roles_enriched(db)


def list_permissions_tree(db: Session) -> list:
    return _permission_tree(db)


def get_role_permissions(db: Session, role_code: str) -> dict:
    _get_role_or_raise(db, role_code)
    return {"role_code": role_code, "codes": _role_codes_snapshot(db, role_code)}


def list_users(db: Session) -> list:
    return _list_users_enriched(db)


# --- orchestrated ---


def create_role(
    db: Session,
    *,
    code: str,
    name: str,
    description: str = "",
    copy_from: Optional[str] = None,
) -> dict:
    try:
        role = _create_custom_role(
            db,
            code=code,
            name=name,
            description=description,
            copy_from=copy_from,
        )
        db.commit()
        return _role_public_dict(db, role)
    except Exception:
        db.rollback()
        raise


def update_role(
    db: Session,
    role_code: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    try:
        role = _update_custom_role(db, role_code, name=name, description=description)
        db.commit()
        return _role_public_dict(db, role)
    except Exception:
        db.rollback()
        raise


def delete_role(db: Session, role_code: str) -> dict:
    try:
        _delete_custom_role(db, role_code)
        db.commit()
        return {"deleted": role_code}
    except Exception:
        db.rollback()
        raise


def save_role_permissions(db: Session, role_code: str, codes: Iterable[str]) -> dict:
    try:
        _get_role_or_raise(db, role_code)
        n = _set_role_permission_codes(db, role_code, codes)
        db.commit()
        return {"role_code": role_code, "saved": n, "codes": _role_codes_snapshot(db, role_code)}
    except Exception:
        db.rollback()
        raise


def reset_role_defaults(db: Session, role_code: str) -> dict:
    try:
        out = _reset_role_defaults(db, role_code)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def create_user(
    db: Session,
    *,
    hotel_id: int,
    username: str,
    password: str,
    role_code: str,
    full_name: str = "",
    phone: str = "",
    is_active: bool = True,
    actor_role: str = "",
) -> dict:
    try:
        out = _create_user_account(
            db,
            hotel_id=hotel_id,
            username=username,
            password=password,
            role_code=role_code,
            full_name=full_name,
            phone=phone,
            is_active=is_active,
            actor_role=actor_role,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def update_user(
    db: Session,
    user_id: int,
    *,
    actor_role: str = "",
    actor_user_id: Optional[int] = None,
    full_name: Optional[str] = None,
    role_code: Optional[str] = None,
    phone: Optional[str] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> dict:
    try:
        out = _update_user_account(
            db,
            user_id,
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            full_name=full_name,
            role_code=role_code,
            phone=phone,
            is_active=is_active,
            password=password,
        )
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise
