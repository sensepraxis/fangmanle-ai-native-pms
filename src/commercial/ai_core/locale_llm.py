# SPDX-License-Identifier: BUSL-1.1
"""Locale-aware LLM JSON 调用 · Template Method。

固定步骤（各 scene 不得再复制）：
1. ``compose_system`` 追加 ``language_instruction()``（跟 X-Locale，禁止写死「必须中文」）
2. ``llm_chat``
3. ``parse_llm_json``（含截断补全）
4. 失败则 locale 化 retry
5. 调用方 ``normalize``；可见字符串用 ``locale_text`` 做 EN+CJK 兜底

Scene 只提供 system / user / retry 文案与 normalize。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.ai_harness_base import parse_json_blob, strip_think
from infra.i18n import get_locale, t

CJK_RE = re.compile(r"[\u4e00-\u9fff]")

ChatFn = Callable[..., dict[str, Any]]


def wants_en(locale: Optional[str] = None) -> bool:
    return str(locale or get_locale() or "").lower().startswith("en")


def clip_text(s: Any, n: int) -> str:
    text = str(s or "").strip()
    if n <= 0 or len(text) <= n:
        return text
    return text[: n - 1] + "…"


def locale_text(
    raw: Any,
    fallback: str,
    n: int = 160,
    *,
    polish: Optional[Callable[[str], str]] = None,
) -> str:
    """可见字符串跟 Locale：EN 且含汉字 → msgid 兜底。"""
    s = clip_text(raw, n)
    if wants_en() and s and CJK_RE.search(s):
        return t(fallback)
    if polish and s:
        s = polish(s)
    return s or t(fallback)


def locale_optional(raw: Any, n: int = 200) -> Optional[str]:
    s = clip_text(raw, n)
    if not s:
        return None
    if wants_en() and CJK_RE.search(s):
        return None
    return s


def locale_str_list(items: Any, *, limit: int = 4, n: int = 80) -> Optional[list[str]]:
    if not isinstance(items, list) or not items:
        return None
    out = [clip_text(x, n) for x in items[:limit]]
    out = [x for x in out if x]
    if not out:
        return None
    if wants_en() and any(CJK_RE.search(x) for x in out):
        return None
    return out


def compose_system(*parts: str, locale: Optional[str] = None) -> str:
    """拼接 scene system，并保证 language_instruction 只出现一次。"""
    from commercial.ai_core.prompt_packs import language_instruction

    body = "\n\n".join(p.strip() for p in parts if str(p or "").strip())
    lang = language_instruction(locale)
    if lang and lang not in body:
        body = f"{body}\n\n{lang}".strip() if body else lang
    return body


def retry_instruction() -> str:
    if wants_en():
        return "Output complete parseable JSON once. No thinking. All narrative strings in English."
    return "务必一次输出完整可解析 JSON，不要思考过程。"


def _close_truncated_json(blob: str) -> str:
    s = blob.rstrip().rstrip(",")
    in_str = False
    escape = False
    stack: list[str] = []
    out: list[str] = []
    for ch in s:
        out.append(ch)
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]") and stack and stack[-1] == ch:
            stack.pop()
    if in_str:
        out.append('"')
    closed = "".join(out).rstrip()
    while closed and closed[-1] in ",:":
        closed = closed[:-1].rstrip()
    while stack:
        closed += stack.pop()
    return re.sub(r",(\s*[}\]])", r"\1", closed)


def _slice_json_blob(text: str) -> str:
    raw = strip_think(text)
    raw = re.sub(r"</?think[^>]*>", "", raw, flags=re.I)
    if not raw:
        return ""
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                raw = p
                break
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0:
        return ""
    if end > start:
        return raw[start : end + 1]
    return raw[start:]


def parse_llm_json(text: str) -> Optional[dict[str, Any]]:
    """提取 JSON object；支持思考链、围栏、截断补全。失败返回 None。"""
    hit = parse_json_blob(text)
    if isinstance(hit, dict):
        return hit
    blob = _slice_json_blob(text)
    if not blob:
        return None
    candidates = [blob, _close_truncated_json(blob)]
    for m in re.finditer(r"\}", blob):
        candidates.append(_close_truncated_json(blob[: m.end()]))
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


@dataclass
class LocaleLlmResult:
    parsed: dict[str, Any]
    raw: str
    model: str
    error: Optional[str] = None


def run_locale_llm_json(
    db: Session,
    *,
    system: str,
    user: str,
    retry_user: Optional[str] = None,
    overrides: Optional[dict[str, Any]] = None,
    retry_overrides: Optional[dict[str, Any]] = None,
    chat_fn: Optional[ChatFn] = None,
) -> LocaleLlmResult:
    """Template Method：system(+语言) → chat → parse → 可选 retry。"""
    from commercial.ai_core.llm_service import chat as llm_chat

    chat = chat_fn or llm_chat
    sys_text = compose_system(system)
    raw = ""
    model = ""
    parsed: Optional[dict[str, Any]] = None
    err: Optional[str] = None
    try:
        res = chat(db, [{"role": "user", "content": user}], sys_text, overrides=overrides)
        raw = str((res or {}).get("content") or "")
        model = str((res or {}).get("model") or "")
        parsed = parse_llm_json(raw)
        if parsed is None and retry_user:
            res2 = chat(
                db,
                [{"role": "user", "content": retry_user}],
                compose_system(sys_text, retry_instruction()),
                overrides=retry_overrides or overrides,
            )
            extra = str((res2 or {}).get("content") or "")
            model = str((res2 or {}).get("model") or model)
            raw = (raw + "\n\n---RETRY---\n\n" + extra)[:8000]
            parsed = parse_llm_json(extra) or parse_llm_json(raw)
        if parsed is None:
            err = t("JSON 解析失败")
            parsed = {}
    except Exception as e:
        err = str(getattr(e, "detail", None) or e)[:200]
        parsed = parsed or {}
    return LocaleLlmResult(parsed=parsed or {}, raw=raw, model=model, error=err)
