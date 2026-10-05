# SPDX-License-Identifier: Apache-2.0
"""pytest 共享固件（session-scope 一次性搭建 + test 间隔离）。

职责：
  1. 在任何业务模块 import 之前，把 DATABASE_URL 锁定到 SQLite（临时文件），
     避免误连 database.py 默认的 PostgreSQL，保证无外部依赖即可跑单测。
  2. 启动时跑 _bootstrap_demo_data（建表 + 灌种子数据）。
  3. 每个 test 前重置 Room.status=VC（避免 checkin 房态污染后续 test）。

种子数据函数实现见 _seed_data.py（拆分后保持 conftest 简洁）。

说明：需要真实后端的 HTTP 冒烟用例（test_flow.py）在无服务时自动 pytest.skip，
既保留其作为「集成测试」的价值，又不阻断 CI。
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

# ---- 0) 路径：确保 import database / models / ... 可用 ----
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# 单测加速：生产默认 12 万次 PBKDF2；测试库灌种很多次用户。
os.environ.setdefault("FML_PBKDF2_ITERATIONS", "1000")

# ---- 1) 锁定 SQLite ----
if not os.environ.get("DATABASE_URL", "").startswith("sqlite"):
    _tmp_db = Path(tempfile.gettempdir()) / "fml_pytest.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"

# ---- 2) 业务模块 import（database.py 读 DATABASE_URL）----
import pytest  # noqa: E402

import models  # noqa: F401  集中模型，确保全部表注册到 Base.metadata
from bootstrap.ensure_ar_ap import ensure_ar_ap_schema  # noqa: E402
from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry  # noqa: E402
from bootstrap.ensure_finance_params_ext import bootstrap_finance_params_ext  # noqa: E402
from bootstrap.ensure_mkt_member_v2 import ensure_member_system_schema, seed_member_system  # noqa: E402
from database import SessionLocal, engine  # noqa: E402

# Rule Engine：注册所有域的 RuleSet
from hk.hk_rules import HK_DISPATCH_RULESET  # noqa: E402,F401
from infra.auth_local import hash_password  # noqa: E402
from infra.rbac_service import ensure_system_roles  # noqa: E402
from models import Base, Hotel, Order, Room, RoomType, ServiceRequest, Supply, User  # noqa: E402
from tests._seed_data import (
    HOTEL_ID as SEED_HOTEL_ID,
)

# ---- 3) 种子数据函数（从 _seed_data.py 导入）----
from tests._seed_data import (  # noqa: E402
    SEED_USERS,
    _activate_dual_review,
    _bootstrap_demo_data,
    _seed_core,
    _seed_corp,
    _seed_rooms_supplies_and_ops,
)

HOTEL_ID = SEED_HOTEL_ID  # re-export 给测试用


def pytest_configure(config) -> None:
    """session-scope：建表 + 灌最小演示数据。"""
    config.addinivalue_line("markers", "commercial: 需要 src/commercial 且 FML_COMMERCIAL 未关闭")
    _bootstrap_demo_data(engine)


def pytest_runtest_setup(item) -> None:
    if item.get_closest_marker("commercial") is None:
        return
    from infra.commercial_pack import commercial_enabled

    if not commercial_enabled():
        pytest.skip("Commercial Core 未启用（无 src/commercial 或 FML_COMMERCIAL=0）")


@pytest.fixture(autouse=True)
def _reset_shared_room_state(request):
    """每个 test 前重置 Room.status=VC，避免 checkin 房态污染后续 test。

    为什么用 function-scope autouse：
    - pytest + unittest.TestCase 集成时，fixture 不会注入到 setUpClass/setUp
    - 但 fixture 在每个 test 函数前自动跑，覆盖 unittest.setUp

    unittest 常用 setUpClass 里长期占用 SessionLocal；SQLite 会把未提交事务
    锁到「database is locked」。先把 class 会话提交/回滚，再更新房态。
    """
    from sqlalchemy.exc import OperationalError

    cls = getattr(request, "cls", None)
    class_db = getattr(cls, "db", None) if cls is not None else None
    if class_db is not None:
        try:
            class_db.commit()
        except Exception:
            class_db.rollback()

    db = SessionLocal()
    try:
        last_err: OperationalError | None = None
        for attempt in range(3):
            try:
                db.query(Room).update({"status": "VC"})
                db.commit()
                last_err = None
                break
            except OperationalError as exc:
                last_err = exc
                db.rollback()
                if "locked" not in str(exc).lower() or attempt == 2:
                    break
                time.sleep(0.2 * (attempt + 1))
        if last_err is not None and "locked" not in str(last_err).lower():
            raise last_err
        if class_db is not None:
            class_db.expire_all()
    finally:
        db.close()
    yield
