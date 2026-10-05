# SPDX-License-Identifier: Apache-2.0
"""版本化 Schema 迁移骨架（Strangler：逐步替代 ensure_* 方言 ALTER）。

设计：
  - 表 ``schema_migrations`` 记录已应用版本（单行一版本，不可回滚自动执行）
  - ``MIGRATIONS`` 按 version 升序；幂等 upgrade(engine) → None
  - SQLite / PG 共用同一套版本号；方言分支写在各 migration 内部
  - 现有 ``bootstrap/ensure_*`` 仍可并行运行（兼容旧路径），新增量优先登记到此

用法::
    from infra.schema_migrate import apply_pending_migrations
    from database import engine
    result = apply_pending_migrations(engine)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

UpgradeFn = Callable[[Engine], None]


@dataclass(frozen=True)
class Migration:
    version: str  # e.g. "2026.10.01.001"
    description: str
    upgrade: UpgradeFn


def _ensure_registry_table(engine: Engine) -> None:
    insp = inspect(engine)
    if insp.has_table("schema_migrations"):
        return
    # 兼容 SQLite / PG：不用 GENERATED IDENTITY
    ddl = """
    CREATE TABLE schema_migrations (
        version VARCHAR(40) PRIMARY KEY,
        description VARCHAR(200),
        applied_at TIMESTAMP
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))


def applied_versions(engine: Engine) -> set[str]:
    _ensure_registry_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {r[0] for r in rows}


def _mark_applied(engine: Engine, m: Migration) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO schema_migrations (version, description, applied_at) VALUES (:v, :d, :t)"),
            {"v": m.version, "d": m.description[:200], "t": datetime.utcnow()},
        )


# ---- 登记迁移：只放「幂等、可安全重跑检测」的增量 ----


def _m001_schema_registry_bootstrap(engine: Engine) -> None:
    """占位：确保 registry 表存在（apply 入口已 ensure）。"""
    _ensure_registry_table(engine)


def _m002_wrap_room_hk_columns(engine: Engine) -> None:
    """把历史 room/hk ALTER 纳入版本账本（内部仍调 ensure，幂等）。"""
    from bootstrap.migrations.alter_room_hk_columns import ensure_room_hk_schema

    ensure_room_hk_schema(engine)


def _m003_wrap_coupon_wallet(engine: Engine) -> None:
    from bootstrap.ensure_coupon_wallet import ensure_coupon_wallet_schema

    ensure_coupon_wallet_schema(engine)


MIGRATIONS: list[Migration] = [
    Migration("2026.10.01.001", "bootstrap schema_migrations registry", _m001_schema_registry_bootstrap),
    Migration("2026.10.01.002", "room/hk columns via versioned wrap", _m002_wrap_room_hk_columns),
    Migration("2026.10.01.003", "coupon wallet schema via versioned wrap", _m003_wrap_coupon_wallet),
]


def apply_pending_migrations(engine: Engine, *, up_to: Optional[str] = None) -> dict:
    """应用未执行的迁移；返回 applied / skipped / current。"""
    _ensure_registry_table(engine)
    done = applied_versions(engine)
    applied: list[str] = []
    skipped: list[str] = []
    for m in sorted(MIGRATIONS, key=lambda x: x.version):
        if up_to and m.version > up_to:
            break
        if m.version in done:
            skipped.append(m.version)
            continue
        m.upgrade(engine)
        _mark_applied(engine, m)
        applied.append(m.version)
        done.add(m.version)
    return {
        "applied": applied,
        "skipped": skipped,
        "current": sorted(done)[-1] if done else None,
        "backend": engine.dialect.name,
    }


def register_migration(version: str, description: str, upgrade: UpgradeFn) -> None:
    """插件/扩展可在启动期追加迁移（须 version 唯一且可排序）。"""
    if any(m.version == version for m in MIGRATIONS):
        raise ValueError(f"migration version already registered: {version}")
    MIGRATIONS.append(Migration(version, description, upgrade))
    MIGRATIONS.sort(key=lambda x: x.version)
