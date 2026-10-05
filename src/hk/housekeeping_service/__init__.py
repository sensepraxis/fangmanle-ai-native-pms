# SPDX-License-Identifier: Apache-2.0
"""hk.housekeeping_service 子包 — 保留外部 import 兼容。

原 hk/housekeeping_service.py（3193 行）按业务子域拆为：
  - task_service           : 任务生命周期
  - repair_service         : 房间状态联动（维修任务）
  - dispatch_service       : 派单调度 + 核心 helper
  - board_service          : 看板 + MCP 工具
  - ai_service             : AI 助手
  - guest_request_service  : 客需工单

外部 `from hk.housekeeping_service import xxx` 走这里 re-export，零改动。
"""

from __future__ import annotations

from hk.housekeeping_service import (
    board_service,  # noqa: F401
    dispatch_service,  # noqa: F401
    guest_request_service,  # noqa: F401
    repair_service,  # noqa: F401
    task_service,  # noqa: F401
)
from hk.housekeeping_service.board_service import (
    build_housekeeping_board,
    ensure_open_tasks_from_rooms,
    hk_ui_status,
    mcp_draft_housekeeping_tasks,
    mcp_list_guest_requests,
    mcp_list_room_status,
    mcp_list_staff_load,
    run_hk_mcp_tools,
)

# ---- 私有 helper re-export（外部代码仍走 hk.housekeeping_service._xxx 路径）----
# 说明：routers/housekeeping.py / commercial.hk.hk_ai_harness 等依赖这些私有 helper。
from hk.housekeeping_service.dispatch_service import (
    _on_duty_staff,
    _waiting_dispatch_rows,
    batch_dispatch,
    notify_hk_dispatch_wecom,
)
from hk.housekeeping_service.guest_request_service import create_guest_request, list_service_requests
from hk.housekeeping_service.repair_service import (
    close_repair_tasks_for_room,
    complete_repair_and_clear_ooo,
    ensure_checkout_clean_task,
    ensure_repair_task,
)

# ---- 模块级常量 re-export（HK_ICON / HK_TYPE_CN）----
# ---- Public re-exports（兼容旧 from xxx import yyy）----
# AI 助手在 commercial.hk，惰性导出以避免与 commercial ↔ OpenCore 循环 import
from hk.housekeeping_service.task_service import (
    HK_ICON,
    HK_TYPE_CN,
    assign_task,
    create_housekeeping_task,
    create_housekeeping_tasks,
    finish_clean,
    ignore_task,
    inspect_task,
    list_housekeeping_tasks,
    start_task,
    task_public_dict,
    urge_task,
)


def __getattr__(name: str):
    if name in ("ai_service", "ai_suggest_dispatch", "build_housekeeping_ai_assistant"):
        from infra.commercial_pack import load_module

        _ai = load_module("commercial.hk.housekeeping_ai_service")
        if _ai is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        if name == "ai_service":
            return _ai
        return getattr(_ai, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ai_suggest_dispatch",
    "assign_task",
    "batch_dispatch",
    "build_housekeeping_ai_assistant",
    "build_housekeeping_board",
    "close_repair_tasks_for_room",
    "complete_repair_and_clear_ooo",
    "create_guest_request",
    "create_housekeeping_task",
    "create_housekeeping_tasks",
    "ensure_checkout_clean_task",
    "ensure_open_tasks_from_rooms",
    "ensure_repair_task",
    "finish_clean",
    "hk_ui_status",
    "ignore_task",
    "inspect_task",
    "list_housekeeping_tasks",
    "list_service_requests",
    "mcp_draft_housekeeping_tasks",
    "mcp_list_guest_requests",
    "mcp_list_room_status",
    "mcp_list_staff_load",
    "notify_hk_dispatch_wecom",
    "run_hk_mcp_tools",
    "start_task",
    "task_public_dict",
    "urge_task",
    "HK_ICON",
    "HK_TYPE_CN",
]
