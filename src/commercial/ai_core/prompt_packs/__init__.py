# SPDX-License-Identifier: BUSL-1.1
"""AI Prompt packs · 按 locale 选择 system 文案 + 语言约束。

``get_scene_prompt(domain, scene)`` 返回已 brand 替换的 system prompt。
``language_instruction()`` 追加到 LLM system，强制输出语言。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from infra.branding import brand_text
from infra.i18n import get_locale, normalize_locale

_PACK_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=4)
def _load_pack(locale: str) -> dict[str, Any]:
    loc = normalize_locale(locale)
    # en / zh-CN files
    name = "en.json" if loc == "en" else "zh-CN.json"
    fp = _PACK_DIR / name
    if not fp.exists():
        fp = _PACK_DIR / "zh-CN.json"
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}


def reload_prompt_packs() -> None:
    _load_pack.cache_clear()


def language_instruction(locale: Optional[str] = None) -> str:
    loc = normalize_locale(locale or get_locale())
    if loc == "en":
        return (
            "Language: Respond entirely in English. "
            "JSON string values (summary, reasons, key_points, labels) must be English. "
            "Do not use Chinese except for proper nouns that must stay Chinese."
        )
    return "语言：请全部使用中文回答。JSON 中的 summary、reasons、key_points、label 等字符串须为中文。"


def get_default_system_prompt(locale: Optional[str] = None) -> str:
    pack = _load_pack(locale or get_locale())
    raw = str(pack.get("default_system") or "")
    return brand_text(raw) if raw else ""


def get_scene_prompt(domain: str, scene: str, locale: Optional[str] = None) -> str:
    """domain: finance | hk | shift | ask | mkt | mkt_coupon | mkt_member | mkt_points | board | segment"""
    pack = _load_pack(locale or get_locale())
    section = pack.get(domain) if isinstance(pack.get(domain), dict) else {}
    raw = ""
    if isinstance(section, dict):
        raw = str(section.get(scene) or section.get("_default") or "")
    if not raw:
        # fallback to zh pack scene
        zh = _load_pack("zh-CN")
        sec = zh.get(domain) if isinstance(zh.get(domain), dict) else {}
        if isinstance(sec, dict):
            raw = str(sec.get(scene) or "")
    text = brand_text(raw) if raw else ""
    if text:
        text = f"{text}\n\n{language_instruction(locale)}"
    return text


def get_ask_system(*, followup: bool = False, locale: Optional[str] = None) -> str:
    pack = _load_pack(locale or get_locale())
    ask = pack.get("ask") if isinstance(pack.get("ask"), dict) else {}
    key = "followup" if followup else "answer"
    raw = str((ask or {}).get(key) or "")
    text = brand_text(raw) if raw else ""
    if text:
        text = f"{text}\n\n{language_instruction(locale)}"
    return text


__all__ = [
    "language_instruction",
    "get_default_system_prompt",
    "get_scene_prompt",
    "get_ask_system",
    "reload_prompt_packs",
]
