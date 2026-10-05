# SPDX-License-Identifier: BUSL-1.1
"""私域 AI · Locale 辅助：kind 元数据、user prompt、代码词本地化。

约定：msgid 保持中文；展示/喂模型时用 t()；EN 下勿把英文码强制译回中文。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


def is_en_locale() -> bool:
    from infra.i18n import get_locale

    return str(get_locale() or "").lower().startswith("en")


def kind_meta(kinds: dict[str, dict], kind: str) -> dict[str, Any]:
    """复制 NARRATIVE_KINDS 条目并对 label/left_h/right_h/btn 做 t()。"""
    from infra.i18n import t

    raw = dict(kinds[kind])
    for k in ("label", "left_h", "right_h", "btn"):
        if raw.get(k):
            raw[k] = t(str(raw[k]))
    return raw


def narrate_user_prompt(
    *,
    label: str,
    allowed_paths: list[str],
    snapshot: Any,
) -> str:
    """组装触发式 narrate 的 user 消息（跟当前 locale）。"""
    paths = json.dumps(allowed_paths, ensure_ascii=False)
    snap = json.dumps(snapshot, ensure_ascii=False, default=str)
    if is_en_locale():
        return (
            f"Task: produce «{label}».\n"
            f"actions.path must be chosen only from this whitelist "
            f"(do not put paths in facts/suggestions body): {paths}\n"
            f"Snapshot:\n{snap}"
        )
    return (
        f"任务：生成「{label}」。\n"
        f"actions.path 仅可从以下白名单选取（不要写进 facts/suggestions 正文）：{paths}\n"
        f"快照：\n{snap}"
    )


def localize_machine_codes(text: Any, replacements: list[tuple[str, str]]) -> str:
    """仅在中文 locale 下把机器码替换为中文可读标签；EN 原样返回。"""
    s = str(text or "")
    if not s:
        return ""
    if is_en_locale():
        return s
    for en, zh in replacements:
        s = re.sub(re.escape(en), zh, s, flags=re.I)
    return s


def localize_insight_payload(
    data: dict[str, Any],
    *,
    replacements: list[tuple[str, str]],
) -> dict[str, Any]:
    out = dict(data or {})
    if is_en_locale():
        return out

    def _one(v: Any) -> str:
        return localize_machine_codes(v, replacements)

    if out.get("narrative_html"):
        out["narrative_html"] = _one(out["narrative_html"])
    out["facts"] = [_one(x) for x in (out.get("facts") or [])]
    out["suggestions"] = [_one(x) for x in (out.get("suggestions") or [])]
    if out.get("confidence_note"):
        out["confidence_note"] = _one(out["confidence_note"])
    actions = []
    for a in out.get("actions") or []:
        if not isinstance(a, dict):
            continue
        item = dict(a)
        for k in ("action_label", "title", "body"):
            if item.get(k):
                item[k] = _one(item[k])
        actions.append(item)
    if actions:
        out["actions"] = actions
    return out
