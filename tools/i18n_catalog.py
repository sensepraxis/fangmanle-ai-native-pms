# SPDX-License-Identifier: Apache-2.0
"""单一 i18n catalog：正式源是仓库根 ``locales/``。

镜像目录（``frontend/src/locales``、``src/locales``）只允许由本模块拷贝生成，
禁止手改三份 ``en.json``。新词条只改 ``locales/*.json``，然后::

    python tools/i18n_catalog.py
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "locales"
MIRROR_DIRS = (
    ROOT / "frontend" / "src" / "locales",
    ROOT / "src" / "locales",
)
CATALOG_NAMES = ("zh-CN.json", "en.json")


def canonical_path(name: str) -> Path:
    return CANONICAL / name


def load_json(name: str) -> dict[str, Any]:
    p = canonical_path(name)
    return json.loads(p.read_text(encoding="utf-8"))


def save_canonical(name: str, data: dict[str, Any]) -> Path:
    p = canonical_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def sync_mirrors() -> list[Path]:
    """把正式源拷到前后端镜像。返回写入的文件路径。"""
    written: list[Path] = []
    if not CANONICAL.is_dir():
        raise FileNotFoundError(f"canonical locales dir missing: {CANONICAL}")
    for dest in MIRROR_DIRS:
        dest.mkdir(parents=True, exist_ok=True)
        for name in CATALOG_NAMES:
            src = CANONICAL / name
            if not src.exists():
                continue
            target = dest / name
            shutil.copy2(src, target)
            written.append(target)
    return written


def mirrors_match() -> bool:
    for name in CATALOG_NAMES:
        src = CANONICAL / name
        if not src.exists():
            continue
        src_bytes = src.read_bytes()
        for dest in MIRROR_DIRS:
            other = dest / name
            if not other.exists() or other.read_bytes() != src_bytes:
                return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync locales/ → frontend + src mirrors")
    ap.add_argument("--check", action="store_true", help="exit 1 if mirrors drift")
    args = ap.parse_args()
    if args.check:
        ok = mirrors_match()
        print(f"i18n mirrors match={ok} canonical={CANONICAL}")
        raise SystemExit(0 if ok else 1)
    written = sync_mirrors()
    print(f"synced {len(written)} files from {CANONICAL}")


if __name__ == "__main__":
    main()
