# SPDX-License-Identifier: Apache-2.0
"""交班 AI · Scene Strategy（handover / takeover）。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError

CandidateBuilder = Callable[[Session, int, int], tuple[dict, list[dict], list[str]]]

_REGISTRY: dict[str, dict[str, Any]] = {}


def register_shift_scene(
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


def list_shift_scenes() -> tuple[str, ...]:
    return tuple(_REGISTRY.keys())


def get_shift_scene(key: str) -> dict[str, Any]:
    scene = (key or "").strip()
    if scene not in _REGISTRY:
        raise InvalidStateError(f"scene 须为 handover / takeover（当前：{', '.join(list_shift_scenes()) or '未注册'}）")
    return _REGISTRY[scene]


def build_shift_candidates(
    db: Session, hotel_id: int, handover_id: int, scene: str
) -> tuple[dict, list[dict], list[str], str]:
    meta = get_shift_scene(scene)
    sit, items, reasons = meta["builder"](db, hotel_id, handover_id)
    return sit, items, reasons, meta["title"]


__all__ = [
    "register_shift_scene",
    "list_shift_scenes",
    "get_shift_scene",
    "build_shift_candidates",
]
