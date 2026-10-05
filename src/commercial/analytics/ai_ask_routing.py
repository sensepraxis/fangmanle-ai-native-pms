# SPDX-License-Identifier: BUSL-1.1
"""AI 问数 · 意图路由（Tier0 / LLM / 澄清 / 追问）。"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from analytics.ask_catalog import (
    ACTION_KEYWORDS,
    FOLLOWUP_INTENTS,
    INTENT_CATALOG,
    PERIOD_ALIASES,
    all_intent_ids,
    get_intent,
    intent_list_for_prompt,
)
from analytics.ask_domain import (
    decompose_route,
    default_questions_dynamic,
    extract_top_n,
    glossary_for_prompt,
    infer_baseline_from_text,
    normalize,
)
from analytics.ask_playbook import FOLLOWUP_KEYWORDS, PRONOUN_MARKERS, tips_for
from commercial.analytics.ai_ask_answering import ASK_LLM_OPTS, _followup_confirm_payload
from commercial.analytics.ai_ask_session import (
    MAX_CLARIFY_ROUNDS,
    MAX_HISTORY_TURNS,
    _touch_session,
    load_session_turns,
)
from commercial.analytics.ask_data_service import _extract_issues_json
from models import AiAskQuery, Hotel

ROUTE_SYSTEM = """你是一名酒店 BI 问数的"意图路由器"。任务：把用户的中文问题，匹配到下方【意图清单】中唯一一个 intent_id，并抽取所需参数(slots)。
酒店背景：约120间房、散客为主的单体/小型连锁酒店。

硬规则：
1. intent_id 必须从清单选，禁止自造；都不匹配输出 "unknown"。
2. slots 只填清单"必填槽"要求的字段；时间缺失时 period 填 "unknown" 待澄清。
3. 输出纯 JSON，不要代码块标记、不要解释、不要思考过程。
4. confidence 用 高/中/低；多意图并列时 candidates 给 2–3 个。
5. 若用户问题实际是"改价/改库存"等操作而非问数，intent_id 填 "action_not_question"。

【意图清单】
{{intent_list}}

输出 JSON：
{"resolved_question":"...","intent_id":"...","intent_label":"...","slots":{"period":"...","horizon":"..."},"confidence":"高|中|低","candidates":["id",...],"clarify":""}
"""

ROUTE_SYSTEM_MULTI = """你是一名酒店 BI 问数的「查询归一化器 + 指代消解器 + 意图路由器」。
酒店：约120间房、散客为主的单体/小型连锁酒店。

[业务术语小词典]
{{glossary}}

[算子清单]
- op_get_value: 现在的值是多少
- op_compare_baseline: 对比/同比/环比
- op_trend: 趋势/走势
- op_rank_top: TopN/排名
- op_breakdown: 拆解/明细

[任务]
第一步【查询归一化】按词典改写为 standard_term，输出 normalized_question。
第二步【指代消解】解析代词，输出 resolved_question。
第三步【意图分类】从【意图清单】选 intent_id 并抽 slots。

[意图清单]
{{intent_list}}
- action_not_question / unknown

硬规则：
1. intent_id 必须从清单选；都不匹配输出 "unknown"
2. 追问意图 followup_* 仅在对话历史非空时使用
3. 输出纯 JSON：{"normalized_question":"...","resolved_question":"...","metric_id":"...","operator_id":"...","intent_id":"...","intent_label":"...","slots":{...},"confidence":"高|中|低","candidates":["id",...],"clarify":"..."}
"""


def _extract_period_from_text(q: str) -> Optional[str]:
    for k, v in PERIOD_ALIASES.items():
        if k in q:
            labels = {"week": "本周", "month": "本月", "quarter": "本季", "custom": "自定义"}
            return labels.get(v, "本月")
    return None


def _extract_horizon_from_text(q: str) -> Optional[int]:
    if re.search(r"7|七|一周|下周", q):
        return 7
    if re.search(r"30|三十|一月|下月", q):
        return 30
    return None


def has_pronoun_reference(question: str) -> bool:
    q = question or ""
    return any(m in q for m in PRONOUN_MARKERS)


def detect_followup_intent(question: str) -> Optional[str]:
    q = question or ""
    # 更具体的优先
    order = ("followup_diagnose", "followup_compare", "followup_optimize", "followup_impact")
    for iid in order:
        kws = FOLLOWUP_KEYWORDS.get(iid) or []
        if any(k in q for k in kws):
            return iid
    return None


def rule_resolve_question(question: str, turns: list[dict], followup_id: Optional[str] = None) -> str:
    q = (question or "").strip()
    if not turns:
        return q
    last = turns[-1]
    prior = last.get("result_summary") or last.get("intent_label") or last.get("q") or "上一轮结论"
    if followup_id == "followup_optimize":
        return f"针对「{prior}」，如何优化或改善？"
    if followup_id == "followup_impact":
        return f"针对「{prior}」，会带来什么影响或后果？"
    if followup_id == "followup_diagnose":
        return f"针对「{prior}」，主要原因是什么？"
    if followup_id == "followup_compare":
        return f"针对「{prior}」，与对比期/对照项相比如何？"
    if has_pronoun_reference(q):
        return f"关于「{prior}」：{q}"
    return q


def tier0_candidates(question: str) -> list[str]:
    q = question or ""
    ql = q.lower()
    if any(k in q for k in ACTION_KEYWORDS):
        return ["action_not_question"]
    out: list[str] = []
    for iid, meta in INTENT_CATALOG.items():
        kws = meta.get("keywords") or []
        if any((k.lower() in ql) or (k in q) for k in kws):
            out.append(iid)
    seen = set()
    uniq = []
    for i in out:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return uniq


def missing_slot(intent_id: str, question: str, slots: dict, period_preset: str) -> Optional[str]:
    meta = get_intent(intent_id)
    if not meta:
        return None
    required = meta.get("required_slots") or []
    if "horizon" in required:
        if slots.get("horizon") or _extract_horizon_from_text(question):
            return None
        return "horizon"
    if "period" in required:
        if slots.get("period") and slots["period"] not in ("unknown", ""):
            return None
        if _extract_period_from_text(question):
            return None
        if period_preset in ("本周", "本月", "本季", "自定义"):
            return None
        return "period"
    return None


def _fill_slots(intent_id: str, question: str, slots: dict, period_preset: str) -> dict:
    out = dict(slots or {})
    if "period" not in out or out.get("period") in (None, "", "unknown"):
        out["period"] = _extract_period_from_text(question) or period_preset or "本月"
    if intent_id == "pickup_gap":
        h = out.get("horizon") or _extract_horizon_from_text(question)
        out["horizon"] = int(h or (7 if (period_preset == "本周") else 30))
    meta = get_intent(intent_id) or {}
    need_bl = "baseline" in (meta.get("required_slots") or []) or (
        (meta.get("operator_id") or "") == "op_compare_baseline"
    )
    if need_bl and not out.get("_baseline"):
        default_bl = meta.get("default_baseline") or "环比"
        out["_baseline"] = infer_baseline_from_text(question, default_bl)
    if "top_n" in (meta.get("required_slots") or []) or (intent_id or "").startswith("guest_top_"):
        out["top_n"] = int(out.get("top_n") or extract_top_n(question, 5))
    if meta.get("ignore_period_filter"):
        out["_ignore_period"] = True
    if meta.get("pii_level"):
        out["_pii_level"] = meta["pii_level"]
    return out


def _llm_route(
    db: Session,
    question: str,
    candidates: list[str],
    period_preset: str,
    hotel_name: str,
    *,
    history: Optional[list[dict]] = None,
) -> dict:
    from commercial.ai_core.llm_service import chat

    history = history or []
    include_fu = bool(history)
    short = candidates or list(INTENT_CATALOG.keys())[:8]
    if include_fu:
        short = list(dict.fromkeys(short + list(FOLLOWUP_INTENTS.keys())))
    lines = []
    for iid in short:
        meta = get_intent(iid)
        if meta:
            lines.append(f"- {iid}: {meta['intent_label']}")
    system = (
        (ROUTE_SYSTEM_MULTI if include_fu else ROUTE_SYSTEM)
        .replace("{{intent_list}}", "\n".join(lines) or intent_list_for_prompt(include_followup=include_fu))
        .replace("{{glossary}}", glossary_for_prompt(30))
    )
    hist_json = json.dumps(history[-MAX_HISTORY_TURNS:], ensure_ascii=False, default=str)
    user = (
        f"【对话历史 - 最近 {MAX_HISTORY_TURNS} 轮】\n{hist_json}\n"
        f"【当前用户问题】\n{question}\n"
        f"【当前上下文】时间范围预设：{period_preset}；酒店：{hotel_name}\n"
        f"【候选短名单】\n{', '.join(short)}\n\n请输出 JSON。"
    )
    try:
        raw = chat(db, [{"role": "user", "content": user}], system, overrides=ASK_LLM_OPTS)
        text = raw.get("content") if isinstance(raw, dict) else str(raw)
        obj = _extract_issues_json(text)
        iid = str(obj.get("intent_id") or "")
        allowed = all_intent_ids()
        if iid not in allowed:
            iid = short[0] if short else "unknown"
        cands = [c for c in (obj.get("candidates") or []) if c in INTENT_CATALOG or c in FOLLOWUP_INTENTS]
        slots = obj.get("slots") if isinstance(obj.get("slots"), dict) else {}
        return {
            "intent_id": iid,
            "intent_label": (get_intent(iid) or {}).get("intent_label") or str(obj.get("intent_label") or ""),
            "slots": slots,
            "confidence": obj.get("confidence") or "中",
            "candidates": cands,
            "resolved_question": str(obj.get("resolved_question") or "").strip() or question,
            "source": "llm",
            "model": (raw or {}).get("model") if isinstance(raw, dict) else None,
        }
    except Exception as e:
        return {
            "intent_id": short[0] if len(short) == 1 else "unknown",
            "intent_label": (get_intent(short[0]) or {}).get("intent_label", "") if short else "",
            "slots": {},
            "confidence": "低",
            "candidates": short[:3],
            "resolved_question": question,
            "source": "llm_fallback",
            "error": str(getattr(e, "detail", None) or e)[:160],
        }


def _build_followup_result(
    followup_id: str,
    parent: AiAskQuery,
    filled: dict,
) -> dict[str, Any]:
    try:
        prior_result = json.loads(parent.result_json or "{}")
    except Exception:
        prior_result = {}
    try:
        prior_answer = json.loads(parent.answer_json or "{}")
    except Exception:
        prior_answer = {}
    prior_intent = parent.intent_id or ""
    prior_summary = prior_answer.get("summary") or prior_result.get("title") or parent.intent_label or ""
    tips = tips_for(prior_intent)
    metrics_base = {
        "prior_intent_id": prior_intent,
        "prior_summary": prior_summary,
        "prior_metrics": prior_result.get("metrics") or {},
    }

    if followup_id == "followup_optimize":
        rows = [{"label": t["name"], "value": t["expected_impact"], "note": t["desc"], "tone": "pos"} for t in tips]
        return {
            "title": "可落地的优化方向",
            "rows": rows,
            "metrics": {**metrics_base, "playbook": tips},
            "unit": "",
            "empty": not tips,
            "playbook_tips": tips,
        }

    if followup_id == "followup_impact":
        pm = prior_result.get("metrics") or {}
        rows = [
            {"label": "上一轮结论", "value": prior_summary or "—", "note": parent.intent_label or ""},
        ]
        # 尽量复用上一轮关键指标
        for k, label in (
            ("ota_pct", "OTA 占比 %"),
            ("business_pct", "商务客占比 %"),
            ("member_pct", "会员占比 %"),
            ("delta_pt", "相对对比期变化(pt)"),
            ("revpar", "RevPAR"),
            ("gap_pct", "预订缺口 %"),
        ):
            if k in pm and pm[k] is not None:
                rows.append({"label": label, "value": pm[k], "note": "来自上一轮查询"})
        rows.append(
            {
                "label": "若维持当前趋势",
                "value": "压力可能延续到下一周期",
                "note": "定性判断，基于上一轮结果，非新编数字",
            }
        )
        return {
            "title": "影响与趋势",
            "rows": rows,
            "metrics": metrics_base,
            "unit": "",
            "empty": False,
            "playbook_tips": [],
        }

    if followup_id == "followup_diagnose":
        rows = [{"label": "现象", "value": prior_summary or "—", "note": "上一轮结论"}]
        drivers = []
        pm = prior_result.get("metrics") or {}
        if pm.get("over") or (isinstance(pm.get("ota_pct"), (int, float)) and pm["ota_pct"] >= 55):
            drivers.append(
                {"label": "渠道结构偏 OTA", "value": f"OTA {pm.get('ota_pct')}%", "note": "证据字段 ota_pct"}
            )
        if pm.get("churn") or (isinstance(pm.get("delta_pt"), (int, float)) and pm["delta_pt"] < 0):
            drivers.append({"label": "客群占比下滑", "value": f"{pm.get('delta_pt')} pt", "note": "证据字段 delta_pt"})
        if pm.get("worse"):
            drivers.append({"label": "会员复购偏弱", "value": f"{pm.get('member_pct')}%", "note": "证据字段 worse"})
        if pm.get("losing_count"):
            drivers.append(
                {
                    "label": "亏损渠道",
                    "value": "、".join(pm.get("losing") or []) or pm.get("losing_count"),
                    "note": "证据字段 losing",
                }
            )
        for r in prior_result.get("rows") or []:
            if len(drivers) >= 3:
                break
            drivers.append(
                {"label": str(r.get("label") or "指标"), "value": r.get("value"), "note": r.get("note") or "上一轮明细"}
            )
        rows.extend(drivers[:3] or [{"label": "驱动因子", "value": "unknown", "note": "上一轮缺少可归因字段"}])
        return {
            "title": "原因拆解",
            "rows": rows,
            "metrics": metrics_base,
            "unit": "",
            "empty": False,
            "playbook_tips": [],
        }

    # followup_compare：复述上一轮 rows，并标注对照
    rows = list(prior_result.get("rows") or [])[:6]
    if not rows:
        rows = [{"label": "对比基线", "value": prior_summary or "unknown", "note": filled.get("period") or "本期"}]
    return {
        "title": "对比视角",
        "rows": rows,
        "metrics": {**metrics_base, "compare_note": "基于上一轮结果复盘对比"},
        "unit": prior_result.get("unit") or "",
        "empty": not rows,
        "playbook_tips": [],
    }


def _persist_pending(
    db: Session,
    hotel_id: int,
    session_id: str,
    question: str,
    intent_id: Optional[str],
    slots: dict,
    tier0: list,
    clarify_round: int,
    period_preset: str,
    baseline: str,
    *,
    need_clarify: bool,
    resolved_question: Optional[str] = None,
    parent_query_id: Optional[int] = None,
    normalized_question: Optional[str] = None,
    metric_id: Optional[str] = None,
    operator_id: Optional[str] = None,
) -> AiAskQuery:
    meta = get_intent(intent_id) if intent_id else None
    mid = metric_id or (meta or {}).get("metric_id")
    oid = operator_id or (meta or {}).get("operator_id")
    row = AiAskQuery(
        session_id=session_id,
        hotel_id=hotel_id,
        parent_query_id=parent_query_id,
        raw_question=question,
        normalized_question=normalized_question,
        resolved_question=resolved_question or question,
        intent_id=intent_id,
        intent_label=(meta or {}).get("intent_label"),
        metric_id=mid,
        operator_id=oid,
        slots_json=json.dumps({**slots, "_period_preset": period_preset, "_baseline": baseline}, ensure_ascii=False),
        tier0_candidates=json.dumps(tier0, ensure_ascii=False),
        need_clarify=need_clarify,
        clarify_round=clarify_round,
        query_ref=(meta or {}).get("query_ref"),
        created_by="ai_agent",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def route_question(
    db: Session,
    hotel_id: int,
    *,
    question: str,
    period_preset: str = "本月",
    baseline: str = "同比",
    session_id: Optional[str] = None,
    clarify_round: int = 0,
) -> dict[str, Any]:
    from infra.i18n import t as _t_route

    q = (question or "").strip()
    if not q:
        return {"status": "error", "message": _t_route("请输入问题")}
    sid = session_id or str(uuid.uuid4())
    _touch_session(db, sid, hotel_id)
    hotel = db.get(Hotel, hotel_id)
    hotel_name = hotel.name if hotel else f"酒店{hotel_id}"
    turns = load_session_turns(db, sid, hotel_id)
    parent_id = turns[-1]["query_id"] if turns else None

    if clarify_round >= MAX_CLARIFY_ROUNDS:
        return {
            "status": "out_of_scope",
            "session_id": sid,
            "message": _t_route("这几轮还没问清楚，建议直接点下面的常见问题。"),
            "presets": default_questions_dynamic(),
            "clarify_round": clarify_round,
        }

    # —— 多轮：代词 / 追问关键词 → 追问意图 ——
    fu = detect_followup_intent(q) if turns else None
    if turns and (fu or has_pronoun_reference(q)):
        if not fu:
            # 有代词但不知追问类型 → 让用户点选
            options = [
                {"intent_id": iid, "intent_label": _t_route(str(meta["intent_label"]))}
                for iid, meta in FOLLOWUP_INTENTS.items()
            ]
            resolved = rule_resolve_question(q, turns)
            row = _persist_pending(
                db,
                hotel_id,
                sid,
                q,
                None,
                {},
                list(FOLLOWUP_INTENTS.keys()),
                clarify_round,
                period_preset,
                baseline,
                need_clarify=True,
                resolved_question=resolved,
                parent_query_id=parent_id,
            )
            return {
                "status": "clarify_intent",
                "session_id": sid,
                "query_id": row.id,
                "prompt": _t_route("你想接着刚才的结论继续问哪一类？"),
                "options": options,
                "resolved_question": resolved,
                "clarify_round": clarify_round,
                "is_followup": True,
            }

        resolved = rule_resolve_question(q, turns, fu)
        # 可选：用 LLM 校正意图；消解句若仍含代词则丢弃，保留规则版
        try:
            llm = _llm_route(db, q, [fu], period_preset, hotel_name, history=turns)
            if llm.get("intent_id") in FOLLOWUP_INTENTS:
                fu = llm["intent_id"]
                resolved = rule_resolve_question(q, turns, fu)
            rq = str(llm.get("resolved_question") or "").strip()
            if rq and not has_pronoun_reference(rq) and len(rq) >= 8:
                resolved = rq
        except Exception:
            pass

        slots = _fill_slots(fu, resolved, {}, period_preset)
        # 继承上一轮 period
        if turns[-1].get("slots", {}).get("period"):
            slots["period"] = turns[-1]["slots"]["period"]
        row = _persist_pending(
            db,
            hotel_id,
            sid,
            q,
            fu,
            slots,
            [fu],
            clarify_round,
            period_preset,
            baseline,
            need_clarify=True,
            resolved_question=resolved,
            parent_query_id=parent_id,
        )
        return _followup_confirm_payload(
            sid=sid, row=row, intent_id=fu, slots=slots, resolved=resolved, clarify_round=clarify_round, auto=True
        )

    cands = tier0_candidates(q)
    norm = normalize(q)

    if not cands:
        # v1.2 兜底：decompose_route（metric × operator）
        dec = decompose_route(q)
        iid = dec.get("intent_id")
        if iid and get_intent(iid):
            meta = get_intent(iid)
            slots = _fill_slots(iid, q, {}, period_preset)
            if dec.get("baseline"):
                slots["_baseline"] = dec["baseline"]
            row = _persist_pending(
                db,
                hotel_id,
                sid,
                q,
                iid,
                slots,
                [iid],
                clarify_round,
                period_preset,
                slots.get("_baseline") or baseline,
                need_clarify=True,
                resolved_question=q,
                normalized_question=dec.get("normalized") or norm.get("normalized"),
                metric_id=dec.get("metric_id"),
                operator_id=dec.get("operator_id"),
            )
            from infra.i18n import t as _t_dec

            bl = slots.get("_baseline") or baseline
            intent_label = _t_dec(str(meta["intent_label"]))
            if meta.get("ignore_period_filter"):
                period_note = _t_dec("全生命周期 · 不受时间范围限制")
            else:
                period_note = f"{_t_dec(str(slots.get('period') or period_preset))} · {_t_dec(str(bl))}"
            if slots.get("top_n"):
                period_note = f"Top{slots['top_n']} · {period_note}"
            return {
                "status": "decompose_confirm",
                "session_id": sid,
                "query_id": row.id,
                "intent_id": iid,
                "intent_label": intent_label,
                "slots": slots,
                "metric_id": dec.get("metric_id"),
                "operator_id": dec.get("operator_id"),
                "normalized_question": dec.get("normalized"),
                "resolved_question": q,
                "pipeline": dec.get("pipeline") or [],
                "prompt": _t_dec("按上面理解，查「{q}」（{note}）？", q=intent_label, note=period_note),
                "clarify_round": clarify_round,
                "via": "decompose_route",
                "pii_level": meta.get("pii_level") or "none",
                "ignore_period_filter": bool(meta.get("ignore_period_filter")),
            }
        row = _persist_pending(
            db,
            hotel_id,
            sid,
            q,
            "unknown",
            {},
            cands,
            clarify_round,
            period_preset,
            baseline,
            need_clarify=True,
            normalized_question=norm.get("normalized"),
            metric_id=norm.get("metric_id"),
            operator_id=norm.get("operator_id"),
        )
        return {
            "status": "out_of_scope",
            "session_id": sid,
            "query_id": row.id,
            "message": _t_route("这个问题我暂时答不了。你可以改问这些："),
            "presets": default_questions_dynamic(),
            "clarify_round": clarify_round,
            "tier0_candidates": cands,
            "normalized_question": norm.get("normalized"),
        }

    if cands == ["action_not_question"] or cands[0] == "action_not_question":
        row = _persist_pending(
            db,
            hotel_id,
            sid,
            q,
            "action_not_question",
            {},
            cands,
            clarify_round,
            period_preset,
            baseline,
            need_clarify=True,
        )
        return {
            "status": "action_block",
            "session_id": sid,
            "query_id": row.id,
            "message": _t_route("改价、改库存请到「价格助手」操作，这里只回答经营数据问题。"),
            "action_path": "/pricing",
            "action_label": _t_route("价格助手"),
            "clarify_round": clarify_round,
        }

    intent_id = cands[0]
    slots: dict[str, Any] = {}
    confidence = "高"
    resolved = q

    if len(cands) > 1:
        from infra.i18n import t as _t_ci

        options = [
            {
                "intent_id": iid,
                "intent_label": _t_ci(str(INTENT_CATALOG[iid]["intent_label"])),
            }
            for iid in cands[:3]
            if iid in INTENT_CATALOG
        ]
        row = _persist_pending(
            db, hotel_id, sid, q, None, slots, cands, clarify_round, period_preset, baseline, need_clarify=True
        )
        return {
            "status": "clarify_intent",
            "session_id": sid,
            "query_id": row.id,
            "prompt": _t_ci("你想问的是下面哪一个？"),
            "options": options,
            "clarify_round": clarify_round,
            "tier0_candidates": cands,
        }

    if intent_id not in INTENT_CATALOG:
        from infra.i18n import t as _t_oos

        row = _persist_pending(
            db, hotel_id, sid, q, "unknown", {}, cands, clarify_round, period_preset, baseline, need_clarify=True
        )
        return {
            "status": "out_of_scope",
            "session_id": sid,
            "query_id": row.id,
            "message": _t_oos("暂时无法匹配意图，请改用预设问题。"),
            "presets": default_questions_dynamic(),
            "clarify_round": clarify_round,
        }

    slots = _fill_slots(intent_id, q, slots, period_preset)
    miss = missing_slot(intent_id, q, slots, period_preset)
    meta = get_intent(intent_id)
    if miss == "period":
        from infra.i18n import t as _t_per

        intent_label = _t_per(str(meta["intent_label"]))
        row = _persist_pending(
            db, hotel_id, sid, q, intent_id, slots, cands, clarify_round, period_preset, baseline, need_clarify=True
        )
        return {
            "status": "clarify_slot",
            "session_id": sid,
            "query_id": row.id,
            "intent_id": intent_id,
            "intent_label": intent_label,
            "slot": "period",
            "prompt": _t_per("「{q}」——你想看哪段时间？", q=intent_label),
            "options": [
                {"value": "本周", "label": _t_per("本周")},
                {"value": "本月", "label": _t_per("本月")},
                {"value": "本季", "label": _t_per("本季")},
            ],
            "clarify_round": clarify_round,
        }
    if miss == "horizon":
        from infra.i18n import t as _t_hz

        intent_label = _t_hz(str(meta["intent_label"]))
        row = _persist_pending(
            db, hotel_id, sid, q, intent_id, slots, cands, clarify_round, period_preset, baseline, need_clarify=True
        )
        return {
            "status": "clarify_slot",
            "session_id": sid,
            "query_id": row.id,
            "intent_id": intent_id,
            "intent_label": intent_label,
            "slot": "horizon",
            "prompt": _t_hz("「{q}」——看未来多久？", q=intent_label),
            "options": [
                {"value": "7", "label": _t_hz("未来 7 天")},
                {"value": "30", "label": _t_hz("未来 30 天")},
            ],
            "clarify_round": clarify_round,
        }

    row = _persist_pending(
        db,
        hotel_id,
        sid,
        q,
        intent_id,
        slots,
        cands,
        clarify_round,
        period_preset,
        baseline,
        need_clarify=True,
        resolved_question=resolved,
    )
    from infra.i18n import t

    intent_label = t(str(meta["intent_label"]))
    slot_txt = (
        t("（未来 {n} 天）", n=slots.get("horizon"))
        if intent_id == "pickup_gap"
        else t(
            "（{period} · {baseline}）",
            period=t(str(slots.get("period") or period_preset)),
            baseline=t(str(baseline)),
        )
    )
    return {
        "status": "confirm",
        "session_id": sid,
        "query_id": row.id,
        "intent_id": intent_id,
        "intent_label": intent_label,
        "slots": slots,
        "prompt": t("确认一下：你是想问「{q}」{slot} 吗？", q=intent_label, slot=slot_txt),
        "confidence": confidence,
        "tier0_candidates": cands,
        "clarify_round": clarify_round,
    }
