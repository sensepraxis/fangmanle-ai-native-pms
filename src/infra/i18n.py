# SPDX-License-Identifier: Apache-2.0
"""轻量 i18n：请求级 locale + 中文 msgid / 稳定 key 双轨。

用法::
    from infra.i18n import t, set_locale, get_locale

    t("经营总览")                    # zh→原样；en→Overview（见 locales/en.json）
    t("nav.overview")                # 稳定 key（见 locales/zh-CN.json + en.json）
    t("状态 {status} 不允许", status="FROZEN")

环境变量 ``FML_DEFAULT_LOCALE``（默认 zh-CN）。
HTTP：``Accept-Language`` / ``X-Locale`` / ``?lang=``。
"""

from __future__ import annotations

import json
import os
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Optional

_locale_var: ContextVar[str] = ContextVar("fml_locale", default="")
_catalogs: dict[str, dict[str, str]] = {}
_loaded = False

# 正式源仅为仓库根 locales/；src/locales 只是构建拷贝，不作为加载源。
_ROOT_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "locales",
]

_PARAM_RE = re.compile(r"\{(\w+)\}")


def _default_locale() -> str:
    return (os.environ.get("FML_DEFAULT_LOCALE") or "zh-CN").strip() or "zh-CN"


def normalize_locale(raw: Optional[str]) -> str:
    s = (raw or "").strip().replace("_", "-")
    if not s:
        return _default_locale()
    low = s.lower()
    if low.startswith("en"):
        return "en"
    if low.startswith("zh"):
        return "zh-CN"
    return s if s in ("en", "zh-CN") else _default_locale()


def get_locale() -> str:
    cur = _locale_var.get()
    return normalize_locale(cur) if cur else _default_locale()


def set_locale(locale: str) -> None:
    _locale_var.set(normalize_locale(locale))


def clear_locale() -> None:
    _locale_var.set("")


def _flatten(obj: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            elif v is not None:
                out[key] = str(v)
                # 也允许顶层短 key
                if not prefix:
                    out[str(k)] = str(v)
    return out


def _find_locales_dir() -> Path:
    for p in _ROOT_CANDIDATES:
        if p.is_dir():
            return p
    # 兜底创建
    p = _ROOT_CANDIDATES[0]
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_catalogs(*, force: bool = False) -> None:
    global _loaded, _catalogs
    if _loaded and not force:
        return
    root = _find_locales_dir()
    cats: dict[str, dict[str, str]] = {"zh-CN": {}, "en": {}}
    for loc in ("zh-CN", "en"):
        fp = root / f"{loc}.json"
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        flat = _flatten(data)
        # phrases：中文 msgid → 译文。顶层显式译文优先（避免 phrases 中「中=中」覆盖已译条目）
        phrases = data.get("phrases") if isinstance(data, dict) else None
        if isinstance(phrases, dict):
            for mk, mv in phrases.items():
                key = str(mk)
                val = str(mv)
                existing = flat.get(key)
                if existing is not None and existing != key and val == key:
                    continue
                flat[key] = val
        # 再次套用顶层字符串，保证近期补的 en 顶层键胜出
        if isinstance(data, dict):
            for mk, mv in data.items():
                if mk == "phrases" or not isinstance(mv, str):
                    continue
                flat[str(mk)] = str(mv)
        cats[loc] = flat
    _catalogs = cats
    _loaded = True


def reload_catalogs() -> None:
    load_catalogs(force=True)


def _lookup(msgid: str, locale: str) -> str:
    load_catalogs()
    # 稳定 key 优先
    hit = _catalogs.get(locale, {}).get(msgid)
    if hit is not None:
        return hit
    # zh：找不到就回 msgid（中文原文）
    if locale.startswith("zh"):
        # 若 zh-CN 有 key，上面已命中；否则返回原文
        return msgid
    # en：再试 phrases / 原文
    hit = _catalogs.get("en", {}).get(msgid)
    if hit is not None:
        return hit
    return msgid


def t(msgid: str, **params: Any) -> str:
    """翻译 msgid；支持 ``{name}`` 插值。"""
    if not msgid:
        return ""
    text = _lookup(str(msgid), get_locale())
    if params:

        def repl(m: re.Match) -> str:
            k = m.group(1)
            return str(params[k]) if k in params else m.group(0)

        text = _PARAM_RE.sub(repl, text)
    return text


def td(mapping: dict[str, str], code: str, *, default: Optional[str] = None) -> str:
    """字典 code → 展示：value 当作 msgid 再翻译。"""
    raw = mapping.get(code)
    if raw is None:
        return default if default is not None else code
    return t(raw)


class TranslatingMap(dict):
    """dict[code]=msgid；取值时按当前 locale 翻译。"""

    def __getitem__(self, key):  # type: ignore[override]
        return t(dict.__getitem__(self, key))

    def get(self, key, default=None):  # type: ignore[override]
        if key not in self:
            return default
        return self[key]

    def items(self):  # type: ignore[override]
        return [(k, t(v)) for k, v in dict.items(self)]

    def values(self):  # type: ignore[override]
        return [t(v) for v in dict.values(self)]


def parse_accept_language(header: Optional[str]) -> str:
    if not header:
        return _default_locale()
    # 取第一个 tag
    first = header.split(",")[0].strip().split(";")[0].strip()
    return normalize_locale(first)


__all__ = [
    "t",
    "td",
    "TranslatingMap",
    "get_locale",
    "set_locale",
    "clear_locale",
    "normalize_locale",
    "load_catalogs",
    "reload_catalogs",
    "parse_accept_language",
]
