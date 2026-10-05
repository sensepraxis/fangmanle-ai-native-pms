# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""把源码里 ``t()`` / ``_t()`` 的中文 msgid 登记进 locales/en.json phrases。

**只扫已包装的翻译调用**，不再扫裸中文字面量（避免 prompt 碎片 / HTML 污染）。
新增词条缺省英译=中文占位；已有英译保留。写完后 sync mirrors。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_catalog import CANONICAL, save_canonical, sync_mirrors  # noqa: E402

CN_CHAR = re.compile(r"[\u4e00-\u9fff]")
T_CALL = re.compile(r"""(?<![A-Za-z0-9_])_?t\(\s*(['"])(?P<body>(?:\\.|(?!\1)[^\n])*?)\1""")

SKIP_PARTS = {".git", "node_modules", "__pycache__", "dist", "build", ".pytest_cache", "locales"}

# 高频 UI 手翻（setdefault 时优先）
HAND = {
    "经营总览": "Overview",
    "订单管理": "Orders",
    "房务与房态": "Rooms & Status",
    "客户会员": "Guests & Members",
    "数据洞察": "Analytics",
    "财务管理": "Finance",
    "私域运营": "Private Domain",
    "系统配置": "System",
    "保存": "Save",
    "取消": "Cancel",
    "确认": "Confirm",
    "删除": "Delete",
    "搜索": "Search",
    "加载中": "Loading",
    "退出登录": "Log out",
    "登录": "Log in",
    "请先登录": "Please sign in",
    "暂无数据": "No data",
}


def _unescape(body: str) -> str:
    body = body.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"')
    body = body.replace("\\\\", "\\")
    return " ".join(body.strip().split())


def extract_t_msgids(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    out: set[str] = set()
    for m in T_CALL.finditer(text):
        body = _unescape(m.group("body"))
        if not body or not CN_CHAR.search(body):
            continue
        if len(body) > 200:
            continue
        if any(x in body for x in ("<", ">", "`")):
            continue
        out.add(body)
    return out


def main() -> None:
    roots = [
        ROOT / "frontend" / "src",
        ROOT / "src",
    ]
    found: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in {".py", ".vue", ".ts", ".tsx"}:
                continue
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            found |= extract_t_msgids(p)

    en_path = CANONICAL / "en.json"
    en = json.loads(en_path.read_text(encoding="utf-8")) if en_path.exists() else {}
    phrases = dict(en.get("phrases") or {})
    for s in sorted(found):
        phrases.setdefault(s, HAND.get(s, s))
    # 不在此删除孤儿——留给 i18n_optimize.py
    en["phrases"] = dict(sorted(phrases.items(), key=lambda x: x[0]))
    save_canonical("en.json", en)
    sync_mirrors()
    print(f"phrases={len(phrases)} t_msgids={len(found)}")


if __name__ == "__main__":
    main()
