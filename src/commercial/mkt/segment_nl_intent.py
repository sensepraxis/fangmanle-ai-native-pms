# SPDX-License-Identifier: BUSL-1.1
"""
AI 找人：LLM 意图识别 → FilterSpec（标签/条件表达式）。
不生成可执行 SQL；SQL 仍由 segment_sql.filter_spec_to_sql 确定性编译。
LLM 不可用或解析失败时回退规则引擎 parse_nl_to_filter。
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from models import TagDefinition

ALLOWED_ORDER_STATUS = {"cancelled", "no_show", "checked_out", "checked_in", "reserved"}
ALLOWED_WINDOWS = {7, 14, 30, 60, 90, 180, 365}


def _segment_nl_system(catalog_txt: str) -> str:
    from commercial.ai_core.prompt_packs import get_scene_prompt

    template = get_scene_prompt("segment", "nl_intent")
    if not template:
        raise RuntimeError("segment.nl_intent prompt pack missing")
    return template.replace("__TAG_CATALOG__", catalog_txt)


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("模型返回为空")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        return json.loads(fenced.group(1))
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        return json.loads(m.group(0))
    raise ValueError("未找到 JSON")


def list_tag_catalog(db: Session) -> list[dict[str, str]]:
    from infra.i18n import t as _t

    rows = db.query(TagDefinition).order_by(TagDefinition.id.asc()).all()
    # name 走 msgid，保证 EN Locale 下目录/提示词是英文，避免模型跟中文标签名
    out = [{"code": (row.code or "").lower(), "name": _t(row.name or row.code or "")} for row in rows if row.code]
    known = {
        "business": _t("商务常旅客"),
        "family": _t("亲子家庭"),
        "repeat": _t("复购客"),
        "vip": "VIP",
        "high_value": _t("高价值客户"),
        "pref_quiet_high_floor": _t("偏好高层安静房"),
        "active_90d": _t("近90天高活跃"),
    }
    have = {x["code"] for x in out}
    for code, name in known.items():
        if code not in have:
            out.append({"code": code, "name": name})
    return out


def _normalize_spec(raw: dict[str, Any], query: str, allowed_codes: set[str]) -> dict[str, Any]:
    window = int(raw.get("window_days") or 90)
    if window not in ALLOWED_WINDOWS:
        window = min(ALLOWED_WINDOWS, key=lambda x: abs(x - window))

    statuses: list[str] = []
    for s in raw.get("order_status") or []:
        s = str(s).strip().lower()
        if s in ALLOWED_ORDER_STATUS and s not in statuses:
            statuses.append(s)

    tags: list[str] = []
    for t in raw.get("tag_codes_any") or []:
        c = str(t).strip().lower()
        if c in allowed_codes and c not in tags:
            tags.append(c)

    min_stays = raw.get("min_stays")
    try:
        min_stays = int(min_stays) if min_stays is not None else None
        if min_stays is not None and min_stays < 1:
            min_stays = None
    except (TypeError, ValueError):
        min_stays = None

    min_nights = raw.get("min_nights")
    try:
        min_nights = int(min_nights) if min_nights is not None else None
        if min_nights is not None and min_nights < 1:
            min_nights = None
    except (TypeError, ValueError):
        min_nights = None

    from infra.i18n import t as _t

    meaning = str(raw.get("meaning") or "").strip()
    expression = str(raw.get("expression") or "").strip()
    if not expression:
        parts = [_t("近{n}天", n=window)]
        if statuses:
            parts.append("status=" + "|".join(statuses))
        for code in tags:
            parts.append(f"tag:{code}")
        if min_stays:
            parts.append(f"stays>={min_stays}")
        if min_nights:
            parts.append(f"nights>={min_nights}")
        if raw.get("require_children_orders"):
            parts.append("require_children")
        if raw.get("prefer_high_floor"):
            parts.append("prefer_high_floor")
        if raw.get("weekend_bias"):
            parts.append("weekend_bias")
        if raw.get("quiet_pref"):
            parts.append("quiet_pref")
        expression = " AND ".join(parts)

    if not meaning:
        meaning = expression
    else:
        meaning = _t(meaning)

    return {
        "query": query,
        "window_days": window,
        "order_status": statuses,
        "tag_codes_any": tags,
        "min_stays": min_stays,
        "min_nights": min_nights,
        "require_children_orders": bool(raw.get("require_children_orders")),
        "prefer_high_floor": bool(raw.get("prefer_high_floor")),
        "weekend_bias": bool(raw.get("weekend_bias")),
        "quiet_pref": bool(raw.get("quiet_pref")),
        "meaning": meaning,
        "expression": expression,
    }


def llm_parse_to_filter(db: Session, query: str) -> dict[str, Any]:
    """调用已配置 LLM，返回规范化 FilterSpec；失败抛异常。"""
    from commercial.ai_core.llm_service import chat as llm_chat

    catalog = list_tag_catalog(db)
    allowed = {x["code"] for x in catalog}
    from commercial.analytics.analytics_ai_locale import is_en_locale
    from infra.i18n import t as _t

    catalog_txt = "\n".join(f"- {x['code']}: {x['name']}" for x in catalog)
    system = _segment_nl_system(catalog_txt)

    if is_en_locale():
        user = (
            f"Audience description: {query}\n\nOutput FilterSpec JSON only. meaning/expression labels must be English."
        )
    else:
        user = _t("客群描述：{q}\n\n请输出 FilterSpec JSON。", q=query)
    res = llm_chat(
        db,
        [{"role": "user", "content": user}],
        extra_system=system,
    )
    parsed = _extract_json(res.get("content") or "")
    if not isinstance(parsed, dict):
        raise ValueError("意图 JSON 不是对象")
    spec = _normalize_spec(parsed, query, allowed)
    spec["_intent_model"] = res.get("model")
    spec["_intent_provider"] = res.get("provider")
    return spec


def _rules_fallback(query: str, reason: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    from guests.nl_filter import parse_nl_to_filter
    from infra.i18n import t as _t

    q = (query or "").strip()
    spec = parse_nl_to_filter(q)
    parts = [_t("近{n}天", n=spec.get("window_days") or 90)]
    if spec.get("order_status"):
        parts.append("status=" + "|".join(spec["order_status"]))
    for code in spec.get("tag_codes_any") or []:
        parts.append(f"tag:{code}")
    if spec.get("min_stays"):
        parts.append(f"stays>={spec['min_stays']}")
    if spec.get("min_nights"):
        parts.append(f"nights>={spec['min_nights']}")
    if spec.get("require_children_orders"):
        parts.append("require_children")
    if spec.get("prefer_high_floor"):
        parts.append("prefer_high_floor")
    if spec.get("quiet_pref"):
        parts.append("quiet_pref")
    expr = " AND ".join(parts)
    spec["expression"] = expr
    spec["meaning"] = expr
    meta = {
        "intent_source": "rules",
        "intent_expr": expr,
        "intent_meaning": expr,
        "intent_fallback_reason": (reason or "")[:200],
    }
    return spec, meta


def resolve_filter_spec(db: Session, query: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    LLM 优先 → 规则兜底。
    返回 (filter_spec, meta)。
    """
    q = (query or "").strip()

    try:
        from commercial.ai_core.llm_service import llm_identity, load_llm_config

        cfg = load_llm_config(db)
        if not cfg.get("enabled", True):
            raise RuntimeError("LLM 已禁用")
        spec = llm_parse_to_filter(db, q)
        identity = llm_identity(
            cfg,
            {
                "model": spec.pop("_intent_model", None),
                "provider": spec.pop("_intent_provider", None),
            },
        )
        meta = {
            "intent_source": "llm",
            "intent_expr": spec.get("expression") or "",
            "intent_meaning": spec.get("meaning") or "",
            "intent_model": identity.get("model"),
            "intent_provider": identity.get("provider"),
            **identity,
        }
        return spec, meta
    except Exception as e:
        return {}, {
            "intent_source": "unavailable",
            "intent_expr": "",
            "intent_meaning": "",
            "intent_fallback_reason": str(e)[:200],
        }


def stream_nl_segment_query(db: Session, hotel_id: int, query: str):
    """
    SSE 事件流：
    - stage: 阶段文案
    - token: LLM 增量文本
    - done: 最终结果（与非流式 nl-query data 同结构）
    - error: 不可恢复错误（极少；多数走规则兜底后仍 done）
    """
    from bootstrap.ensure_nl_segment import seed_nl_cancel_demo
    from commercial.ai_core.llm_service import chat_stream, llm_identity, load_llm_config
    from commercial.analytics.analytics_ai_locale import is_en_locale
    from guests.nl_filter import query_nl_guests
    from infra.i18n import t as _t

    q = (query or "").strip()
    if not q:
        yield {"type": "error", "message": _t("请输入客群描述")}
        return

    yield {"type": "stage", "content": _t("准备数据…")}
    seed_nl_cancel_demo(db, hotel_id)

    spec: dict[str, Any] | None = None
    meta: dict[str, Any] = {}

    try:
        cfg = load_llm_config(db)
        if not cfg.get("enabled", True):
            raise RuntimeError("LLM 已禁用")

        catalog = list_tag_catalog(db)
        allowed = {x["code"] for x in catalog}
        catalog_txt = "\n".join(f"- {x['code']}: {x['name']}" for x in catalog)
        system = _segment_nl_system(catalog_txt)

        yield {"type": "stage", "content": _t("大模型意图识别中…")}
        if is_en_locale():
            user = (
                f"Audience description: {q}\n\n"
                "First write a one-line Intent in English, then output FilterSpec JSON. "
                "meaning must be English."
            )
        else:
            user = _t("客群描述：{q}\n\n请先写「意图：…」，再输出 FilterSpec JSON。", q=q)
        full = ""
        for chunk in chat_stream(
            db,
            [{"role": "user", "content": user}],
            extra_system=system,
        ):
            full += chunk
            yield {"type": "token", "content": chunk}

        parsed = _extract_json(full)
        if not isinstance(parsed, dict):
            raise ValueError("意图 JSON 不是对象")
        spec = _normalize_spec(parsed, q, allowed)
        identity = llm_identity(cfg)
        meta = {
            "intent_source": "llm",
            "intent_expr": spec.get("expression") or "",
            "intent_meaning": spec.get("meaning") or "",
            "intent_model": identity.get("model"),
            "intent_provider": identity.get("provider"),
            "intent_raw": full[:4000],
            **identity,
        }
    except Exception as e:
        yield {
            "type": "error",
            "message": _t("未能调用大模型，未生成客群意图（规则不会冒充 AI）。{err}", err=str(e)[:80]),
        }
        return

    yield {"type": "stage", "content": _t("按条件查库匹配客人…")}
    result = query_nl_guests(db, hotel_id, q, spec=spec)
    result.update(meta)
    yield {"type": "done", "data": result}
