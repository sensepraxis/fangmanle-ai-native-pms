# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""可选：合并 ``tools/_i18n_hand_*.json`` 入手翻 phrases（若存在）。

发布包不再附带历史手翻 JSON；译文已在 ``locales/en.json``。
若本地自备 hand pack，放到 ``tools/`` 后运行本脚本。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_catalog import save_canonical, sync_mirrors  # noqa: E402


def main() -> None:
    packs = [Path(p) for p in sys.argv[1:]]
    if not packs:
        packs = sorted((ROOT / "tools").glob("_i18n_hand_*.json"))
    if not packs:
        print("no tools/_i18n_hand_*.json found (ok for release; phrases already in locales/en.json)")
        return

    en_path = ROOT / "locales/en.json"
    en = json.loads(en_path.read_text(encoding="utf-8"))
    phrases: dict = dict(en.get("phrases") or {})
    applied = 0
    for p in packs:
        path = p if p.is_absolute() else ROOT / p
        if not path.exists():
            print(f"MISSING {path}")
            continue
        hand = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(hand, dict):
            print(f"BAD {path}")
            continue
        for k, v in hand.items():
            if not isinstance(k, str) or not isinstance(v, str) or not v.strip():
                continue
            if phrases.get(k) != v:
                applied += 1
            phrases[k] = v
        print(f"merged {path.name} keys={len(hand)}")

    en["phrases"] = dict(sorted(phrases.items(), key=lambda x: x[0]))
    save_canonical("en.json", en)
    sync_mirrors()
    print(f"phrases={len(phrases)} applied_changes={applied}")


if __name__ == "__main__":
    main()
