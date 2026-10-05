# SPDX-License-Identifier: BUSL-1.1
"""房务 AI Harness · Scene Strategy 注册表（对齐 finance.ai_scene_registry）。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError

# builder 返回 items, reasons（situation 由 build_situation 另算）
CandidateBuilder = Callable[[Session, int], tuple[list[dict], list[str]]]
SituationBuilder = Callable[[Session, int], dict]

_REGISTRY: dict[str, dict[str, Any]] = {}


def register_hk_scene(
    key: str,
    *,
    title: str,
    builder: CandidateBuilder,
    situation_builder: Optional[SituationBuilder] = None,
    system_prompt: Optional[str] = None,
) -> None:
    _REGISTRY[key] = {
        "key": key,
        "title": title,
        "builder": builder,
        "situation_builder": situation_builder,
        "system_prompt": system_prompt,
    }


def list_hk_scenes() -> tuple[str, ...]:
    return tuple(_REGISTRY.keys())


def get_hk_scene(key: str) -> dict[str, Any]:
    scene = (key or "").strip()
    if scene not in _REGISTRY:
        raise InvalidStateError(f"scene 须为：{', '.join(list_hk_scenes()) or '(empty)'}")
    return _REGISTRY[scene]


def build_hk_candidates(db: Session, hotel_id: int, scene: str) -> tuple[list[dict], list[str], str]:
    meta = get_hk_scene(scene)
    items, reasons = meta["builder"](db, hotel_id)
    return items, reasons, meta["title"]


__all__ = [
    "register_hk_scene",
    "list_hk_scenes",
    "get_hk_scene",
    "build_hk_candidates",
]
