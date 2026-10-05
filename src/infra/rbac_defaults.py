# SPDX-License-Identifier: Apache-2.0
"""RBAC 四角色 demo 账号配置。

从原 `bootstrap.ensure_rbac` 抽离；ensure_rbac_users / bootstrap_rbac_all 仍在
`bootstrap.ensure_rbac` 里。

展示名跟随 SEED_LOCALE（与 seed.packs 一致）。
"""

from __future__ import annotations


def get_demo_users() -> list[tuple[str, str, str, str]]:
    try:
        from seed.locale_pack import get_pack

        pack = get_pack()
        users = getattr(pack, "LOCAL_USERS", None)
        if users:
            return list(users)
    except Exception:
        pass
    return [
        ("admin", "admin123", "admin", "系统管理员"),
        ("gm", "gm123", "gm", "店长"),
        ("revenue", "rm123", "rm", "收益经理"),
        ("front", "front123", "fd", "前台"),
    ]


# 兼容旧 import（优先在 SEED_LOCALE 已设置后使用 get_demo_users）
DEMO_USERS = get_demo_users()
