# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""整体优化 locales/en.json：去重、剔污染、收窄为「仍被 t()/_t() 引用」的词条。

用法::
    python tools/i18n_optimize.py           # 写回 + sync mirrors
    python tools/i18n_optimize.py --dry-run # 只打印统计

原则：
- 正式源只改 ``locales/en.json``
- 稳定命名空间（nav/common/...）保留
- 中文 msgid 保留：静态 ``t()``/``_t()``、前端 lib 常量表中文串（动态 ``t(map[k])``）、
  以及已有实质英译的条目（避免误删动态 msgid）
- 删除顶层与 phrases 重复的中文键；删除脚本污染键
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_catalog import CANONICAL, save_canonical, sync_mirrors  # noqa: E402

CN_CHAR = re.compile(r"[\u4e00-\u9fff]")
# t('...') / _t("...") — 单行，禁止跨行吞进整段 JS
T_CALL = re.compile(r"""(?<![A-Za-z0-9_])_?t\(\s*(['"])(?P<body>(?:\\.|(?!\1)[^\n])*?)\1""")
# 常量表里的中文 msgid（供 t(SOURCE_LABEL[k]) 等动态查找）
CN_LITERAL = re.compile(r"""['"]([^'"\n]*[\u4e00-\u9fff][^'"\n]*)['"]""")

SKIP_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    "locales",
}

# 稳定命名空间：永不当「中文 msgid 顶层键」删
STABLE_TOP = frozenset(
    {
        "nav",
        "common",
        "auth",
        "error",
        "deposit",
        "channel",
        "orders",
        "finance",
        "rooms",
        "guests",
        "mkt",
        "hk",
        "analytics",
        "system",
        "phrases",
    }
)

# 仅判「代码碎片」；允许 UI 文案里的 <strong>、比较符 >、<、反引号说明
POLLUTION_MARKERS = (
    "const ",
    "let ",
    "var ",
    "function ",
    "=>",
    "document.",
    "class=",
    "ref(",
    "import ",
    "]),",
    "// ",
)


def _unescape(body: str) -> str:
    body = body.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"')
    body = body.replace("\\\\", "\\")
    return body.strip()


def extract_t_msgids() -> set[str]:
    roots = [ROOT / "frontend" / "src", ROOT / "src"]
    found: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in {".py", ".vue", ".ts", ".tsx", ".js"}:
                continue
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in T_CALL.finditer(text):
                body = _unescape(m.group("body"))
                if not body or not CN_CHAR.search(body):
                    continue
                # 单行化（模板里偶发换行）
                body = " ".join(body.split())
                found.add(body)
    return found


def extract_dynamic_msgid_literals() -> set[str]:
    """前端 lib / 后端常见「中文常量 → t(变量)」动态 msgid。"""
    roots = [
        ROOT / "frontend" / "src" / "lib",
        ROOT / "src" / "infra",
    ]
    found: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix not in {".ts", ".tsx", ".js", ".py"}:
                continue
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in CN_LITERAL.finditer(text):
                body = " ".join(m.group(1).split())
                if not body or is_pollution(body):
                    continue
                # 过长说明/日志不进 live
                if len(body) > 80:
                    continue
                found.add(body)
    return found


def has_real_en(msgid: str, en: str) -> bool:
    """已有实质英译的条目，孤儿清理时保留（动态 msgid 兜底）。"""
    en = str(en or "")
    if not en or en == msgid:
        return False
    if CN_CHAR.search(en) and not re.search(r"[A-Za-z]", en):
        return False
    return True


def is_pollution(key: str) -> bool:
    s = key or ""
    if any(m in s for m in POLLUTION_MARKERS):
        return True
    # 坏提取残留：以 ') 或 ', 开头的半截模板
    if s.startswith("')") or s.startswith("',") or s.startswith('"}') or s.startswith("`},"):
        return True
    if "\n" in s and ("const " in s or "else {" in s or "ref<" in s):
        return True
    # 模板字符串拼进 msgid 的典型形态
    if "${" in s and ("`" in s or "const" in s or "else {" in s):
        return True
    return False


def better_en(a: str, b: str, msgid: str) -> str:
    """选更好的英译：优先非中文、非空、且不等于 msgid。"""

    def score(v: str) -> tuple:
        v = str(v or "")
        return (
            1 if v and v != msgid else 0,
            0 if CN_CHAR.search(v) else 1,
            len(v),
        )

    return a if score(a) >= score(b) else b


def optimize(dry_run: bool = False) -> dict:
    en_path = CANONICAL / "en.json"
    en = json.loads(en_path.read_text(encoding="utf-8"))
    phrases = dict(en.get("phrases") or {})
    live_raw = extract_t_msgids() | extract_dynamic_msgid_literals()
    live = {k for k in live_raw if not is_pollution(k)}

    stats = {
        "before_phrases": len(phrases),
        "before_top_cn": 0,
        "t_msgids": len(live),
        "skipped_polluted_t": len(live_raw) - len(live),
        "removed_top_dup": 0,
        "removed_pollution": 0,
        "removed_orphan": 0,
        "kept_phrases": 0,
        "merged_into_phrases": 0,
    }

    # 1) 顶层中文键 → 合并进 phrases 后删除
    top_cn_keys = [k for k, v in en.items() if k not in STABLE_TOP and isinstance(v, str) and CN_CHAR.search(k)]
    stats["before_top_cn"] = len(top_cn_keys)
    for k in top_cn_keys:
        v = en[k]
        if k in phrases:
            phrases[k] = better_en(phrases[k], v, k)
        else:
            phrases[k] = v
            stats["merged_into_phrases"] += 1
        if not dry_run:
            del en[k]
        stats["removed_top_dup"] += 1

    # 2) 剔除污染
    for k in list(phrases.keys()):
        if is_pollution(k):
            del phrases[k]
            stats["removed_pollution"] += 1

    # 3) 剔除未被 t() 引用的孤儿中文 msgid（保留仍被引用的 + 稳定命名空间无关）
    #    注意：拼接型 t('x'+y) 扫不到；保守策略：孤儿且「中=中」或英译很差才删？
    #    用户要求整体优化瘦身：删除不在 live 中的 phrases。
    #    风险：动态 msgid。缓解：保留 live 的所有键；孤儿中若英译有实质内容也删
    #    （动态 msgid 本来就翻不到固定包）。
    for k in list(phrases.keys()):
        if k in live:
            continue
        # 已有实质英译的保留：动态 t(变量) 扫不全时的安全网
        if has_real_en(k, phrases.get(k, "")):
            continue
        del phrases[k]
        stats["removed_orphan"] += 1

    # 4) 确保所有 live msgid 在 phrases 中有条目（缺则中=中占位）
    for k in live:
        phrases.setdefault(k, k)

    phrases = dict(sorted(phrases.items(), key=lambda x: x[0]))
    stats["kept_phrases"] = len(phrases)
    stats["after_bytes_est"] = len(json.dumps({**en, "phrases": phrases}, ensure_ascii=False))

    if not dry_run:
        en["phrases"] = phrases
        save_canonical("en.json", en)
        sync_mirrors()

    return stats


def health_check() -> dict:
    """CI：顶层不得再堆中文 msgid；phrases 不得含 HTML 污染。"""
    en = json.loads((CANONICAL / "en.json").read_text(encoding="utf-8"))
    phrases = en.get("phrases") or {}
    top_cn = [k for k, v in en.items() if k not in STABLE_TOP and isinstance(v, str) and CN_CHAR.search(k)]
    pollution = [k for k in phrases if is_pollution(k)]
    return {
        "ok": not top_cn and not pollution,
        "top_cn_keys": len(top_cn),
        "pollution_keys": len(pollution),
        "phrases": len(phrases),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Optimize locales/en.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="health check only (CI)")
    args = ap.parse_args()
    if args.check:
        h = health_check()
        print(json.dumps(h, ensure_ascii=False))
        raise SystemExit(0 if h["ok"] else 1)
    stats = optimize(dry_run=args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.dry_run:
        print("(dry-run: no files written)")


if __name__ == "__main__":
    main()
