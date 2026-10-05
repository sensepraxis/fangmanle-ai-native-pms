# SPDX-License-Identifier: Apache-2.0
"""用户管理与角色权限配置 API — 薄 HTTP 层。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api_common import ok
from database import get_db
from infra.auth_local import AppContext, get_current_user, require_scopes

router = APIRouter(tags=["rbac"])


class UserCreateBody(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role_code: str
    phone: str = ""
    is_active: bool = True


class UserUpdateBody(BaseModel):
    full_name: Optional[str] = None
    role_code: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class RolePermsBody(BaseModel):
    codes: list[str] = Field(default_factory=list)


class RoleCreateBody(BaseModel):
    code: str
    name: str
    description: str = ""
    copy_from: Optional[str] = None


class RoleUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


def _assert_can_list_roles(ctx: AppContext) -> None:
    if ctx.role == "admin":
        return
    if ctx.can("menu.system.rbac") or ctx.can("menu.system.users"):
        return
    raise HTTPException(403, "无权查看角色列表")


@router.get("/rbac/roles")
def list_roles(
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.rbac import list_roles as list_roles_uc

    _assert_can_list_roles(ctx)
    return ok(list_roles_uc(db))


@router.post("/rbac/roles")
def create_role(
    body: RoleCreateBody,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.rbac")),
):
    from application.rbac import create_role as create_role_uc

    return ok(
        create_role_uc(
            db,
            code=body.code,
            name=body.name,
            description=body.description,
            copy_from=body.copy_from,
        )
    )


@router.put("/rbac/roles/{role_code}")
def update_role(
    role_code: str,
    body: RoleUpdateBody,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.rbac")),
):
    from application.rbac import update_role as update_role_uc

    return ok(update_role_uc(db, role_code, name=body.name, description=body.description))


@router.delete("/rbac/roles/{role_code}")
def remove_role(
    role_code: str,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.rbac")),
):
    from application.rbac import delete_role

    return ok(delete_role(db, role_code))


@router.get("/rbac/permissions")
def list_permissions_tree(
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("menu.system.rbac")),
):
    from application.rbac import list_permissions_tree as list_permissions_tree_uc

    return ok(list_permissions_tree_uc(db))


@router.get("/rbac/roles/{role_code}/permissions")
def get_role_permissions(
    role_code: str,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("menu.system.rbac")),
):
    from application.rbac import get_role_permissions as get_role_permissions_uc

    return ok(get_role_permissions_uc(db, role_code))


@router.put("/rbac/roles/{role_code}/permissions")
def put_role_permissions(
    role_code: str,
    body: RolePermsBody,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.rbac")),
):
    from application.rbac import save_role_permissions

    return ok(save_role_permissions(db, role_code, body.codes))


@router.post("/rbac/roles/{role_code}/reset-defaults")
def reset_role_defaults(
    role_code: str,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.rbac")),
):
    from application.rbac import reset_role_defaults as reset_role_defaults_uc

    return ok(reset_role_defaults_uc(db, role_code))


@router.get("/rbac/users")
def list_users(
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("menu.system.users")),
):
    from application.rbac import list_users as list_users_uc

    return ok(list_users_uc(db))


@router.post("/rbac/users")
def create_user(
    body: UserCreateBody,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.users")),
):
    from application.rbac import create_user as create_user_uc

    return ok(
        create_user_uc(
            db,
            hotel_id=ctx.hotel_id,
            username=body.username,
            password=body.password,
            role_code=body.role_code,
            full_name=body.full_name,
            phone=body.phone,
            is_active=body.is_active,
            actor_role=ctx.role,
        )
    )


@router.put("/rbac/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateBody,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(require_scopes("action.system.users")),
):
    from application.rbac import update_user as update_user_uc

    return ok(
        update_user_uc(
            db,
            user_id,
            actor_role=ctx.role,
            actor_user_id=ctx.user_id,
            full_name=body.full_name,
            role_code=body.role_code,
            phone=body.phone,
            is_active=body.is_active,
            password=body.password,
        )
    )
