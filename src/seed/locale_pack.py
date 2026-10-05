# SPDX-License-Identifier: Apache-2.0
"""种子数据语言包：由 SEED_LOCALE（或 FML_DEFAULT_LOCALE）选择中文 / 英文 demo 文案。

用法:
    from seed.locale_pack import get_seed_locale, get_pack, seed_text
    pack = get_pack()
    room_name = pack.ROOM_TYPE_TPL[0][1]
    tip = seed_text("高优：临近预抵或 VIP，建议优先闭环。")

环境变量:
    SEED_LOCALE=zh-CN | en
    （未设置时回退 FML_DEFAULT_LOCALE，再默认 zh-CN）
"""

from __future__ import annotations

import os
from functools import lru_cache
from types import ModuleType
from typing import Any


def get_seed_locale() -> str:
    raw = os.environ.get("SEED_LOCALE") or os.environ.get("FML_DEFAULT_LOCALE") or "zh-CN"
    s = str(raw).strip().lower()
    if s.startswith("en"):
        return "en"
    return "zh-CN"


@lru_cache(maxsize=2)
def get_pack(locale: str | None = None) -> ModuleType:
    loc = locale or get_seed_locale()
    if loc == "en":
        from seed.packs import en as pack
    else:
        from seed.packs import zh_CN as pack
    return pack


def clear_pack_cache() -> None:
    get_pack.cache_clear()


def seed_text(zh: str, en: str | None = None) -> str:
    """写入 DB 的展示文案：中文库用原文；英文库用 en 或对照表。

    算法码（如强度 弱/中/强/爆）请勿走本函数，保持与代码字典键一致。
    """
    if not zh:
        return zh
    if get_seed_locale() != "en":
        return zh
    if en is not None:
        return en
    from seed.packs.en_strings import EN_STRINGS

    return EN_STRINGS.get(zh, zh)


def seed_choice(items_zh: list[Any], items_en: list[Any] | None = None) -> list[Any]:
    if get_seed_locale() == "en" and items_en is not None:
        return items_en
    return items_zh
