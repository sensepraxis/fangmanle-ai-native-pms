# SPDX-License-Identifier: BUSL-1.1
"""财务 AI Harness · Scene Strategy 注册表。

把 ``_build`` 里的 if/elif scene 换成可注册策略，新增场景无需改分发核心。
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol

from sqlalchemy.orm import Session

from domain import InvalidStateError

CandidateBuilder = Callable[[Session, int], tuple[dict, list[dict], list[str]]]


class FinanceAiScene(Protocol):
    key: str
    title: str

    def build_candidates(self, db: Session, hotel_id: int) -> tuple[dict, list[dict], list[str]]: ...


_REGISTRY: dict[str, dict[str, Any]] = {}


def register_finance_scene(
    key: str,
    *,
    title: str,
    builder: CandidateBuilder,
    system_prompt: Optional[str] = None,
) -> None:
    _REGISTRY[key] = {
        "key": key,
        "title": title,
        "builder": builder,
        "system_prompt": system_prompt,
    }


def list_finance_scenes() -> tuple[str, ...]:
    return tuple(_REGISTRY.keys())


def get_finance_scene(key: str) -> dict[str, Any]:
    scene = (key or "").strip()
    if scene not in _REGISTRY:
        raise InvalidStateError(f"scene 须为：{', '.join(list_finance_scenes())}")
    return _REGISTRY[scene]


def build_scene_candidates(db: Session, hotel_id: int, scene: str) -> tuple[dict, list[dict], list[str], str]:
    from infra.i18n import t

    meta = get_finance_scene(scene)
    sit, items, reasons = meta["builder"](db, hotel_id)
    return sit, items, reasons, t(meta["title"])


__all__ = [
    "register_finance_scene",
    "list_finance_scenes",
    "get_finance_scene",
    "build_scene_candidates",
]
