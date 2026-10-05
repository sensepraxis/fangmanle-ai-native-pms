# SPDX-License-Identifier: BUSL-1.1
"""排班 AI 建议包层：规则引擎（退房预测/缺口）为事实，LLM 生成解读与建议文案。

点击后才调系统 LLM（当前配置的厂商/模型，可插拔）；失败标明不可用，不用规则稿冒充 AI。
"""

from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import extract_json, format_insight_html
from commercial.ai_core.llm_service import chat, llm_identity, load_llm_config
from hk.staffing_service import build_ai_forecast
from infra.branding import brand_text
from infra.i18n import get_locale
from infra.i18n import t as _t


def _staffing_system_prompt() -> str:
    lang = "English" if get_locale().startswith("en") else "中文"
    return brand_text(
        """你是{APP_NAME}酒店 PMS 的「排班参谋」。
根据规则引擎给出的未来多日退房预测与班次缺口事实，输出 JSON（不要 markdown 围栏）：
{
  "summary":"≤40字总览",
  "facts":["排班事实2～4条"],
  "suggestions":["可执行建议1～3条"],
  "days":[{"date":"YYYY-MM-DD","reason":"≤60字现状解读","suggest":"≤40字建议结论"}],
  "confidence":"high|medium|low",
  "confidence_note":"≤40字"
}
要求：
1. days 必须覆盖快照中每一个 date（缺一不可），禁止编造日期或改动人数。
2. reason/suggest 必须与该日 need_clean / counts / 缺口一致，可润色但不得改数字事实。
3. 用户可见文案必须使用__LANG__；勿出现模型名、API、数据库等词。
4. 有缺口日优先给出可执行补班表述；无缺口日写清「无需改班」。"""
    ).replace("__LANG__", lang)


def _compact_days(days: list[dict]) -> list[dict]:
    out = []
    for d in days or []:
        out.append(
            {
                "date": d.get("date"),
                "label": d.get("label"),
                "need_clean": d.get("need_clean"),
                "counts": d.get("counts"),
                "want": d.get("want"),
                "delta": d.get("delta"),
                "has_gap": bool(d.get("has_gap")),
                "reason": d.get("reason"),
                "suggest": d.get("suggest"),
            }
        )
    return out


def _merge_day_text(rule_days: list[dict], llm_days: list) -> list[dict]:
    by_date = {}
    for raw in llm_days or []:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("date") or "").strip()
        if not key:
            continue
        by_date[key] = {
            "reason": str(raw.get("reason") or "").strip()[:120] or None,
            "suggest": str(raw.get("suggest") or "").strip()[:80] or None,
        }
    merged = []
    for d in rule_days:
        item = dict(d)
        hit = by_date.get(str(item.get("date") or ""))
        if hit:
            if hit.get("reason"):
                item["reason"] = hit["reason"]
            if hit.get("suggest"):
                item["suggest"] = hit["suggest"]
            item["ai_enriched"] = True
        else:
            item["ai_enriched"] = False
        merged.append(item)
    return merged


def _rule_fallback(forecast: dict, *, cfg: dict, err: str = "") -> dict[str, Any]:
    days = []
    for d in forecast.get("days") or []:
        item = dict(d)
        item["reason"] = ""
        item["suggest"] = ""
        days.append(item)
    gap_n = sum(1 for d in days if d.get("has_gap"))
    facts = [
        _t("规则引擎已测算未来 {n} 天退房与班次", n=len(days)),
        _t("其中缺口日 {n} 天（下列数字是排班数据，不是 AI 结论）", n=gap_n),
    ]
    out = {
        **forecast,
        "title": _t("AI 排班建议"),
        "subtitle": "",
        "disclaimer": "",
        "days": days,
        "narrative_html": "",
        "facts": facts,
        "suggestions": [],
        "summary": "",
        "confidence": "",
        "confidence_note": "",
        "source": "unavailable",
    }
    if err:
        out["llm_error"] = err[:200]
    return out


def narrate_staffing_ai(db: Session, hotel_id: int, opts: Optional[dict] = None) -> dict[str, Any]:
    """生成真实 LLM 包层的排班建议（含按日 reason/suggest）。"""
    opts = opts or {}
    days_n = int(opts.get("days") or 7)
    forecast = build_ai_forecast(db, hotel_id, days=days_n)
    cfg = load_llm_config(db)

    if not cfg.get("enabled", True):
        out = _rule_fallback(forecast, cfg=cfg, err=_t("大模型未启用"))
        return out

    snap = {
        "days": _compact_days(forecast.get("days") or []),
        "apply_from": forecast.get("apply_from"),
        "apply_to": forecast.get("apply_to"),
        "apply_count": forecast.get("apply_count"),
    }
    lang_line = "User-facing copy must be in English." if get_locale().startswith("en") else "用户可见文案必须全中文。"
    user_prompt = (
        "任务：生成排班 AI 解读与逐日建议。\n"
        f"{lang_line}\n"
        f"快照：\n{json.dumps(snap, ensure_ascii=False, default=str)}\n"
        "【规则摘录·仅素材】须基于快照重写 JSON，禁止把规则 reason/suggest 当最终答复原文。"
    )
    try:
        res = chat(
            db,
            [{"role": "user", "content": user_prompt}],
            extra_system=_staffing_system_prompt(),
            overrides={"temperature": 0.3, "max_tokens": 2200, "think": False},
        )
        parsed = extract_json(res.get("content") or "") or {}
        fact_list = parsed.get("facts") if isinstance(parsed.get("facts"), list) else []
        sug_list = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []
        html = format_insight_html(_t("排班事实"), fact_list, _t("增补建议"), sug_list)
        if not html and not parsed.get("days"):
            return _rule_fallback(forecast, cfg=cfg, err=_t("模型未返回可用内容"))

        merged_days = _merge_day_text(list(forecast.get("days") or []), parsed.get("days") or [])
        # 至少要有一部分被 LLM 覆盖，否则视为失败兜底（避免假 AI）
        enriched = sum(1 for d in merged_days if d.get("ai_enriched"))
        if enriched == 0 and not html:
            return _rule_fallback(forecast, cfg=cfg, err=_t("模型未覆盖任何日期"))

        if not html:
            return _rule_fallback(forecast, cfg=cfg, err=_t("模型未返回可用双栏解读"))

        conf = str(parsed.get("confidence") or "medium").lower()
        if conf not in ("high", "medium", "low"):
            conf = "medium"

        return {
            **forecast,
            "title": _t("AI 排班建议"),
            "subtitle": "",
            "disclaimer": "",
            "days": merged_days,
            "narrative_html": html,
            "facts": [str(x) for x in fact_list if str(x).strip()],
            "suggestions": [str(x) for x in sug_list if str(x).strip()],
            "summary": str(parsed.get("summary") or "")[:80],
            "confidence": conf,
            "confidence_note": str(parsed.get("confidence_note") or "")[:80],
            "source": "llm",
            **llm_identity(cfg, res),
            "enriched_days": enriched,
        }
    except HTTPException as e:
        return _rule_fallback(
            forecast,
            cfg=cfg,
            err=str(e.detail) if hasattr(e, "detail") else str(e),
        )
    except Exception as e:
        return _rule_fallback(forecast, cfg=cfg, err=str(e)[:200])
