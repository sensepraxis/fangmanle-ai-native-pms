# SPDX-License-Identifier: BUSL-1.1
"""AI 叙事内核 · 统一 JSON 解析 / 双栏 HTML / 触发式 narrate 编排。

各域 `*_ai.py` 只保留：快照组装、规则兜底、action 归一化与写库执行。
产品约定见 `.cursor/rules/ai-narrative-ux.mdc`。
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from commercial.ai_core.llm_service import chat, llm_identity, load_llm_config

PolishFn = Callable[[dict[str, Any]], dict[str, Any]]
NormalizeActionsFn = Callable[[list], list[dict]]
FallbackFn = Callable[[], dict[str, Any]]


def extract_json(text: str) -> Optional[dict]:
    """从模型输出中提取第一个 JSON 对象（兼容 markdown 围栏）。"""
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def scrub_route_paths(text: str) -> str:
    """去掉文案中夹带的前端路由（如 /acquisition/...），避免展示给业务人员。

    先暂存 HTML 标签，避免把 ``</strong>`` 误当成路径削成 ``<>``。
    """
    s = str(text or "")
    holders: list[str] = []

    def _hold(m: re.Match) -> str:
        holders.append(m.group(0))
        return f"\x00H{len(holders) - 1}\x00"

    s = re.sub(r"</?[a-zA-Z][^>]*>", _hold, s)
    # 仅剥离应用路由形态（至少两段 path），勿匹配 /strong 之类
    s = re.sub(
        r"(?:\s*[（(]\s*)?(/(?:acquisition|analytics|pricing|orders|guests|finance|system|hk|c\d)[\w\-./?=&#%]*)(?:\s*[）)])?",
        "",
        s,
        flags=re.I,
    )
    s = re.sub(r"\s{2,}", " ", s).strip(" ，,;；·.-—")
    for i, html in enumerate(holders):
        s = s.replace(f"\x00H{i}\x00", html)
    return s


def format_insight_html(
    left_h: str,
    facts: list,
    right_h: str | None = None,
    suggestions: list | None = None,
) -> str:
    """事实 / 建议双栏 HTML（前端用 v-html 展示，禁止裸 JSON）。"""
    from infra.i18n import t as _t

    if right_h is None:
        right_h = _t("建议")
    fact_lis = "".join(f"<li>{scrub_route_paths(x)}</li>" for x in (facts or []) if scrub_route_paths(x))
    sug_lis = "".join(f"<li>{scrub_route_paths(x)}</li>" for x in (suggestions or []) if scrub_route_paths(x))
    if not fact_lis and not sug_lis:
        return ""
    parts = ['<div class="ai-insight">']
    if fact_lis:
        parts.append(
            f'<section class="ai-insight-sec fact"><div class="ai-insight-h">{left_h}</div>'
            f"<ul>{fact_lis}</ul></section>"
        )
    if sug_lis:
        parts.append(
            f'<section class="ai-insight-sec sug"><div class="ai-insight-h">{right_h}</div><ul>{sug_lis}</ul></section>'
        )
    parts.append("</div>")
    return "".join(parts)


def safe_path(path: Optional[str], allowed: list[str], default: str) -> str:
    """白名单路径校验；允许带 query 的同前缀路径。"""
    p = str(path or "").strip()
    if p in allowed:
        return p
    for a in allowed:
        base = a.split("?")[0]
        if p.startswith(base):
            return p if "?" in p or p == base else a
    return default


def confidence_of(parsed: dict, default: str = "medium") -> str:
    conf = str((parsed or {}).get("confidence") or default).lower()
    return conf if conf in ("high", "medium", "low") else default


def list_str(items: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(items, list):
        return []
    out = [str(x).strip() for x in items if str(x).strip()]
    return out[:limit]


def base_action(
    raw: dict,
    *,
    index: int,
    allowed_types: set[str] | frozenset[str],
    path_default: str,
    path_fn: Callable[[Optional[str], str], str] | None = None,
) -> dict[str, Any]:
    """抽取通用 action 字段；域内可再合并 payload。"""
    at = str(raw.get("action_type") or "open_path")
    if at not in allowed_types:
        at = "open_path"
    path = (path_fn or (lambda p, d: d))(raw.get("path"), path_default)
    return {
        "id": str(raw.get("id") or f"a{index + 1}"),
        "action_type": at,
        "action_label": str(raw.get("action_label") or "执行")[:48],
        "title": str(raw.get("title") or "建议动作")[:48],
        "body": str(raw.get("body") or "")[:120],
        "path": path,
    }


def run_narrate(
    db: Session,
    *,
    kind: str,
    meta: dict[str, Any],
    user_prompt: str,
    build_fallback: FallbackFn,
    normalize_actions: NormalizeActionsFn,
    polish: PolishFn | None = None,
    overrides: dict[str, Any] | None = None,
    extra_success: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """规则摘录只进 prompt 当素材；用户可见结论必须来自 LLM，否则 source=unavailable。"""
    from commercial.ai_core.prompt_packs import get_scene_prompt
    from infra.i18n import t as _t

    label = str(meta.get("label") or kind)
    left_h = str(meta.get("left_h") or _t("事实"))
    right_h = str(meta.get("right_h") or _t("建议"))
    system = str(meta.get("system") or "")
    pd, ps = meta.get("prompt_domain"), meta.get("prompt_scene")
    if pd and ps:
        packed = get_scene_prompt(str(pd), str(ps))
        if packed:
            system = packed

    cfg = load_llm_config(db)
    fallback = dict(build_fallback() or {})
    facts_only = [str(x) for x in (fallback.get("facts") or []) if str(x).strip()]

    def _unavailable(err: str = "") -> dict[str, Any]:
        return {
            "kind": kind,
            "label": label,
            "narrative_html": "",
            "facts": facts_only,
            "suggestions": [],
            "actions": [],
            "source": "unavailable",
            "llm_error": (err or "")[:200],
        }

    if not cfg.get("enabled", True):
        return _unavailable(_t("大模型未启用"))

    excerpt = {
        "facts": facts_only[:8],
        "suggestions": list(fallback.get("suggestions") or [])[:6],
        "summary": str(fallback.get("summary") or "")[:200],
    }
    material = (
        "\n\n【规则摘录·仅素材】须基于数据重写 JSON 回答，禁止把摘录当最终答复原文。\n"
        + json.dumps(excerpt, ensure_ascii=False, default=str)[:4000]
    )

    llm_opts = {"temperature": 0.3, "max_tokens": 1600, "think": False}
    if overrides:
        llm_opts.update(overrides)

    try:
        res = chat(
            db,
            [{"role": "user", "content": user_prompt + material}],
            extra_system=system,
            overrides=llm_opts,
        )
        parsed = extract_json(res.get("content") or "") or {}
        fact_list = [scrub_route_paths(x) for x in list_str(parsed.get("facts"))]
        fact_list = [x for x in fact_list if x]
        sug_list = [scrub_route_paths(x) for x in list_str(parsed.get("suggestions"))]
        sug_list = [x for x in sug_list if x]
        html = format_insight_html(left_h, fact_list, right_h, sug_list)
        if not html:
            return _unavailable(_t("模型未返回可用内容"))

        out: dict[str, Any] = {
            "kind": kind,
            "label": label,
            "narrative_html": html,
            "facts": fact_list,
            "suggestions": sug_list,
            "actions": normalize_actions(parsed.get("actions") or []),
            "confidence": confidence_of(parsed),
            "confidence_note": str(parsed.get("confidence_note") or "")[:120],
            "source": "llm",
            **llm_identity(cfg, res),
        }
        if extra_success:
            out.update(extra_success)
        if polish:
            out = polish(out)
        return out
    except HTTPException as e:
        return _unavailable(str(e.detail) if hasattr(e, "detail") else str(e))
    except Exception as e:
        return _unavailable(str(e)[:200])
