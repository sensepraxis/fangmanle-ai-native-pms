# SPDX-License-Identifier: BUSL-1.1
"""AI 问数 · 回答模板注册表（表驱动，替代长 if/elif）。

``ai_ask_answering._template_answer`` 查本注册表；未注册 intent 走默认摘要。
"""

from __future__ import annotations

from typing import Any, Callable

from infra.i18n import t

# intent_id → (result, slots) -> (summary, points)
AnswerTemplateFn = Callable[[dict, dict], tuple[str, list[str]]]

ANSWER_TEMPLATE_REGISTRY: dict[str, AnswerTemplateFn] = {}


def register_answer_template(intent_id: str, fn: AnswerTemplateFn) -> None:
    ANSWER_TEMPLATE_REGISTRY[intent_id] = fn


def register_answer_templates(intent_ids: list[str], fn: AnswerTemplateFn) -> None:
    for iid in intent_ids:
        register_answer_template(iid, fn)


def get_answer_template(intent_id: str) -> AnswerTemplateFn | None:
    return ANSWER_TEMPLATE_REGISTRY.get(intent_id)


def _rows_points(rows: list, n: int = 3) -> list[str]:
    return [f"{r.get('label')}: {r.get('value')}" for r in rows[:n]]


def _tpl_followup_optimize(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    tips = result.get("playbook_tips") or m.get("playbook") or []
    prior = m.get("prior_summary") or t("上一轮结论")
    summary = t("围绕「{prior}」，可优先考虑以下方向。", prior=prior)
    points = [f"{tip.get('name')}: {tip.get('expected_impact')}" for tip in tips[:3]]
    return summary, points


def _tpl_followup_impact(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    prior = m.get("prior_summary") or t("当前结论")
    summary = t(
        "在「{prior}」基础上，若趋势延续，经营压力可能在下一周期继续显现。",
        prior=prior,
    )
    return summary, _rows_points(rows)


def _tpl_followup_diagnose(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    prior = m.get("prior_summary") or t("该现象")
    summary = t("「{prior}」主要可从下列因素理解。", prior=prior)
    return summary, _rows_points(rows[1:4] if len(rows) > 1 else rows)


def _tpl_followup_compare(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    prior = m.get("prior_summary") or t("结论")
    summary = t("对照上一轮「{prior}」的关键指标如下。", prior=prior)
    return summary, _rows_points(rows)


def _tpl_occupancy(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    period = t(str(slots.get("period") or "本期"))
    summary = t(
        "本期入住率 {occ}%，对比期 {base}%，变化 {delta} 个百分点（{period}）。",
        occ=m.get("occ_pct"),
        base=m.get("occ_pct_base"),
        delta=m.get("delta_pt"),
        period=t(str(m.get("baseline") or period)),
    )
    return summary, _rows_points(rows)


def _tpl_adr(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t(
        "本期 ADR ¥{adr}，对比期 ¥{base}，相对变化 {delta}%。",
        adr=m.get("adr"),
        base=m.get("adr_base"),
        delta=m.get("delta_pct"),
    )
    return summary, _rows_points(rows)


def _tpl_revpar(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t(
        "本期 RevPAR ¥{revpar}，对比期 ¥{base}，相对变化 {delta}%。",
        revpar=m.get("revpar"),
        base=m.get("revpar_base"),
        delta=m.get("delta_pct"),
    )
    return summary, _rows_points(rows)


def _tpl_revpar_trend(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t(
        "本期 RevPAR ¥{revpar}，OCC {occ}%，ADR ¥{adr}。",
        revpar=m.get("revpar"),
        occ=m.get("occ_pct"),
        adr=m.get("adr"),
    )
    return summary, _rows_points(rows)


def _tpl_channel_profit(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    period = t(str(slots.get("period") or "本期"))
    losing = m.get("losing") or []
    if losing:
        summary = t(
            "{period}有 {n} 个渠道净收益为负：{names}",
            period=period,
            n=m.get("losing_count", 0),
            names=", ".join(str(x) for x in losing),
        )
    else:
        summary = t(
            "{period}有 {n} 个渠道净收益为负。",
            period=period,
            n=m.get("losing_count", 0),
        )
    unit = t("元")
    return summary, [f"{r['label']}: {r['value']} {unit}" for r in rows[:3]]


def _tpl_ota_share(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    period = t(str(slots.get("period") or "本期"))
    ota = m.get("ota_pct")
    tail = t("已越过 55% 警戒线。") if m.get("over") else t("未超 55% 警戒线。")
    summary = t("{period} OTA 间夜占比 {ota}%，{tail}", period=period, ota=ota, tail=tail)
    return summary, [f"{r['label']} {r['value']}%" for r in rows[:3]]


def _tpl_business_churn(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t(
        "商务客占比 {pct}%，较对比期 {delta} 个百分点{tail}",
        pct=m.get("business_pct"),
        delta=m.get("delta_pt"),
        tail=t("，存在流失迹象。") if m.get("churn") else t("，结构尚可。"),
    )
    return summary, _rows_points(rows)


def _tpl_member_repurchase(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    from commercial.analytics.analytics_ai_locale import is_en_locale

    summary = t(
        "会员占比（复购代理）{pct}%，环比 {delta} 个百分点{tail}",
        pct=m.get("member_pct"),
        delta=m.get("delta_pt"),
        tail=t("，复购偏弱。") if m.get("worse") else ("." if is_en_locale() else "。"),
    )
    return summary, _rows_points(rows)


def _tpl_pickup_gap(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t(
        "未来预订缺口 {gap} 间夜（约 {pct}%）。",
        gap=m.get("gap"),
        pct=m.get("gap_pct"),
    )
    return summary, _rows_points(rows)


def _tpl_guest_top_payment(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    n = m.get("top_n") or len(rows)
    summary = t("全生命周期累计消费最高的前 {n} 位客户如下（已脱敏）。", n=n)
    if result.get("need_pii_ack"):
        summary += t("查看明细需管理者二次确认。")
    points = [
        f"{r.get('guest_id') or r.get('label')} · {r.get('guest_name') or r.get('label')}: ¥{r.get('value')}"
        for r in rows[:3]
    ]
    return summary, points


def _tpl_guest_top_stay(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    n = m.get("top_n") or len(rows)
    summary = t("到店次数最多的前 {n} 位客户如下（已脱敏）。", n=n)
    if result.get("need_pii_ack"):
        summary += t("查看明细需管理者二次确认。")
    unit = t("次")
    points = [
        f"{r.get('guest_id') or r.get('label')} · {r.get('guest_name') or r.get('label')}: {r.get('value')} {unit}"
        for r in rows[:3]
    ]
    return summary, points


def _tpl_guest_aov(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    count = m.get("guest_count") or sum(int(r.get("value") or 0) for r in rows)
    summary = t("客单价分布共覆盖 {n} 位客户（全生命周期）。", n=count)
    unit = t("人")
    return summary, [f"{r.get('label')}: {r.get('value')} {unit}" for r in rows[:4]]


def _tpl_guest_churn(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    thr = m.get("threshold_days") or 90
    summary = t(
        "沉睡客户（≥{thr} 天未住）共 {n} 人，以下为脱敏名单。",
        thr=thr,
        n=m.get("count") or len(rows),
    )
    points = [
        t("{name}：未住 {days} 天", name=r.get("guest_name") or r.get("label"), days=r.get("value")) for r in rows[:3]
    ]
    return summary, points


def _tpl_guest_segment(result: dict, slots: dict) -> tuple[str, list[str]]:
    m = result.get("metrics") or {}
    rows = result.get("rows") or []
    summary = t("按标签分群共 {n} 个标签有客户。", n=m.get("tag_count") or len(rows))
    unit = t("人")
    return summary, [f"{r.get('label')}: {r.get('value')} {unit}" for r in rows[:3]]


def _register_builtins() -> None:
    register_answer_template("followup_optimize", _tpl_followup_optimize)
    register_answer_template("followup_impact", _tpl_followup_impact)
    register_answer_template("followup_diagnose", _tpl_followup_diagnose)
    register_answer_template("followup_compare", _tpl_followup_compare)
    register_answer_templates(
        ["occupancy_compare_mom", "occupancy_get_value", "occupancy_trend"],
        _tpl_occupancy,
    )
    register_answer_templates(["adr_compare_mom", "adr_get_value"], _tpl_adr)
    register_answer_templates(["revpar_compare_mom", "revpar_get_value"], _tpl_revpar)
    register_answer_template("revpar_trend", _tpl_revpar_trend)
    register_answer_template("channel_profit_loss", _tpl_channel_profit)
    register_answer_template("ota_share_ratio", _tpl_ota_share)
    register_answer_template("business_churn", _tpl_business_churn)
    register_answer_template("member_repurchase", _tpl_member_repurchase)
    register_answer_template("pickup_gap", _tpl_pickup_gap)
    register_answer_template("guest_top_rank_cumulative_payment", _tpl_guest_top_payment)
    register_answer_template("guest_top_rank_stay_count", _tpl_guest_top_stay)
    register_answer_template("guest_distribution_avg_order_value", _tpl_guest_aov)
    register_answer_template("guest_churn_warning_last_stay_date", _tpl_guest_churn)
    register_answer_template("guest_segment_count_by_tag", _tpl_guest_segment)


_register_builtins()
