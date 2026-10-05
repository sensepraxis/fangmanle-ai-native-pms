# SPDX-License-Identifier: BUSL-1.1
"""AI 问数 · 确认执行（查数 / 流式回答 / PII / 澄清点选）。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from analytics.ask_catalog import INTENT_CATALOG, get_intent, is_followup_intent
from analytics.ask_domain import COMPOSITE_INTENTS, default_questions_dynamic
from analytics.ask_pii import apply_pii_gate, role_can_access_pii, sanitize_answer_text, strip_internal_ids
from analytics.ask_playbook import filter_playbook_ids
from analytics.ask_queries import run_query
from commercial.analytics.ai_ask_answering import (
    ASK_LLM_OPTS,
    _answer_system,
    _finalize_answer,
    _followup_confirm_payload,
    _parse_answer_text,
    _unavailable_answer,
    narrate_query_result,
)
from commercial.analytics.ai_ask_routing import (
    _build_followup_result,
    _fill_slots,
    missing_slot,
    route_question,
    rule_resolve_question,
)
from commercial.analytics.ai_ask_session import load_session_turns
from commercial.analytics.ask_data_service import _strip_think
from models import AiAskQuery


def _execute_metric_query(
    db: Session,
    hotel_id: int,
    *,
    iid: str,
    meta: dict,
    filled: dict,
    period_preset: str,
    bl: str,
    start: Optional[str],
    end: Optional[str],
    role: Optional[str],
    pii_unlocked: bool = False,
) -> dict[str, Any]:
    ignore = bool(meta.get("ignore_period_filter") or filled.get("_ignore_period"))
    pii_level = str(meta.get("pii_level") or filled.get("_pii_level") or "none")
    if pii_level != "none" and not role_can_access_pii(role):
        return apply_pii_gate({"rows": [], "empty": True, "title": meta.get("intent_label")}, pii_level, role=role)

    result = run_query(
        db,
        hotel_id,
        meta["query_ref"],
        period_label=str(filled.get("period") or period_preset),
        baseline=bl,
        horizon=int(filled.get("horizon") or 7),
        top_n=int(filled.get("top_n") or 5),
        start=start,
        end=end,
        ignore_period=ignore,
    )
    if pii_level != "none":
        result = apply_pii_gate(result, pii_level, role=role, unlocked=pii_unlocked)
    return result


def _prepare_confirmed_query(
    db: Session,
    hotel_id: int,
    *,
    query_id: int,
    confirmed: bool = True,
    intent_id: Optional[str] = None,
    slots: Optional[dict] = None,
    period_preset: str = "本月",
    baseline: str = "同比",
) -> dict[str, Any]:
    row = db.get(AiAskQuery, query_id)
    if not row or row.hotel_id != hotel_id:
        return {"status": "error", "message": "会话不存在"}
    if not confirmed:
        row.need_clarify = False
        db.commit()
        return {"status": "cancelled", "message": "已取消，可换种问法或点默认问题。"}

    iid = intent_id or row.intent_id
    meta = get_intent(iid) if iid else None
    if not meta or iid in ("unknown", "action_not_question"):
        return {"status": "out_of_scope", "message": "意图无效", "presets": default_questions_dynamic()}
    if iid not in INTENT_CATALOG and not is_followup_intent(iid) and iid not in COMPOSITE_INTENTS:
        return {"status": "out_of_scope", "message": "意图无效", "presets": default_questions_dynamic()}

    parent = None
    if is_followup_intent(iid):
        if row.parent_query_id:
            parent = db.get(AiAskQuery, row.parent_query_id)
        if not parent or not parent.answer_json:
            # 回退：同 session 最近一条已回答
            turns = load_session_turns(db, row.session_id, hotel_id, limit=1)
            if turns:
                parent = db.get(AiAskQuery, turns[-1]["query_id"])
                row.parent_query_id = parent.id if parent else None
        if not parent or not parent.answer_json:
            return {
                "status": "out_of_scope",
                "message": "还没有上一轮结论，请先问一个具体数据问题。",
                "presets": default_questions_dynamic(),
            }

    prev_slots = {}
    try:
        prev_slots = json.loads(row.slots_json or "{}")
    except Exception:
        prev_slots = {}
    merged = {**prev_slots, **(slots or {})}
    period = merged.get("period") or prev_slots.get("_period_preset") or period_preset or "本月"
    bl = merged.get("_baseline") or baseline or "同比"
    horizon = int(merged.get("horizon") or 7)
    filled = _fill_slots(
        iid, row.resolved_question or row.raw_question or "", {**merged, "period": period, "horizon": horizon}, period
    )

    miss = missing_slot(iid, row.raw_question or "", filled, period)
    if miss:
        return {
            "status": "clarify_slot",
            "query_id": row.id,
            "session_id": row.session_id,
            "intent_id": iid,
            "intent_label": meta["intent_label"],
            "slot": miss,
            "prompt": f"还差「{miss}」才能查数，请选择：",
            "options": (
                [
                    {"value": "本周", "label": "本周"},
                    {"value": "本月", "label": "本月"},
                    {"value": "本季", "label": "本季"},
                ]
                if miss == "period"
                else [{"value": "7", "label": "未来 7 天"}, {"value": "30", "label": "未来 30 天"}]
            ),
        }

    row.confirmed_at = datetime.utcnow()
    row.intent_id = iid
    row.intent_label = meta["intent_label"]
    row.query_ref = meta.get("query_ref")
    row.slots_json = json.dumps(filled, ensure_ascii=False)
    row.need_clarify = False
    if not row.resolved_question:
        row.resolved_question = row.raw_question
    db.commit()
    return {
        "status": "ready",
        "row": row,
        "intent_id": iid,
        "meta": meta,
        "slots": filled,
        "baseline": bl,
        "parent": parent,
    }


def confirm_and_execute(
    db: Session,
    hotel_id: int,
    *,
    query_id: int,
    confirmed: bool = True,
    intent_id: Optional[str] = None,
    slots: Optional[dict] = None,
    period_preset: str = "本月",
    baseline: str = "同比",
    start: Optional[str] = None,
    end: Optional[str] = None,
    role: Optional[str] = None,
) -> dict[str, Any]:
    prep = _prepare_confirmed_query(
        db,
        hotel_id,
        query_id=query_id,
        confirmed=confirmed,
        intent_id=intent_id,
        slots=slots,
        period_preset=period_preset,
        baseline=baseline,
    )
    if prep.get("status") != "ready":
        return prep

    row: AiAskQuery = prep["row"]
    iid = prep["intent_id"]
    meta = prep["meta"]
    filled = prep["slots"]
    bl = prep["baseline"]
    parent: Optional[AiAskQuery] = prep.get("parent")

    if is_followup_intent(iid) and parent:
        result = _build_followup_result(iid, parent, filled)
        prior_summary = ""
        try:
            prior_summary = (json.loads(parent.answer_json or "{}") or {}).get("summary") or ""
        except Exception:
            prior_summary = parent.intent_label or ""
        answer = narrate_query_result(
            db,
            row.resolved_question or row.raw_question or "",
            result,
            meta["intent_label"],
            iid,
            filled,
            followup=True,
            prior_summary=prior_summary,
            prior_intent_id=parent.intent_id,
        )
        tips = result.get("playbook_tips") or answer.get("tips") or []
        if iid == "followup_optimize":
            tips = filter_playbook_ids(parent.intent_id or "", [t.get("id") for t in tips if isinstance(t, dict)])
            answer["tips"] = tips
            answer["playbook_used"] = [t["id"] for t in tips]
            result["playbook_tips"] = tips
        return _finalize_answer(db, row, iid, meta, filled, result, answer, parent_query_id=parent.id, role=role)

    result = _execute_metric_query(
        db,
        hotel_id,
        iid=iid,
        meta=meta,
        filled=filled,
        period_preset=period_preset,
        bl=bl,
        start=start,
        end=end,
        role=role,
        pii_unlocked=bool(row.pii_accessed),
    )
    if result.get("pii_denied"):
        return {
            "status": "pii_denied",
            "session_id": row.session_id,
            "query_id": row.id,
            "message": result.get("message") or "无权限查看客户个人数据",
            "result": strip_internal_ids(result),
        }

    safe_result = strip_internal_ids(result)
    answer = narrate_query_result(
        db, row.resolved_question or row.raw_question or "", safe_result, meta["intent_label"], iid, filled
    )
    if answer.get("summary"):
        answer["summary"] = sanitize_answer_text(str(answer["summary"]))
    answer["pii_mask"] = bool(safe_result.get("pii_mask"))

    return _finalize_answer(db, row, iid, meta, filled, safe_result, answer, role=role)


def ack_pii(
    db: Session,
    hotel_id: int,
    *,
    query_id: int,
    ack_by: str,
    role: Optional[str] = None,
    period_preset: str = "本月",
    baseline: str = "同比",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict[str, Any]:
    """D8：管理者二次确认后解锁客户明细预览，并落审计三联。"""
    if not role_can_access_pii(role):
        return {"status": "pii_denied", "message": "当前账号无权限查看客户个人数据（需店长/管理员）。"}
    by = (ack_by or "").strip()
    if not by:
        return {"status": "error", "message": "请填写工号后再确认"}

    row = db.get(AiAskQuery, query_id)
    if not row or row.hotel_id != hotel_id:
        return {"status": "error", "message": "会话不存在"}
    if not row.confirmed_at:
        return {"status": "error", "message": "尚未确认意图，不能披露客户明细"}

    iid = row.intent_id or ""
    meta = get_intent(iid) or {}
    if (meta.get("pii_level") or "none") != "confirm":
        return {"status": "error", "message": "本条问数无需隐私二次确认"}

    slots = {}
    try:
        slots = json.loads(row.slots_json or "{}")
    except Exception:
        slots = {}
    filled = _fill_slots(iid, row.resolved_question or row.raw_question or "", slots, period_preset)
    bl = str(filled.get("_baseline") or baseline)

    row.pii_accessed = True
    row.pii_ack_by = by[:32]
    row.pii_ack_at = datetime.utcnow()
    db.commit()

    result = _execute_metric_query(
        db,
        hotel_id,
        iid=iid,
        meta=meta,
        filled=filled,
        period_preset=period_preset,
        bl=bl,
        start=start,
        end=end,
        role=role,
        pii_unlocked=True,
    )
    if result.get("pii_denied"):
        return {
            "status": "pii_denied",
            "query_id": row.id,
            "message": result.get("message") or "无权限查看客户个人数据",
        }

    safe_result = strip_internal_ids(result)
    answer = narrate_query_result(
        db, row.resolved_question or row.raw_question or "", safe_result, meta["intent_label"], iid, filled
    )
    if answer.get("summary"):
        answer["summary"] = sanitize_answer_text(str(answer.get("summary") or ""))
    answer["pii_mask"] = True
    answer["pii_unlocked"] = True
    out = _finalize_answer(db, row, iid, meta, filled, safe_result, answer, role=role)
    out["status"] = "answered"
    out["pii_ack_by"] = row.pii_ack_by
    out["pii_ack_at"] = row.pii_ack_at.isoformat() + "Z" if row.pii_ack_at else None
    return out


def stream_confirm_and_execute(
    db: Session,
    hotel_id: int,
    *,
    query_id: int,
    confirmed: bool = True,
    intent_id: Optional[str] = None,
    slots: Optional[dict] = None,
    period_preset: str = "本月",
    baseline: str = "同比",
    start: Optional[str] = None,
    end: Optional[str] = None,
    role: Optional[str] = None,
) -> Iterator[dict[str, Any]]:
    """确认后流式：查库/playbook → LLM token → 结构化结果。"""
    prep = _prepare_confirmed_query(
        db,
        hotel_id,
        query_id=query_id,
        confirmed=confirmed,
        intent_id=intent_id,
        slots=slots,
        period_preset=period_preset,
        baseline=baseline,
    )
    if prep.get("status") != "ready":
        yield {"type": "done", "data": prep}
        return

    row: AiAskQuery = prep["row"]
    iid = prep["intent_id"]
    meta = prep["meta"]
    filled = prep["slots"]
    bl = prep["baseline"]
    parent: Optional[AiAskQuery] = prep.get("parent")

    yield {"type": "stage", "stage": "query", "message": "正在查询…"}

    prior_summary = ""
    prior_intent_id = None
    if is_followup_intent(iid) and parent:
        result = _build_followup_result(iid, parent, filled)
        try:
            prior_summary = (json.loads(parent.answer_json or "{}") or {}).get("summary") or ""
        except Exception:
            prior_summary = parent.intent_label or ""
        prior_intent_id = parent.intent_id
    else:
        result = _execute_metric_query(
            db,
            hotel_id,
            iid=iid,
            meta=meta,
            filled=filled,
            period_preset=period_preset,
            bl=bl,
            start=start,
            end=end,
            role=role,
            pii_unlocked=bool(row.pii_accessed),
        )
        if result.get("pii_denied"):
            yield {
                "type": "done",
                "data": {
                    "status": "pii_denied",
                    "session_id": row.session_id,
                    "query_id": row.id,
                    "message": result.get("message") or "无权限查看客户个人数据",
                    "result": strip_internal_ids(result),
                },
            }
            return
        result = strip_internal_ids(result)

    yield {
        "type": "query_done",
        "message": "查询完成",
        "result": result,
        "intent_label": meta["intent_label"],
    }

    from commercial.ai_core.llm_service import chat_stream, load_llm_config
    from extensions.llm.facade import resolve_model_name

    model_name = ""
    followup = is_followup_intent(iid)
    try:
        cfg = load_llm_config(db)
        model_name = resolve_model_name(cfg)
        if not cfg.get("enabled", True):
            raise RuntimeError("LLM 模块已禁用")
        from commercial.analytics.analytics_ai_locale import is_en_locale
        from infra.i18n import t as _t

        yield {
            "type": "stage",
            "stage": "llm",
            "message": _t("正在整理回答…"),
            "model": model_name,
        }
        qtext = row.resolved_question or row.raw_question or ""
        payload = json.dumps(result, ensure_ascii=False, default=str)
        if followup:
            if is_en_locale():
                user = (
                    f"[Follow-up] {qtext}\n[Intent] {meta['intent_label']}\n"
                    f"[Prior conclusion] {prior_summary}\n"
                    f"[This result] {payload}\n"
                    "Output JSON only. User-visible strings must be English."
                )
            else:
                user = (
                    f"【用户追问】{qtext}\n【意图】{meta['intent_label']}\n"
                    f"【上一轮结论】{prior_summary}\n"
                    f"【本轮查询结果】{payload}\n请输出 JSON。"
                )
            system = _answer_system(followup=True)
        else:
            if is_en_locale():
                user = (
                    f"[Question] {qtext}\n[Intent] {meta['intent_label']}\n"
                    f"[Query result] {payload}\n"
                    "Output JSON only. User-visible strings must be English."
                )
            else:
                user = f"【用户原问题】{qtext}\n【意图】{meta['intent_label']}\n【查询结果】{payload}\n请输出 JSON。"
            system = _answer_system(followup=False)
        buf: list[str] = []
        for tok in chat_stream(
            db,
            [{"role": "user", "content": user}],
            system,
            overrides={**ASK_LLM_OPTS, "think": True, "max_tokens": 900},
        ):
            if not tok:
                continue
            buf.append(tok)
            yield {"type": "token", "content": tok}
        raw_text = "".join(buf)
        try:
            answer = _parse_answer_text(raw_text, prior_intent_id=prior_intent_id if followup else None)
            answer["model"] = model_name
        except Exception:
            answer = _unavailable_answer(result, "模型输出无法解析为 JSON")
            yield {"type": "error", "message": _t("未能生成 AI 解读，已保留查询数据")}
    except Exception as e:
        from infra.i18n import t as _t

        err = str(getattr(e, "detail", None) or e)[:200]
        yield {"type": "error", "message": _t("未能调用大模型")}
        answer = _unavailable_answer(result, err)

    if followup and iid == "followup_optimize" and parent:
        tips = filter_playbook_ids(
            parent.intent_id or "",
            answer.get("playbook_used") or [t.get("id") for t in (result.get("playbook_tips") or [])],
        )
        answer["tips"] = tips
        answer["playbook_used"] = [t["id"] for t in tips]
        result["playbook_tips"] = tips
    elif not followup:
        # 非追问不得挂 playbook 卡片（避免占位率问数误出会员召回中文卡）
        answer.pop("tips", None)
        answer.pop("playbook_used", None)
        result.pop("playbook_tips", None)

    from commercial.analytics.ai_ask_answering import _localize_answer_text

    if answer.get("summary"):
        answer["summary"] = _localize_answer_text(sanitize_answer_text(str(answer["summary"])))
    if isinstance(answer.get("key_points"), list):
        answer["key_points"] = [_localize_answer_text(str(x)) for x in answer["key_points"]]
    answer["pii_mask"] = bool(result.get("pii_mask"))

    payload = _finalize_answer(
        db,
        row,
        iid,
        meta,
        filled,
        result,
        answer,
        parent_query_id=parent.id if parent else None,
        role=role,
    )
    yield {"type": "done", "data": payload}


def apply_clarify_choice(
    db: Session,
    hotel_id: int,
    *,
    query_id: int,
    question: str,
    intent_id: Optional[str] = None,
    slot: Optional[str] = None,
    slot_value: Optional[str] = None,
    period_preset: str = "本月",
    baseline: str = "同比",
    clarify_round: int = 0,
) -> dict[str, Any]:
    """用户点选意图或槽位后，回到确认闸门（仍不查库，除非再 confirm）。"""
    row = db.get(AiAskQuery, query_id)
    if not row or row.hotel_id != hotel_id:
        return {"status": "error", "message": "会话不存在"}

    slots = {}
    try:
        slots = json.loads(row.slots_json or "{}")
    except Exception:
        slots = {}
    iid = intent_id or row.intent_id
    if slot and slot_value is not None:
        if slot == "horizon":
            slots["horizon"] = int(slot_value)
        else:
            slots[slot] = slot_value
            if slot == "period":
                period_preset = str(slot_value)

    # 澄清里选了追问意图
    if iid and is_followup_intent(iid):
        turns = load_session_turns(db, row.session_id, hotel_id)
        parent_id = row.parent_query_id or (turns[-1]["query_id"] if turns else None)
        resolved = rule_resolve_question(question or row.raw_question or "", turns, iid)
        filled = _fill_slots(iid, resolved, slots, period_preset)
        meta = get_intent(iid)
        row.intent_id = iid
        row.intent_label = meta["intent_label"]
        row.resolved_question = resolved
        row.parent_query_id = parent_id
        row.slots_json = json.dumps(
            {**filled, "_period_preset": period_preset, "_baseline": baseline}, ensure_ascii=False
        )
        row.clarify_round = clarify_round + 1
        row.query_ref = meta.get("query_ref")
        db.commit()
        return _followup_confirm_payload(
            sid=row.session_id,
            row=row,
            intent_id=iid,
            slots=filled,
            resolved=resolved,
            clarify_round=row.clarify_round,
            auto=True,
        )

    if not iid or (iid not in INTENT_CATALOG and iid not in COMPOSITE_INTENTS):
        return route_question(
            db,
            hotel_id,
            question=question or row.raw_question,
            period_preset=period_preset,
            baseline=baseline,
            session_id=row.session_id,
            clarify_round=clarify_round + 1,
        )

    filled = _fill_slots(iid, question or row.raw_question or "", slots, period_preset)
    miss = missing_slot(iid, question or row.raw_question or "", filled, period_preset)
    meta = get_intent(iid)
    row.intent_id = iid
    row.intent_label = meta["intent_label"]
    row.slots_json = json.dumps({**filled, "_period_preset": period_preset, "_baseline": baseline}, ensure_ascii=False)
    row.clarify_round = clarify_round + 1
    db.commit()

    from infra.i18n import t

    if miss:
        slot_name = t("时间") if miss == "period" else t("展望窗口")
        intent_label = t(str(meta["intent_label"]))
        return {
            "status": "clarify_slot",
            "session_id": row.session_id,
            "query_id": row.id,
            "intent_id": iid,
            "intent_label": intent_label,
            "slot": miss,
            "prompt": t("「{q}」——请选择{slot}：", q=intent_label, slot=slot_name),
            "options": (
                [
                    {"value": "本周", "label": t("本周")},
                    {"value": "本月", "label": t("本月")},
                    {"value": "本季", "label": t("本季")},
                ]
                if miss == "period"
                else [
                    {"value": "7", "label": t("未来 7 天")},
                    {"value": "30", "label": t("未来 30 天")},
                ]
            ),
            "clarify_round": row.clarify_round,
        }

    intent_label = t(str(meta["intent_label"]))
    slot_txt = (
        t("（未来 {n} 天）", n=filled.get("horizon"))
        if iid == "pickup_gap"
        else t(
            "（{period} · {baseline}）",
            period=t(str(filled.get("period") or period_preset)),
            baseline=t(str(baseline)),
        )
    )
    return {
        "status": "confirm",
        "session_id": row.session_id,
        "query_id": row.id,
        "intent_id": iid,
        "intent_label": intent_label,
        "slots": filled,
        "prompt": t("确认一下：你是想问「{q}」{slot} 吗？", q=intent_label, slot=slot_txt),
        "clarify_round": row.clarify_round,
    }
