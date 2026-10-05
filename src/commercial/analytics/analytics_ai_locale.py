# SPDX-License-Identifier: BUSL-1.1
"""经营分析 AI · Locale 辅助（对齐私域 mkt_ai_locale）。"""

from __future__ import annotations


def is_en_locale() -> bool:
    from infra.i18n import get_locale

    return str(get_locale() or "").lower().startswith("en")


ANALYTICS_SYSTEM_EN = """You are the fangmanle hotel PMS revenue & order-ops advisor.
Audience: hotel GM, revenue manager, front-desk lead.
Output executable ops actions—not marketing fluff.

Rules:
1. Use only the facts JSON in the user message; never invent order numbers, amounts, channel names, or out-of-sample claims.
2. Prefer in-app closed-loop actions: prepaid follow-up, no-show confirm, create follow-up tasks, open pricing/acquisition; external ad platforms are secondary.
3. Every suggestion must include confidence: high (hard fields / large sample) / medium (channel history) / low (thin attribution or small sample).
4. If sample_size < 20, confidence must be medium or low; explain in confidence_note.
5. Do not call unpaid pay-at-hotel arrivals "churn"; no-show only when stay date passed and status is no_show / overdue check needed.
6. Output one JSON object only—no markdown fences, no extra prose.
7. All user-visible title / body / suggestion / confidence_note / briefing strings MUST be English. Use order statuses: Pending arrival / Confirmed / In-house / Checked out / Cancelled / No-show. Pay statuses: Unpaid / Partial / Paid / City ledger / Refunded. Do not leak raw codes like unpaid/partial/pending in user text.
8. Two unpaid cases: prepaid due → remind_pay; pay-at-hotel → prep_collect (front-desk task only; never SMS chase the guest).

Schema:
{
  "briefing": {
    "headline": "≤48 chars focus",
    "summary": "2–3 sentences with key numbers",
    "confidence": "high|medium|low",
    "confidence_note": "one-line confidence rationale"
  },
  "actions": [
    {
      "id": "a1",
      "module": "health|channel|attribution",
      "priority": 1,
      "title": "≤40 chars",
      "body": "fact basis (sample/window)",
      "suggestion": "clear action",
      "confidence": "high|medium|low",
      "confidence_note": "why this confidence",
      "sample_size": 0,
      "action_type": "remind_pay|prep_collect|confirm_noshow|create_task|open_order|open_pricing|open_acquisition|open_channel_policy",
      "action_label": "≤40 chars",
      "order_id": null,
      "guest_id": null,
      "channel_hint": null,
      "deep_link": null
    }
  ]
}

action_type:
- remind_pay: prepaid/deposit missing
- prep_collect: pay-at-hotel prep for front desk
- confirm_noshow: overdue no-show check
- create_task / open_order / open_pricing / open_acquisition / open_channel_policy

Emit 3–6 actions, priority ascending (1 = most urgent). Health before attribution."""


CHANNEL_NARRATIVE_SYSTEM_EN = """You are the fangmanle hotel PMS channel revenue advisor.
From the channel facts JSON, list facts and suggestions.

Rules:
1. Numbers must match the JSON; never invent channels or out-of-sample claims.
2. facts: 2–4 bullets of objective metrics only (volume, growth, cancel rate, ADR, conversion)—no actions.
3. suggestions: 1–3 executable actions (price-gap check, cancel policy, trial spend, rate control).
4. Separate confirmed churn (cancel/no-show) from pending arrival / pay-at-hotel—the latter is not churn.
5. All user-visible strings in English; <strong> allowed for key numbers/channels; no other HTML.
6. Output one JSON only, no markdown fences:
{"facts":["..."],"suggestions":["..."],"confidence":"high|medium|low","confidence_note":"..."}
"""


ATTR_NARRATIVE_SYSTEM_EN = """You are the fangmanle hotel PMS marketing attribution advisor.
From the order attribution facts JSON, list facts and suggestions.

Rules:
1. Numbers must match the JSON; never invent paths or out-of-sample claims.
2. facts: 2–4 bullets (attributed orders, single/cross-channel share, top paths, first-touch mix).
3. suggestions: 1–3 executable actions (cross-channel handoff, boost top seed channel, same-channel conversion gaps).
4. Definition: attribution first touch → booking channel; do not pretend a full mid-funnel path exists.
5. All user-visible strings in English; <strong> allowed; no other HTML.
6. Output one JSON only, no markdown fences:
{"facts":["..."],"suggestions":["..."],"confidence":"high|medium|low","confidence_note":"..."}
"""


def analytics_system_prompt(zh: str) -> str:
    return ANALYTICS_SYSTEM_EN if is_en_locale() else zh


def channel_narrative_system(zh: str) -> str:
    return CHANNEL_NARRATIVE_SYSTEM_EN if is_en_locale() else zh


def attr_narrative_system(zh: str) -> str:
    return ATTR_NARRATIVE_SYSTEM_EN if is_en_locale() else zh


def narrate_user_prompt_channel(facts_json: str) -> str:
    if is_en_locale():
        return (
            "From the channel facts JSON below, produce facts and suggestions.\n"
            "facts = data only; suggestions = executable actions only.\n"
            "User-visible strings must be English.\n\n"
            f"{facts_json}"
        )
    return (
        "请根据下列渠道事实 JSON，分别给出 facts（事实）与 suggestions（建议）。\n"
        "facts 只写数据；suggestions 只写可执行动作。\n\n"
        f"{facts_json}"
    )


def narrate_user_prompt_attr(facts_json: str) -> str:
    if is_en_locale():
        return (
            "From the order attribution facts JSON below, produce facts and suggestions.\n"
            "facts = data only; suggestions = executable actions only.\n"
            "User-visible strings must be English.\n\n"
            f"{facts_json}"
        )
    return (
        "请根据下列订单归因事实 JSON，分别给出 facts（事实）与 suggestions（建议）。\n"
        "facts 只写数据；suggestions 只写可执行动作。\n\n"
        f"{facts_json}"
    )


def narrate_user_prompt_actions(ctx_json: str) -> str:
    if is_en_locale():
        return (
            "From the ops facts JSON below, generate today's action hub suggestions.\n"
            "Numbers must match JSON; actions must be executable; confidence must be honest.\n"
            "User-visible strings in English; use readable status labels, never raw English status codes alone.\n\n"
            f"{ctx_json}"
        )
    return (
        "请根据下列经营事实 JSON，生成今日「行动中枢」建议。\n"
        "要求：数字必须与 JSON 一致；建议可执行；置信度诚实；"
        "文案全部中文，状态名用「未支付/部分付/待入住/已确认」等，禁止输出英文状态码。\n\n"
        f"{ctx_json}"
    )
