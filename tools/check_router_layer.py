# SPDX-License-Identifier: Apache-2.0
"""HTTP 层不得直连 Commercial Core / commercial_pack。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS = ROOT / "src" / "routers"

# 新代码禁止；存量 ORM 查询见 docs/BOUNDED_CONTEXTS.md「已知遗留」
_COMMERCIAL = re.compile(
    r"(\bfrom\s+commercial\b|\bimport\s+commercial\b|"
    r"infra\.commercial_pack|"
    r"commercial\.[a-zA-Z_]+)"
)


def main() -> int:
    bad: list[str] = []
    for path in ROUTERS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.split("#", 1)[0]
            if _COMMERCIAL.search(stripped):
                rel = path.relative_to(ROOT)
                bad.append(f"{rel}:{i}: {line.strip()}")
    if bad:
        print("router 禁止直连 commercial / commercial_pack，请改走 application.*：")
        print("\n".join(bad))
        return 1
    print("router layer ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
