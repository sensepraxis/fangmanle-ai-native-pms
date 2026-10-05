# SPDX-License-Identifier: Apache-2.0
"""core 域 ORM 模型。"""

from models._types import Base, Boolean, Column, DateTime, ForeignKey, Integer, SmallInteger, String, func


class Hotel(Base):
    """本店配置（全库仅一行）。"""

    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(40), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    city = Column(String(60))
    address = Column(String(255))
    timezone = Column(String(40), default="Asia/Shanghai")
    currency = Column(String(3), default="CNY")
    star_rating = Column(SmallInteger)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(40), nullable=False, unique=True)
    name = Column(String(60), nullable=False)
    description = Column(String(255))
    is_system = Column(Boolean, default=False)


# ============================================================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="SET NULL"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    username = Column(String(60), nullable=False, unique=True)
    password_hash = Column(String(128))
    full_name = Column(String(80))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Permission(Base):
    """RBAC 权限点：menu=二级菜单，action=按钮/敏感操作。"""

    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(80), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    kind = Column(String(20), nullable=False)  # menu | action
    module = Column(String(40), nullable=False)
    sort_order = Column(Integer, default=0)


# ============================================================================
class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
