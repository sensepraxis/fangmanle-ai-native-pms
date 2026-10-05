# SPDX-License-Identifier: Apache-2.0
"""Dump FastAPI OpenAPI JSON to docs/openapi.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FML_COMMERCIAL", os.environ.get("FML_COMMERCIAL", "0"))

from api import app  # noqa: E402

out = ROOT / "docs" / "openapi.json"
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out)
