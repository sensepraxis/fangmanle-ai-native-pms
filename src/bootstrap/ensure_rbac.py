# SPDX-License-Identifier: Apache-2.0
"""RBAC 迁移：建表 + 四角色账号 + 默认权限矩阵。

RBAC demo 账号配置已抽到 `infra.rbac_defaults`；本文件保留 schema 保活与四角色账号
创建 / 旧账号停用逻辑。
"""

from __future__ import annotations

from infra.auth_local import hash_password
from infra.rbac_defaults import get_demo_users
from infra.rbac_service import bootstrap_rbac, ensure_rbac_schema, ensure_system_roles
from models import Hotel, Role, User


def ensure_rbac_users(db) -> dict:
    """幂等创建/对齐四角色账号；停用旧 housekeeping 等。"""
    hotel = db.query(Hotel).order_by(Hotel.id).first()
    if not hotel:
        return {"users": 0}
    roles = ensure_system_roles(db)
    touched = 0
    for username, password, role_code, full_name in get_demo_users():
        role = roles.get(role_code)
        u = db.query(User).filter_by(username=username).first()
        if not u:
            db.add(
                User(
                    hotel_id=hotel.id,
                    role_id=role.id if role else None,
                    username=username,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    is_active=True,
                )
            )
            touched += 1
        else:
            u.password_hash = hash_password(password)
            u.hotel_id = hotel.id
            u.role_id = role.id if role else u.role_id
            u.full_name = full_name
            u.is_active = True
            touched += 1

    # 旧账号：映射或停用
    legacy = {
        "housekeeping": ("fd", False),  # 客房并入前台能力，账号停用
        "finance": ("gm", False),
        "manager": ("gm", True),  # 保留为店长别名号
        "marketing": ("gm", False),
        "owner": ("gm", False),
    }
    for username, (role_code, keep_active) in legacy.items():
        u = db.query(User).filter_by(username=username).first()
        if not u:
            continue
        role = roles.get(role_code)
        if role:
            u.role_id = role.id
        u.is_active = keep_active
        if username == "manager" and keep_active and not u.password_hash:
            u.password_hash = hash_password("manager123")

    # 确保 admin 一定是 admin 角色
    admin_role = roles.get("admin")
    admin_u = db.query(User).filter_by(username="admin").first()
    if admin_u and admin_role:
        admin_u.role_id = admin_role.id
        admin_u.is_active = True

    db.commit()
    return {"users": touched, "hotel_id": hotel.id}


def bootstrap_rbac_all(engine, db, *, reset_matrix: bool = False) -> dict:
    ensure_rbac_schema(engine)
    from models import Permission, RolePermission

    Permission.__table__.create(bind=engine, checkfirst=True)
    RolePermission.__table__.create(bind=engine, checkfirst=True)
    info = bootstrap_rbac(db, reset_matrix=reset_matrix)
    users = ensure_rbac_users(db)
    return {**info, **users}
