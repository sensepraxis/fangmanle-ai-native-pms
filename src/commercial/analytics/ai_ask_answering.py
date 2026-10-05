# SPDX-License-Identifier: BUSL-1.1
"""AI 问数 · 回答生成（模板 / LLM / catalog / finalize）。"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from analytics.ask_catalog import FOLLOWUP_INTENTS, INTENT_CATALOG, get_intent, is_followup_intent
from analytics.ask_domain import COMPOSITE_INTENTS, default_questions_dynamic, glossary_active
from analytics.ask_pii import role_can_access_pii
from analytics.ask_playbook import filter_playbook_ids
from commercial.ai_core.prompt_packs import get_ask_system
from commercial.analytics.ai_ask_session import MAX_CLARIFY_ROUNDS, _touch_session
from commercial.analytics.ask_data_service import _extract_issues_json, _strip_think
from infra.i18n import t
from models import AiAskQuery

ASK_LLM_OPTS = {"temperature": 0.2, "top_p": 0.85, "max_tokens": 600, "think": False}


def _answer_system(*, followup: bool = False) -> str:
    from commercial.analytics.analytics_ai_locale import is_en_locale

    packed = get_ask_system(followup=followup)
    if packed:
        return packed
    if is_en_locale():
        return ANSWER_SYSTEM_FOLLOWUP_EN if followup else ANSWER_SYSTEM_EN
    return ANSWER_SYSTEM_FOLLOWUP if followup else ANSWER_SYSTEM


ANSWER_SYSTEM = """你是酒店 BI 问数的"回答生成器"。任务：基于【查询结果】用大白话回答用户的问题，只说结果里有的数字。
硬规则：
1. 只引用【查询结果】中的字段与数值；结果没有的写 "unknown"，禁止编造。
2. 输出纯 JSON：{"summary":"一句话结论","key_points":["≤3条要点"],"chart":{"type":"bar|line|pie|none","title":"","series":[]},"pii_mask":true/false,"confidence":"高|中|低"}
3. 不给出调价/改库存等执行建议（那是价格助手的事）。
4. 若 result 含 pii_mask/need_pii_ack，summary 只能引用脱敏字段（GUEST-xxxx、某某先生、金额），禁止真名/手机号。
5. 若 result 为空或 empty=true，summary 写"暂未查到相关数据"，key_points 为空。
"""

ANSWER_SYSTEM_FOLLOWUP = """你是酒店 BI 问数的"回答生成器"。任务：基于【上一轮结论】和【本轮查询结果】回答用户当前的追问。
硬规则：
1. 只引用【上一轮结论】和【本轮查询结果】中的字段与数值；无则写 "unknown"
2. 若本轮是追问意图（followup_*），优先用 playbook / tips 规则；不允许编造 playbook 之外的招数
3. 不出现改价/改库存等执行建议（那是价格助手的事）
4. 输出 JSON：{"summary":"一句话结论","key_points":["≤3条要点"],"chart":{"type":"bar|line|pie|none","title":"","series":[]},"playbook_used":["tip_id",...],"confidence":"高|中|低"}
"""

ANSWER_SYSTEM_EN = """You are a hotel BI Q&A answerer. Using ONLY the query result, answer in plain English.
Hard rules:
1. Cite only fields/numbers in the query result; use "unknown" if missing — never invent.
2. Output pure JSON: {"summary":"one sentence","key_points":["≤3 bullets"],"chart":{"type":"bar|line|pie|none","title":"","series":[]},"pii_mask":true/false,"confidence":"high|medium|low"}
3. No pricing/inventory execution advice (that is the pricing assistant).
4. If result has pii_mask/need_pii_ack, summary may only use masked fields (GUEST-xxxx, Mr/Ms X, amounts) — never real name/phone.
5. If result is empty or empty=true, summary = "No related data found", key_points = [].
6. All user-visible strings (summary, key_points, chart.title) MUST be English.
"""

ANSWER_SYSTEM_FOLLOWUP_EN = """You are a hotel BI Q&A answerer for follow-ups. Use the prior conclusion and this result; answer in English.
Hard rules:
1. Cite only prior conclusion + this result; else "unknown".
2. For followup_* intents, prefer playbook/tips — do not invent tips outside playbook.
3. No pricing/inventory execution advice.
4. Output JSON: {"summary":"one sentence","key_points":["≤3"],"chart":{"type":"bar|line|pie|none","title":"","series":[]},"playbook_used":["tip_id",...],"confidence":"high|medium|low"}
5. All user-visible strings MUST be English.
"""


def _normalize_confidence(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("high", "高", "高置信"):
        return "high"
    if s in ("low", "低", "低置信"):
        return "low"
    return "medium"


# LLM 偶发夹带中文术语时，EN Locale 下替换为英文业务词
_EN_TERM_FIXES: tuple[tuple[str, str], ...] = (
    ("OTA占比", "OTA share"),
    ("OTA 占比", "OTA share"),
    ("间夜占比", "room-night share"),
    ("直订率", "direct booking rate"),
    ("入住率", "occupancy"),
    ("复购率", "repurchase rate"),
    ("进项票认证", "input VAT invoice certification"),
    ("进项票及时认证", "certify input VAT invoices promptly"),
)


def _localize_answer_text(text: str) -> str:
    from commercial.analytics.analytics_ai_locale import is_en_locale

    s = str(text or "")
    if not s or not is_en_locale():
        return s
    for zh, en in _EN_TERM_FIXES:
        if zh in s:
            s = s.replace(zh, en)
    # H先生 / 王女士 → Mr. H / Ms. 王
    s = re.sub(r"([\w\u4e00-\u9fff])先生", r"Mr. \1", s)
    s = re.sub(r"([\w\u4e00-\u9fff])女士", r"Ms. \1", s)
    s = re.sub(r"([\w\u4e00-\u9fff])小姐", r"Ms. \1", s)
    return s


def _hash_snap(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _template_answer(intent_id: str, result: dict, slots: dict) -> dict:
    from commercial.analytics.ai_ask_answer_templates import get_answer_template

    if result.get("empty"):
        return {
            "summary": t("暂未查到相关数据"),
            "key_points": [],
            "chart": {"type": "none", "title": "", "series": []},
            "confidence": "low",
            "source": "template",
        }
    rows = result.get("rows") or []
    fn = get_answer_template(intent_id)
    if fn:
        summary, points = fn(result, slots)
    else:
        summary = result.get("title") or t("查询完成")
        points = [f"{r.get('label')}: {r.get('value')}" for r in rows[:3]]

    series = [
        {"name": r.get("guest_name") or r.get("label"), "value": r.get("value")}
        for r in rows
        if isinstance(r.get("value"), (int, float))
    ]
    out = {
        "summary": _localize_answer_text(summary),
        "key_points": [_localize_answer_text(str(p)) for p in points],
        "chart": {"type": "bar" if series else "none", "title": result.get("title") or "", "series": series},
        "confidence": "medium",
        "source": "template",
    }
    if intent_id == "followup_optimize":
        tips = result.get("playbook_tips") or []
        out["playbook_used"] = [t.get("id") for t in tips if t.get("id")]
        out["tips"] = tips
    return out


def _chart_from_result(result: dict) -> dict:
    rows = result.get("rows") or []
    series = [
        {"name": r.get("guest_name") or r.get("label"), "value": r.get("value")}
        for r in rows
        if isinstance(r.get("value"), (int, float))
    ]
    return {"type": "bar" if series else "none", "title": result.get("title") or "", "series": series}


def _unavailable_answer(result: dict, err: str | None = None) -> dict:
    """查询数据仍返回；不把规则模板包装成 AI 回答。"""
    return {
        "summary": "",
        "key_points": [],
        "chart": _chart_from_result(result),
        "confidence": "",
        "source": "unavailable",
        "error": (err or "")[:240],
    }


def narrate_query_result(
    db: Session,
    question: str,
    result: dict,
    intent_label: str,
    iid: str,
    filled: dict,
    **llm_kwargs: Any,
) -> dict:
    """规则模板只作为模型素材；没有模型输出就不算 AI 回答。"""
    material = _template_answer(iid, result, filled)
    answer = _llm_answer(db, question, result, intent_label, material=material, **llm_kwargs)
    if answer.get("source") == "llm" and str(answer.get("summary") or "").strip():
        return answer
    return _unavailable_answer(result, answer.get("error"))


def intent_looks_like_freeform_tips(kps: list, tips: list[dict]) -> bool:
    """若要点与 playbook 名称几乎无关，视为可能乱编，用 playbook 覆盖。"""
    if not tips:
        return False
    names = [t.get("name") or "" for t in tips]
    hit = 0
    for kp in kps:
        s = str(kp)
        if any(n and n[:4] in s for n in names):
            hit += 1
    return hit == 0


def _parse_answer_text(text: str, *, prior_intent_id: Optional[str] = None) -> dict:
    obj = _extract_issues_json(_strip_think(text) if text else "")
    summary = str(obj.get("summary") or "").strip()
    if any(k in summary for k in ("调价", "改价", "降价", "涨价", "关房")):
        summary = re.sub(r"(建议|请).{0,20}(调价|改价|降价|涨价|关房).{0,30}", "", summary)
    kps = obj.get("key_points") if isinstance(obj.get("key_points"), list) else []
    chart = obj.get("chart") if isinstance(obj.get("chart"), dict) else {"type": "none", "title": "", "series": []}
    if chart.get("type") not in ("bar", "line", "pie", "none"):
        chart["type"] = "none"
    out = {
        "summary": _localize_answer_text(summary or t("暂未查到相关数据")),
        "key_points": [_localize_answer_text(str(x)) for x in kps[:3]],
        "chart": chart,
        "confidence": _normalize_confidence(obj.get("confidence")),
        "source": "llm",
    }
    claimed = obj.get("playbook_used") if isinstance(obj.get("playbook_used"), list) else []
    if prior_intent_id:
        tips = filter_playbook_ids(prior_intent_id, [str(x) for x in claimed])
        out["playbook_used"] = [tip["id"] for tip in tips]
        out["tips"] = tips
        # 若模型写了额外招数在 key_points，用 playbook 覆盖要点
        if tips and intent_looks_like_freeform_tips(kps, tips):
            out["key_points"] = [f"{tip['name']}: {tip['expected_impact']}" for tip in tips[:3]]
    return out


def _llm_answer(
    db: Session,
    question: str,
    result: dict,
    intent_label: str,
    *,
    followup: bool = False,
    prior_summary: str = "",
    prior_intent_id: Optional[str] = None,
    material: Optional[dict] = None,
) -> dict:
    from commercial.ai_core.llm_service import chat
    from commercial.analytics.analytics_ai_locale import is_en_locale

    payload = json.dumps(result, ensure_ascii=False, default=str)
    if followup:
        if is_en_locale():
            user = (
                f"[Follow-up] {question}\n[Intent] {intent_label}\n"
                f"[Prior conclusion] {prior_summary}\n"
                f"[This result] {payload}\n"
                "Output JSON only. User-visible strings must be English."
            )
        else:
            user = (
                f"【用户追问】{question}\n【意图】{intent_label}\n"
                f"【上一轮结论】{prior_summary}\n"
                f"【本轮查询结果】{payload}\n请输出 JSON。"
            )
        system = _answer_system(followup=True)
    else:
        if is_en_locale():
            user = (
                f"[Question] {question}\n[Intent] {intent_label}\n"
                f"[Query result] {payload}\n"
                "Output JSON only. User-visible strings must be English."
            )
        else:
            user = f"【用户原问题】{question}\n【意图】{intent_label}\n【查询结果】{payload}\n请输出 JSON。"
        system = _answer_system(followup=False)
    if material and isinstance(material, dict):
        excerpt = {"summary": material.get("summary"), "key_points": material.get("key_points")}
        user += (
            "\n【规则摘录·仅素材】"
            + json.dumps(excerpt, ensure_ascii=False)
            + "\n请基于【查询结果】自行组织白话，禁止把摘录当最终答案照抄。"
        )
    try:
        raw = chat(
            db,
            [{"role": "user", "content": user}],
            system,
            overrides={**ASK_LLM_OPTS, "think": True, "max_tokens": 900},
        )
        text = raw.get("content") if isinstance(raw, dict) else str(raw)
        out = _parse_answer_text(text, prior_intent_id=prior_intent_id if followup else None)
        out["model"] = (raw or {}).get("model") if isinstance(raw, dict) else None
        return out
    except Exception as e:
        return {"error": str(getattr(e, "detail", None) or e)[:200]}


def catalog_payload() -> dict:
    intents = [
        {
            "intent_id": iid,
            "intent_label": m["intent_label"],
            "group_name": m["group_name"],
            "required_slots": m.get("required_slots") or [],
            "is_default": bool(m.get("is_default")),
            "default_question": m.get("default_question"),
            "metric_id": m.get("metric_id"),
            "operator_id": m.get("operator_id"),
        }
        for iid, m in {**INTENT_CATALOG, **COMPOSITE_INTENTS}.items()
    ]
    followups = [
        {
            "intent_id": iid,
            "intent_label": m["intent_label"],
            "group_name": m["group_name"],
            "required_slots": m.get("required_slots") or [],
            "is_followup": True,
        }
        for iid, m in FOLLOWUP_INTENTS.items()
    ]
    return {
        "presets": default_questions_dynamic(),
        "intents": intents,
        "followups": followups,
        "glossary": [
            {
                "standard_term": g["standard_term"],
                "aliases": g.get("aliases") or [],
                "metric_id": g["metric_id"],
                "unit": g.get("unit"),
                "definition": g.get("definition"),
                "domain": g.get("domain"),
                "sample_query": g.get("sample_query"),
                "hot_score": g.get("hot_score") or 0,
            }
            for g in glossary_active(limit=30)
        ],
        "max_clarify_rounds": MAX_CLARIFY_ROUNDS,
    }


def _followup_confirm_payload(
    *,
    sid: str,
    row: AiAskQuery,
    intent_id: str,
    slots: dict,
    resolved: str,
    clarify_round: int,
    auto: bool = True,
) -> dict[str, Any]:
    from infra.i18n import t

    meta = get_intent(intent_id) or {}
    label = t(str(meta.get("intent_label") or intent_id))
    return {
        "status": "auto_execute" if auto else "confirm",
        "session_id": sid,
        "query_id": row.id,
        "intent_id": intent_id,
        "intent_label": label,
        "slots": slots,
        "resolved_question": resolved,
        "prompt": t("基于刚才的结论，你是想了解「{q}」吗？", q=label),
        "confidence": "高",
        "clarify_round": clarify_round,
        "is_followup": True,
        "parent_query_id": row.parent_query_id,
    }


def _finalize_answer(
    db: Session,
    row: AiAskQuery,
    iid: str,
    meta: dict,
    filled: dict,
    result: dict,
    answer: dict,
    *,
    parent_query_id: Optional[int] = None,
    role: Optional[str] = None,
) -> dict[str, Any]:
    from commercial.ai_core.llm_service import llm_identity, load_llm_config
    from extensions.llm.facade import resolve_model_name

    try:
        cfg = load_llm_config(db)
        identity = llm_identity(cfg, {"model": answer.get("model")} if answer.get("model") else None)
        model_name = resolve_model_name(cfg, res=answer if isinstance(answer, dict) else None)
    except Exception:
        identity = {}
        model_name = str((answer or {}).get("model") or resolve_model_name())
    tips = answer.get("tips") or result.get("playbook_tips") or []
    snap = {
        "intent_id": iid,
        "slots": filled,
        "result_metrics": result.get("metrics"),
        "playbook": [t.get("id") for t in tips],
    }
    row.result_json = json.dumps(result, ensure_ascii=False, default=str)
    row.answer_json = json.dumps(answer, ensure_ascii=False, default=str)
    row.playbook_tips = json.dumps(tips, ensure_ascii=False, default=str) if tips else None
    if parent_query_id:
        row.parent_query_id = parent_query_id
    row.snapshot_hash = _hash_snap(snap)
    src = answer.get("source") or "unavailable"
    used_llm = src == "llm"
    if not used_llm:
        identity = {}
        model_name = None
        row.model_name = None
    else:
        row.model_name = model_name
    db.commit()
    _touch_session(db, row.session_id, row.hotel_id)
    from infra.i18n import t as _t_fin

    intent_label = _t_fin(str(meta.get("intent_label") or "查询结果"))
    note = intent_label
    return {
        "status": "answered",
        "session_id": row.session_id,
        "query_id": row.id,
        "parent_query_id": row.parent_query_id,
        "intent_id": iid,
        "intent_label": intent_label,
        "slots": filled,
        "resolved_question": row.resolved_question,
        "result": result,
        "answer": answer,
        "tips": tips,
        "confirmed_at": row.confirmed_at.isoformat() + "Z" if row.confirmed_at else None,
        "snapshot_hash": row.snapshot_hash,
        "model_name": model_name,
        "answer_source": src,
        "note": note,
        "is_followup": is_followup_intent(iid),
        "pii_level": result.get("pii_level") or meta.get("pii_level") or "none",
        "need_pii_ack": bool(result.get("need_pii_ack")),
        "pii_accessed": bool(row.pii_accessed),
        "can_ack_pii": role_can_access_pii(role),
        **identity,
    }
