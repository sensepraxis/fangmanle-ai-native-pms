# SPDX-License-Identifier: BUSL-1.1
"""
价格助手服务：特征层 + §5.6 规则优化 + 三档执行 + 审计三联单。
合规铁律：仅建议、人拍板、绝不自动跟价/爬登录态。
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.i18n import get_locale, t
from pricing.pricing_assistant import recommendation_service as _pricing_recommendation_service

_CHANNEL_MSGID = {
    "direct": "官网直订",
    "ota_ctrip": "携程",
    "ota_meituan": "美团",
    "ota_fliggy": "飞猪",
    "ota_douyin": "抖音",
}


def _channel_label(code: str) -> str:
    key = str(code or "")
    msgid = _CHANNEL_MSGID.get(key)
    if msgid:
        return t(msgid)
    return key or t("未标注渠道")


def narrate_explain_with_llm(db: Session, reco_key: str) -> dict:
    """
    调用系统配置的 LLM，基于 explain_json 快照生成店长可读的白话说明。
    数值以快照为准，不重新算价；规则白话只作素材，失败则 source=unavailable。
    """
    detail = _pricing_recommendation_service.get_recommendation(db, reco_key)
    explain = detail.get("explain_json") or {}
    if not explain:
        raise InvalidStateError(t("该建议尚无推导快照，请先重新生成建议"))
    factors = explain.get("factors") or []
    factor_brief = []
    for f in factors:
        if f.get("muted"):
            continue
        delta = float(f.get("delta") or 0)
        name = str(f.get("name") or t("因子")).split("（")[0].strip() or t("因子")
        factor_brief.append({"name": name, "delta": round(delta, 1)})
    compliance = explain.get("compliance") or {}
    fair = explain.get("fair_price_band") or {}
    ch = str(detail.get("channel") or "")
    channel_label = _channel_label(ch)
    try:
        from commercial.ai_core.llm_service import (
            chat as llm_chat,
        )
        from commercial.ai_core.llm_service import (
            format_llm_fallback_note,
            llm_identity,
            load_llm_config,
        )

        llm_cfg = load_llm_config(db)
    except Exception:
        llm_cfg = {}
        llm_identity = lambda cfg, res=None: {
            "model": (cfg or {}).get("model"),
            "provider": (cfg or {}).get("provider") or "ollama",
            "provider_label": (cfg or {}).get("provider") or "ollama",
        }
        format_llm_fallback_note = lambda cfg, err, **kw: t(
            "（当前大模型暂不可用：{err}；以上为规则化说明）", err=str(err)[:80]
        )
        llm_chat = None
    locale = get_locale()
    en = str(locale or "").lower().startswith("en")
    if en:
        system = (
            "You are a hotel revenue management advisor briefing the GM on a rate change.\n"
            "Using the pricing snapshot, write a short English explanation: why move from current to suggested, "
            "name the main factors, and note any compliance items needing human review.\n"
            "Rules: use only numbers in the snapshot; do not reprice or invent data; do not echo this prompt or output JSON/Markdown; "
            "about 150–250 words in 2–3 short paragraphs."
        )
        snapshot = {
            "room_type": detail.get("room_type_name"),
            "stay_date": detail.get("stay_date"),
            "channel": channel_label,
            "current_list_price": detail.get("current_price"),
            "suggested_list_price": detail.get("suggested_price"),
            "suggested_net_base": detail.get("suggested_base"),
            "est_net": detail.get("est_n"),
            "base_rate": explain.get("base_rate"),
            "factor_sum": explain.get("factor_sum"),
            "factors": factor_brief,
            "compliance": {
                "daily_uplift_ok": bool(compliance.get("cap_ok")),
                "cost_floor_ok": bool(compliance.get("cost_floor_ok")),
                "net_floor_ok": bool(compliance.get("n_floor_ok")),
                "net": compliance.get("n_est"),
                "net_floor": compliance.get("n_floor"),
            },
            "fair_band_note": (fair.get("msg") or "").strip() or None,
            "must_stress": "Suggestion only — GM must confirm before changing rates; the system never auto-follows.",
        }
        user = f"Explain this suggested rate to the GM using the snapshot below.\n\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}"
    else:
        system = "你是酒店收益管理顾问，面向店长口头汇报调价理由。\n根据用户给出的「定价快照」写一段中文说明即可：说清为何从当前价调到建议价，点到主要因子与需要人工留意的合规点。\n要求：只依据快照里的数字，不要改价、不要编造未给出的数据；不要复述本系统提示或输出 JSON/Markdown；约 150～250 字，分 2～3 段。"
        snapshot = {
            "房型": detail.get("room_type_name"),
            "入住日": detail.get("stay_date"),
            "渠道": channel_label,
            "当前挂牌价": detail.get("current_price"),
            "建议挂牌价": detail.get("suggested_price"),
            "建议结算底价": detail.get("suggested_base"),
            "预估净到手": detail.get("est_n"),
            "基准价": explain.get("base_rate"),
            "因子合计": explain.get("factor_sum"),
            "因子明细": factor_brief,
            "合规": {
                "相对前日涨幅通过": bool(compliance.get("cap_ok")),
                "成本底线通过": bool(compliance.get("cost_floor_ok")),
                "净到手下限通过": bool(compliance.get("n_floor_ok")),
                "净到手": compliance.get("n_est"),
                "净到手下限": compliance.get("n_floor"),
            },
            "公平价带提示": (fair.get("msg") or "").strip() or None,
            "须强调": "本结果仅为建议，须店长确认后改价，系统不会自动跟价。",
        }
        user = f"请根据下列定价快照，向店长解释本次建议价。\n\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}"
    fallback = _rule_based_narration(detail, explain)
    user = user + (
        ("\n\n[Rule excerpt for material only — rewrite; do not copy as the answer]\n" + fallback)
        if en
        else ("\n\n【规则摘录·仅素材】须基于快照重写白话说明，禁止原样照抄。\n" + fallback)
    )

    def _looks_like_prompt_echo(text: str) -> bool:
        """模型若把指令/快照原文吐回来，视为调用失败。"""
        raw = text or ""
        bad = (
            "禁止编造",
            "不要复述本系统提示",
            "请根据下列定价快照",
            "请输出店长可读",
            '"房型"',
            "factor_sum",
            "n_floor_ok",
            "规则：①",
            "Explain this suggested rate",
            "must_stress",
            "规则摘录",
        )
        hits = sum(1 for b in bad if b in raw)
        return hits >= 2 or len(raw) > 900

    identity: dict = {}
    narrative = ""
    source = "unavailable"
    llm_error = ""
    try:
        from commercial.ai_core.llm_service import chat as llm_chat

        if llm_chat is None:
            raise RuntimeError(t("大模型未接入"))
        resp = llm_chat(
            db, [{"role": "user", "content": user}], None, overrides={"system_prompt": system, "temperature": 0.35}
        )
        raw = (resp.get("content") or "").strip()
        if not raw or _looks_like_prompt_echo(raw):
            llm_error = t("模型返回空内容") if not raw else t("模型输出不可用")
        else:
            narrative = raw
            identity = llm_identity(llm_cfg, resp)
            source = "llm"
    except Exception as e:
        llm_error = str(e)[:200]
        identity = {}
        source = "unavailable"
        narrative = ""
    if isinstance(identity, dict) and identity.get("provider_label"):
        pl = str(identity.get("provider_label") or "")
        if "本地" in pl:
            identity = {**identity, "provider_label": pl.replace("本地", t("本地"))}
    if source != "llm":
        identity = {}
    out = {
        "reco_id": detail.get("reco_id"),
        "narrative": narrative,
        **identity,
        "source": source,
        "explain_json": explain,
        "recommendation": {
            "room_type_name": detail.get("room_type_name"),
            "stay_date": detail.get("stay_date"),
            "channel": detail.get("channel"),
            "current_price": detail.get("current_price"),
            "suggested_price": detail.get("suggested_price"),
            "suggested_base": detail.get("suggested_base"),
            "est_n": detail.get("est_n"),
            "top_reasons": detail.get("top_reasons"),
        },
    }
    if llm_error and source != "llm":
        out["llm_error"] = llm_error
    return out


def _rule_based_narration(detail: dict, explain: dict) -> str:
    """LLM 不可用时的规则化白话说明（随 locale）。"""
    factors = [f for f in explain.get("factors") or [] if not f.get("muted")]
    ch = str(detail.get("channel") or "")
    channel_label = _channel_label(ch) if ch else t("当前渠道")
    parts = [
        t(
            "「{room}」 {date} · {channel}：建议从现价 {cur} 元调至 {sug} 元（基准价 {base} 元，因子合计约 {sum} 元）。",
            room=detail.get("room_type_name"),
            date=detail.get("stay_date"),
            channel=channel_label,
            cur=detail.get("current_price"),
            sug=explain.get("suggested_price"),
            base=explain.get("base_rate"),
            sum=explain.get("factor_sum"),
        )
    ]
    if factors:
        bits = []
        for f in factors[:4]:
            d = float(f.get("delta") or 0)
            name = str(f.get("name") or t("因子")).split("（")[0].strip()
            delta_s = f"+{int(d)}" if d >= 0 else str(int(d))
            bits.append(t("{name} {delta} 元", name=name, delta=delta_s))
        parts.append(t("主要拉动：{bits}。", bits="；".join(bits)))
    c = explain.get("compliance") or {}
    gate_ok = bool(c.get("cap_ok")) and bool(c.get("cost_floor_ok")) and bool(c.get("n_floor_ok"))
    if gate_ok:
        parts.append(t("涨幅封顶、成本底线与净到手下限均已通过。"))
    else:
        notes = []
        if not c.get("cap_ok"):
            notes.append(t("涨幅封顶需关注"))
        if not c.get("cost_floor_ok"):
            notes.append(t("成本底线需复核"))
        if not c.get("n_floor_ok"):
            notes.append(
                t("净到手 {n} 低于下限 {floor}，建议店长确认后再采纳", n=c.get("n_est"), floor=c.get("n_floor"))
            )
        parts.append(t("合规提示：{notes}。", notes="；".join(notes)))
    fair = explain.get("fair_price_band") or {}
    if fair.get("msg"):
        parts.append(str(fair.get("msg")))
    parts.append(t("以上仅为建议，须店长确认后改价，系统不会自动跟价。"))
    return "\n\n".join(parts)
