# SPDX-License-Identifier: Apache-2.0
"""OpenCore ↔ Commercial Core 加载边界。

默认：磁盘上有 ``src/commercial`` 则启用。
``FML_COMMERCIAL=0`` 时即使目录存在也不加载（便于测 OpenCore 单独启动）。
去掉 ``src/commercial/`` 后 ``import commercial`` 失败，同样视为未启用。
"""

from __future__ import annotations

import importlib
import os
from typing import Any, Callable

_UNSET = object()
_enabled_cache: object = _UNSET


def commercial_enabled() -> bool:
    global _enabled_cache
    if _enabled_cache is not _UNSET:
        return bool(_enabled_cache)
    flag = str(os.environ.get("FML_COMMERCIAL", "1") or "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        _enabled_cache = False
        return False
    try:
        import commercial  # noqa: F401

        _enabled_cache = True
    except ImportError:
        _enabled_cache = False
    return bool(_enabled_cache)


def reset_commercial_cache() -> None:
    global _enabled_cache
    _enabled_cache = _UNSET


def load_module(dotted: str) -> Any | None:
    if not commercial_enabled():
        return None
    try:
        return importlib.import_module(dotted)
    except ImportError:
        return None


def unavailable_error():
    from domain import BusinessError
    from infra.i18n import t

    return BusinessError(t("商业 AI 能力未启用"))


def call(dotted: str, name: str, *args: Any, **kwargs: Any) -> Any:
    mod = load_module(dotted)
    if mod is None:
        raise unavailable_error()
    fn = getattr(mod, name, None)
    if fn is None:
        raise unavailable_error()
    return fn(*args, **kwargs)


def optional_call(dotted: str, name: str, default: Any, *args: Any, **kwargs: Any) -> Any:
    mod = load_module(dotted)
    if mod is None:
        return default
    fn = getattr(mod, name, None)
    if fn is None:
        return default
    return fn(*args, **kwargs)


def bind(dotted: str, name: str) -> Callable[..., Any]:
    def _fn(*args: Any, **kwargs: Any) -> Any:
        return call(dotted, name, *args, **kwargs)

    _fn.__name__ = name
    _fn.__qualname__ = name
    return _fn


# 关商业包时并入 branding.menus_hidden，前端 hasMenu / 路由按 pack 隐藏。
COMMERCIAL_UI_MENUS: tuple[str, ...] = (
    "menu.analytics.ai",
    "menu.system.llm",
)


def commercial_ui_hidden_menus() -> list[str]:
    if commercial_enabled():
        return []
    return list(COMMERCIAL_UI_MENUS)
