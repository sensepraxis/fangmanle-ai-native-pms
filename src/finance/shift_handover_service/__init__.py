# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子包 — 保留外部 import 兼容。

原 finance/shift_handover_service.py（1115 行）按业务子域拆为：
  - handover_service        : workspace/sign/complete
  - shift_window_service    : 时间窗口
  - float_service           : 备用金 + Float Count
  - asset_service           : 资产盘点
  - revenue_service         : 营收 / 押金
  - task_service            : 任务 / 客需 / escalate
  - _common                 : 共用 helper

外部 `from finance.shift_handover_service import xxx` 走这里 re-export。
注意：测试用 patch("finance.shift_handover_service._current_shift", ...) 等，
故私有 helper 也通过这里 re-export，保证 patch path 命中。
"""

from __future__ import annotations

# ---- 让 patch("finance.shift_handover_service.date") 命中 ----
from datetime import date as date  # noqa: F401  兼容 patch path
from datetime import datetime as datetime

from finance.shift_handover_service import (
    _common,  # noqa: F401
    asset_service,  # noqa: F401
    float_service,  # noqa: F401
    handover_service,  # noqa: F401
    revenue_service,  # noqa: F401
    shift_window_service,  # noqa: F401
    task_service,  # noqa: F401
)

# ---- 私有 helper 也 re-export（让 patch path 命中）----
from finance.shift_handover_service._common import (
    _f,
    _log,
    _mask_name,
    _money,
)
from finance.shift_handover_service.asset_service import (
    _build_asset_inventory,
    _normalize_unconfirmed_assets,
    _purge_legacy_assets,
    _sync_assets_from_inventory,
    save_asset_count,
)
from finance.shift_handover_service.float_service import (
    _float_breakdown_expected,
    _float_expected,
    _float_history,
    _sync_float_breakdown,
    save_float_count,
)

# ---- 公共 API ----
from finance.shift_handover_service.handover_service import (
    build_workspace,
    complete_handover,
    get_or_create_handover,
    sign_handover,
)
from finance.shift_handover_service.revenue_service import (
    _channel_revenue,
    _deposit_handover,
    _merge_yesterday,
    _revenue_target,
)
from finance.shift_handover_service.shift_window_service import (
    _current_shift,
    _shift_window,
)
from finance.shift_handover_service.task_service import (
    _build_tasks,
    _carryover_tasks,
    _guest_situations,
    escalate_task,
    guest_situations_for_display,
    tasks_for_display,
)

__all__ = [
    # 公共 API
    "build_workspace",
    "complete_handover",
    "escalate_task",
    "get_or_create_handover",
    "save_asset_count",
    "save_float_count",
    "sign_handover",
    # 私有 helper（也 export，让 patch path 命中）
    "_money",
    "_f",
    "_mask_name",
    "_log",
    "_current_shift",
    "_shift_window",
    "_float_expected",
    "_float_breakdown_expected",
    "_sync_float_breakdown",
    "_float_history",
    "_build_asset_inventory",
    "_sync_assets_from_inventory",
    "_purge_legacy_assets",
    "_normalize_unconfirmed_assets",
    "_revenue_target",
    "_channel_revenue",
    "_merge_yesterday",
    "_deposit_handover",
    "_guest_situations",
    "_build_tasks",
    "_carryover_tasks",
    "guest_situations_for_display",
    "tasks_for_display",
]
