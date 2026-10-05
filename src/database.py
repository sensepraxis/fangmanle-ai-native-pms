# SPDX-License-Identifier: Apache-2.0
"""数据库会话与引擎。

【双数据库后端】生产用 PostgreSQL；未设置 ``DATABASE_URL`` 时默认仓库根
``data/fml_demo.db``（SQLite），避免 fork 后静默去连本机 5432。

通过环境变量 DATABASE_URL 决定后端类型：

  · SQLite（未配置时的默认 / demo / CI）：
        sqlite:///C:/path/to/repo/data/fml_demo.db
        sqlite:///:memory:

  · PostgreSQL（生产，须显式设置）：
        postgresql+psycopg2://user:pass@host:5432/dbname
        postgresql+psycopg://user:pass@host:5432/dbname

切换：
    export DATABASE_URL=postgresql+psycopg2://fml:fmlpass@localhost:5432/fml
    $env:DATABASE_URL = "postgresql+psycopg2://fml:fmlpass@localhost:5432/fml"

生产部署务必设 DATABASE_URL 指向 PostgreSQL。

Schema 增量请登记 ``infra.schema_migrate.MIGRATIONS``。本地说明见 README「本地启动指南」。
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE = _REPO_ROOT / "data" / "fml_demo.db"


def default_database_url() -> str:
    """未设置环境变量时的 SQLite 路径（仓库根 data/fml_demo.db）。"""
    _DEFAULT_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + _DEFAULT_SQLITE.resolve().as_posix()


DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip() or default_database_url()

# connect_args 按后端类型分支
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
else:
    connect_args = {"connect_timeout": 5}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)

if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_concurrency_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)


def is_sqlite() -> bool:
    """当前后端是否为 SQLite（业务代码可借此分支判断方言特性）"""
    return DATABASE_URL.startswith("sqlite")


@contextmanager
def session_scope(*, commit: bool = True):
    """后台任务 / 启动期统一会话边界（禁止业务模块手写 SessionLocal+close）。

    用法::
        with session_scope() as db:
            do_work(db)
    """
    db = SessionLocal()
    try:
        yield db
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
