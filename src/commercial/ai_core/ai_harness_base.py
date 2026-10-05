# SPDX-License-Identifier: BUSL-1.1
"""AI Harness 公共骨架 · Template Method + JSON 解析。

各域 harness（财务 / 房务 / 交班）共享：
- ``strip_think`` / ``parse_json_blob``
- ``run_ai_draft_pipeline``：candidates → llm_refine → assemble（persist 由调用方负责）
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional, Protocol

from sqlalchemy.orm import Session


def strip_think(text: str) -> str:
    """去掉 Qwen3 等模型的思考链，便于解析 JSON。"""
    if not text:
        return ""
    raw = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
    raw = re.sub(r"<thinking>[\s\S]*?</thinking>", "", raw, flags=re.I)
    return raw.strip()


def parse_json_blob(text: str, *, strip_thinking: bool = True) -> dict | None:
    """从 LLM 文本提取首个 JSON object；失败返回 None。"""
    if not text:
        return None
    raw = strip_think(text) if strip_thinking else text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


# 兼容旧私有名
_strip_think = strip_think
_parse_json_blob = parse_json_blob


class AiDraftSteps(Protocol):
    """Template Method 钩子：各 harness 实现候选 / 精炼 / 落库。"""

    def build_candidates(self, db: Session, **ctx: Any) -> tuple[Any, list[dict], list[str], str]:
        """返回 situation, items, reasons, title。"""
        ...

    def refine_with_llm(
        self,
        db: Session,
        *,
        scene: str,
        title: str,
        situation: Any,
        items: list[dict],
        reasons: list[str],
    ) -> tuple[list[dict], list[str], str, Any, str, Optional[str], Optional[str]]:
        """返回 items, reasons, summary, extra, source, model, llm_error。"""
        ...


def run_ai_draft_pipeline(
    steps: AiDraftSteps,
    db: Session,
    *,
    scene: str,
    **ctx: Any,
) -> dict[str, Any]:
    """Template Method：建候选 → LLM 精炼 → 返回统一草稿结构（不含 DB persist）。"""
    situation, items, reasons, title = steps.build_candidates(db, scene=scene, **ctx)
    items, reasons, summary, extra, source, model, llm_error = steps.refine_with_llm(
        db,
        scene=scene,
        title=title,
        situation=situation,
        items=items,
        reasons=reasons,
    )
    return {
        "scene": scene,
        "title": title,
        "situation": situation,
        "summary": summary,
        "reasons": reasons,
        "items": items,
        "source": source,
        "model": model,
        "llm_error": llm_error,
        "extra": extra,
        "status": "draft",
    }


# Scene registry helpers (generic)
SceneBuilder = Callable[..., tuple]

_SCENE_REGISTRIES: dict[str, dict[str, dict[str, Any]]] = {}


def register_scene(domain: str, key: str, *, title: str, builder: SceneBuilder, **meta: Any) -> None:
    bucket = _SCENE_REGISTRIES.setdefault(domain, {})
    bucket[key] = {"key": key, "title": title, "builder": builder, **meta}


def list_scenes(domain: str) -> tuple[str, ...]:
    return tuple(_SCENE_REGISTRIES.get(domain, {}).keys())


def get_scene(domain: str, key: str) -> dict[str, Any]:
    bucket = _SCENE_REGISTRIES.get(domain) or {}
    scene = (key or "").strip()
    if scene not in bucket:
        raise KeyError(f"{domain} scene 须为：{', '.join(bucket) or '(empty)'}")
    return bucket[scene]


__all__ = [
    "strip_think",
    "parse_json_blob",
    "_strip_think",
    "_parse_json_blob",
    "AiDraftSteps",
    "run_ai_draft_pipeline",
    "register_scene",
    "list_scenes",
    "get_scene",
]
