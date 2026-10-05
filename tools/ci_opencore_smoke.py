# SPDX-License-Identifier: Apache-2.0
"""OpenCore smoke: with FML_COMMERCIAL=0, gate is off; ask kernel and rule shift still load."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["FML_COMMERCIAL"] = "0"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from infra.commercial_pack import commercial_enabled, reset_commercial_cache  # noqa: E402

reset_commercial_cache()
if commercial_enabled():
    raise SystemExit("FML_COMMERCIAL=0: commercial_enabled() must be False")

if os.environ.get("FML_OPENCORE_NODIR") == "1":
    if (SRC / "commercial").exists():
        raise SystemExit("FML_OPENCORE_NODIR=1: expected src/commercial to be gone")

from analytics.ask_catalog import INTENT_CATALOG, get_intent  # noqa: E402
from analytics.ask_pii import mask_name  # noqa: E402
from analytics.ask_playbook import PLAYBOOK  # noqa: E402
from analytics.ask_queries import resolve_ask_period  # noqa: E402
from finance.shift_handover_service.task_service import (  # noqa: E402
    guest_situations_for_display,
    tasks_for_display,
)

assert INTENT_CATALOG and get_intent("channel_profit_loss")
assert PLAYBOOK and callable(resolve_ask_period) and callable(mask_name)
assert callable(guest_situations_for_display) and callable(tasks_for_display)

from api import app  # noqa: E402

if app is None:
    raise SystemExit("api.app failed to load")
print("opencore-smoke ok", "intents=", len(INTENT_CATALOG))
