# SPDX-License-Identifier: BUSL-1.1
"""经营分析 AI 行动中枢 —— 基于订单/渠道/归因事实，生成可执行建议（本地 LLM + 规则兜底）。"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import extract_json, format_insight_html
from commercial.ai_core.llm_service import chat as llm_chat
from commercial.ai_core.llm_service import llm_identity, load_llm_config
from commercial.analytics.analytics_ai_locale import (
    analytics_system_prompt,
    attr_narrative_system,
    channel_narrative_system,
    narrate_user_prompt_actions,
    narrate_user_prompt_attr,
    narrate_user_prompt_channel,
)
from infra.i18n import t
from models import Campaign, Channel, ChannelAttribution, CrmTask, Guest, Order

# 对外文案用中文；库内仍存英文码
_ORDER_STATUS_CN = {
    "pending": "待入住",
    "confirmed": "已确认",
    "checked_in": "在住",
    "checked_out": "已退房",
    "cancelled": "已取消",
    "no_show": "未到店",
}
_PAY_STATUS_CN = {
    "unpaid": "未支付",
    "partial": "部分付",
    "paid": "已支付",
    "refunded": "已退",
    "on_account": "挂账",
}
# 不用 \b：中文与英文码相邻时（如「支付状态partial」）无单词边界
_EN_LABEL_RE = re.compile(
    r"(?<![A-Za-z0-9_])("
    r"checked_out|checked_in|on_account|no_show|noshow|"
    r"cancelled|confirmed|pending|"
    r"unpaid|partial|paid|refunded|"
    r"payment_status|order_status"
    r")(?![A-Za-z0-9_])",
    re.I,
)
_EN_LABEL_MAP = {
    "checked_out": "已退房",
    "checked_in": "在住",
    "on_account": "挂账",
    "no_show": "未到店",
    "noshow": "未到店",
    "cancelled": "已取消",
    "confirmed": "已确认",
    "pending": "待入住",
    "unpaid": "未支付",
    "partial": "部分付",
    "paid": "已支付",
    "refunded": "已退",
    "payment_status": "支付状态",
    "order_status": "订单状态",
}


def _status_cn(code: Optional[str]) -> str:
    c = (code or "").strip()
    msgid = _ORDER_STATUS_CN.get(c)
    return t(msgid) if msgid else (c or "—")


def _pay_cn(code: Optional[str]) -> str:
    c = (code or "").strip()
    msgid = _PAY_STATUS_CN.get(c)
    return t(msgid) if msgid else (c or "—")


def _localize_text(text: str) -> str:
    """把文案中残留的英文状态码替换为当前 locale 文案。"""
    if not text:
        return text

    def repl(m: re.Match) -> str:
        raw = m.group(1)
        zh = _EN_LABEL_MAP.get(raw.lower(), raw)
        return t(zh) if zh != raw else raw

    return _EN_LABEL_RE.sub(repl, text)


ANALYTICS_SYSTEM = """你是「AI-Native PMS」的收益与订单运营参谋（Revenue & Order Ops Advisor）。
服务对象：单体/区域酒店的店长、收益经理、前台主管。
你的产出不是漂亮文案，而是「可执行的经营动作」。

## 工作原则
1. 只依据用户消息中的事实 JSON，禁止编造订单号、金额、渠道名或样本外结论。
2. 优先内部可闭环动作：预付跟进、确认未到店、生成跟进任务、跳转价格助手/获客；外链投放平台仅作次级建议。
3. 每条建议必须标注置信度：high（库内硬字段/大样本）/ medium（渠道历史推断）/ low（归因不全或样本不足）。
4. 样本数 < 20 的推断一律 medium 或 low，并在 confidence_note 写明原因。
5. 禁止把「待到店未付」说成「已流失」；未到店仅当入住日已过且状态为未到店 / 或建议核查逾期未办。
6. 输出必须是单一 JSON 对象，不要 Markdown 代码围栏，不要额外解释。
7. 面向用户的 title / body / suggestion / confidence_note / briefing 必须全部使用中文。订单状态用「待入住/已确认/在住/已退房/已取消/未到店」，支付状态用「未支付/部分付/已支付/挂账/已退」。严禁在文案中出现 unpaid、partial、pending、confirmed、paid、no_show 等英文字段值。
8. 区分两类未结清：应预付未到账用 remind_pay（跟进预付：提醒付款或核对渠道到账）；到店付口径用 prep_collect（到店收款准备，写前台任务，禁止对客人发催付短信）。

## 输出 schema
{
  "briefing": {
    "headline": "≤28字今日经营焦点",
    "summary": "2～3句，含关键数字",
    "confidence": "high|medium|low",
    "confidence_note": "一句话说明可信度依据"
  },
  "actions": [
    {
      "id": "a1",
      "module": "health|channel|attribution",
      "priority": 1,
      "title": "≤20字标题",
      "body": "事实依据（含样本/窗口）",
      "suggestion": "明确建议动作",
      "confidence": "high|medium|low",
      "confidence_note": "为何是该置信度",
      "sample_size": 0,
      "action_type": "remind_pay|prep_collect|confirm_noshow|create_task|open_order|open_pricing|open_acquisition|open_channel_policy",
      "action_label": "按钮文案≤8字",
      "order_id": null,
      "guest_id": null,
      "channel_hint": null,
      "deep_link": null
    }
  ]
}

## action_type 选用
- remind_pay：应预付/订金未到账，跟进预付（提醒客人付款，或核对 OTA/券商到账）
- prep_collect：到店付口径，生成前台到店收款准备（不要催付客人）
- confirm_noshow：逾期未办，建议核查并标记未到店
- create_task：一般跟进任务（企微/前台）
- open_order：需打开具体订单
- open_pricing：提价/控价试探
- open_acquisition：加预算/内容投放类（须 low/medium）
- open_channel_policy：退改政策/配额类建议

actions 输出 3～6 条，按 priority 升序（1 最紧急）。健康类优先于归因类。"""


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("模型返回为空")
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.I).strip()
    data = extract_json(raw)
    if not data:
        raise ValueError("未找到 JSON")
    return data


def _conf_rank(c: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get((c or "").lower(), 0)


def build_analytics_context(db: Session, hotel_id: int) -> dict[str, Any]:
    """从订单库聚合经营分析上下文（供 LLM 与规则兜底共用）。"""
    today = date.today()
    d0 = today - timedelta(days=3)
    d1 = today + timedelta(days=3)
    d30 = today - timedelta(days=29)

    channels = {c.id: c for c in db.query(Channel).all()}
    orders = db.query(Order).filter_by(hotel_id=hotel_id).all()
    guest_ids = {o.guest_id for o in orders if o.guest_id}
    guests = {g.id: g for g in (db.query(Guest).filter(Guest.id.in_(guest_ids)).all() if guest_ids else [])}

    OPEN = {"pending", "confirmed"}
    CHURN_CANCEL = "cancelled"

    from finance.pay_risk import classify_near_pay_action

    def is_overdue(o: Order) -> bool:
        return bool(o.check_in and o.check_in < today and (o.status or "") in OPEN)

    def is_confirmed_noshow(o: Order) -> bool:
        return (o.status or "") == "no_show" and bool(o.check_in and o.check_in <= today)

    def is_cancelled(o: Order) -> bool:
        return (o.status or "") == CHURN_CANCEL

    win = [o for o in orders if o.check_in and d0 <= o.check_in <= d1]
    win30 = [o for o in orders if o.check_in and d30 <= o.check_in <= today]

    prepaid_risks = []
    collect_preps = []
    for o in orders:
        act = classify_near_pay_action(o, channels.get(o.channel_id), today)
        if act == "remind_pay":
            prepaid_risks.append(o)
        elif act == "prep_collect":
            collect_preps.append(o)
    prepaid_risks.sort(key=lambda x: (-float(x.total_amount or 0), x.check_in or today))
    collect_preps.sort(key=lambda x: (-float(x.total_amount or 0), x.check_in or today))
    # 兼容旧变量名：pay_risks = 应预付未到账（跟进）
    pay_risks = prepaid_risks
    overdues = sorted([o for o in orders if is_overdue(o)], key=lambda x: x.check_in or today)
    cancelled_n = sum(1 for o in win if is_cancelled(o))
    noshow_n = sum(1 for o in win if is_confirmed_noshow(o))
    awaiting_n = sum(1 for o in win if o.check_in and o.check_in > today and (o.status or "") in OPEN)

    # 渠道取消率（30 日）
    ch_stat: dict[str, dict] = {}
    for o in win30:
        ch = channels.get(o.channel_id)
        name = ch.name if ch else "未标注"
        code = ch.code if ch else "other"
        if name not in ch_stat:
            ch_stat[name] = {
                "channel": name,
                "code": code,
                "bookings": 0,
                "churn": 0,
                "revenue": 0.0,
                "nights": 0,
            }
        st = ch_stat[name]
        st["bookings"] += 1
        st["revenue"] += max(0.0, float(o.total_amount or 0) - float(o.other_amount or 0))
        st["nights"] += max(1, int(o.nights or 1)) * max(1, int(o.rooms or 1))
        if is_cancelled(o) or is_confirmed_noshow(o):
            st["churn"] += 1

    channel_rows = []
    for v in ch_stat.values():
        bn = v["bookings"] or 1
        channel_rows.append(
            {
                **v,
                "cancel_rate_pct": round(100.0 * v["churn"] / bn, 1),
                "adr": round(v["revenue"] / (v["nights"] or 1), 0),
            }
        )
    channel_rows.sort(key=lambda x: (-x["cancel_rate_pct"], -x["bookings"]))

    # 小红书环比（粗）
    prev0, prev1 = d30 - timedelta(days=30), d30 - timedelta(days=1)

    def xhs_count(lo: date, hi: date) -> int:
        n = 0
        for o in orders:
            if not o.check_in or not (lo <= o.check_in <= hi):
                continue
            ch = channels.get(o.channel_id)
            if ch and (ch.code or "").lower() == "xiaohongshu":
                n += 1
        return n

    xhs_cur = xhs_count(d30, today)
    xhs_prev = xhs_count(prev0, prev1)
    xhs_delta = round(100.0 * (xhs_cur - xhs_prev) / xhs_prev, 0) if xhs_prev else (100.0 if xhs_cur else 0.0)

    camps = db.query(Campaign).filter_by(hotel_id=hotel_id).all()
    xhs_camps = [c for c in camps if (c.channel or "") == "xiaohongshu"]
    xhs_roi = None
    if xhs_camps and xhs_camps[0].roi is not None:
        xhs_roi = float(xhs_camps[0].roi)
    elif xhs_camps:
        sp = float(xhs_camps[0].spend or 0) or 1
        xhs_roi = round(float(xhs_camps[0].attributed_rev or 0) / sp, 1)

    attrs = db.query(ChannelAttribution).filter(ChannelAttribution.hotel_id == hotel_id).limit(200).all()
    attr_n = len(attrs)

    def slim_order(o: Order) -> dict:
        ch = channels.get(o.channel_id)
        g = guests.get(o.guest_id) if o.guest_id else None
        st = o.status or ""
        pay = o.payment_status or ""
        return {
            "order_id": o.id,
            "order_no": o.order_no,
            "guest_id": o.guest_id,
            "guest": (g.name if g else None) or "客人",
            "channel": ch.name if ch else "未标注",
            "amount": round(float(o.total_amount or 0), 2),
            "check_in": o.check_in.isoformat() if o.check_in else None,
            "status": _status_cn(st),
            "payment_status": _pay_cn(pay),
        }

    order_risks = []
    for o in pay_risks[:12]:
        order_risks.append(
            {
                **slim_order(o),
                "risk_code": "pay",
                "risk_label": t("预付跟进"),
                "score": 78,
                "reason": t(
                    "入住日 {date} · 支付状态{pay} · 应预付/订金未到账",
                    date=o.check_in,
                    pay=_pay_cn(o.payment_status or "unpaid"),
                ),
                "confidence": "high",
                "action_type": "remind_pay",
            }
        )
    for o in collect_preps[:10]:
        order_risks.append(
            {
                **slim_order(o),
                "risk_code": "collect",
                "risk_label": t("到店收款"),
                "score": 55,
                "reason": t(
                    "入住日 {date} · 支付状态{pay} · 到店付口径，前台交接收款即可",
                    date=o.check_in,
                    pay=_pay_cn(o.payment_status or "unpaid"),
                ),
                "confidence": "high",
                "action_type": "prep_collect",
            }
        )
    for o in overdues[:10]:
        order_risks.append(
            {
                **slim_order(o),
                "risk_code": "overdue",
                "risk_label": t("逾期未办"),
                "score": 80,
                "reason": t(
                    "入住日 {date} 已过，状态仍为{status}，建议核查是否标记未到店",
                    date=o.check_in,
                    status=_status_cn(o.status),
                ),
                "confidence": "high",
                "action_type": "confirm_noshow",
            }
        )

    # 渠道历史取消率 → 临近入住 confirmed 单打取消风险标签
    ch_cancel = {r["channel"]: r["cancel_rate_pct"] for r in channel_rows if r["bookings"] >= 5}
    for o in orders:
        if (o.status or "") not in OPEN or not o.check_in:
            continue
        if o.check_in < today or o.check_in > today + timedelta(days=3):
            continue
        ch = channels.get(o.channel_id)
        name = ch.name if ch else ""
        rate = ch_cancel.get(name, 0)
        if rate < 18:
            continue
        if any(x["order_id"] == o.id for x in order_risks):
            continue
        order_risks.append(
            {
                **slim_order(o),
                "risk_code": "cancel",
                "risk_label": t("取消风险 {pct}%", pct=min(95, int(rate + 10))),
                "score": min(95, int(rate + 10)),
                "reason": t(
                    "渠道「{name}」近30日取消/未到店率约 {rate}%（样本≥5），入住临近",
                    name=name,
                    rate=rate,
                ),
                "confidence": "medium" if rate < 30 else "medium",
            }
        )

    return {
        "as_of": today.isoformat(),
        "hotel_id": hotel_id,
        "windows": {
            "health": {"from": d0.isoformat(), "to": d1.isoformat()},
            "channel_30d": {"from": d30.isoformat(), "to": today.isoformat()},
        },
        "kpi": {
            "win_bookings": len(win),
            "cancelled": cancelled_n,
            "confirmed_noshow": noshow_n,
            "awaiting": awaiting_n,
            "pay_risk_count": len(pay_risks),
            "collect_prep_count": len(collect_preps),
            "overdue_count": len(overdues),
            "xhs_bookings_30d": xhs_cur,
            "xhs_delta_pct": int(xhs_delta),
            "xhs_roi": xhs_roi,
            "attribution_rows": attr_n,
            "campaigns": len(camps),
        },
        "pay_risk_top": [slim_order(o) for o in pay_risks[:5]],
        "collect_prep_top": [slim_order(o) for o in collect_preps[:5]],
        "overdue_top": [slim_order(o) for o in overdues[:5]],
        "channel_quality": channel_rows[:8],
        "order_risks": order_risks[:25],
    }


def _rule_fallback(ctx: dict) -> dict:
    kpi = ctx.get("kpi") or {}
    actions = []
    pid = 1

    pay_n = int(kpi.get("pay_risk_count") or 0)
    if pay_n:
        top = (ctx.get("pay_risk_top") or [{}])[0]
        actions.append(
            {
                "id": f"r{pid}",
                "module": "health",
                "priority": pid,
                "title": t("跟进 {n} 笔应预付未到账", n=pay_n),
                "body": t(
                    "近48h入住、应预付/订金未齐共 {n} 单，金额示例 ¥{amount}。",
                    n=pay_n,
                    amount=top.get("amount") or 0,
                ),
                "suggestion": t("提醒客人完成预付，或核对 OTA/券商是否已结算到账；待到店不算流失。"),
                "confidence": "high",
                "confidence_note": t("基于渠道预付口径、订金与支付状态"),
                "sample_size": pay_n,
                "action_type": "remind_pay",
                "action_label": t("一键跟进"),
                "order_id": top.get("order_id"),
                "guest_id": top.get("guest_id"),
                "channel_hint": top.get("channel"),
                "deep_link": None,
            }
        )
        pid += 1

    collect_n = int(kpi.get("collect_prep_count") or 0)
    if collect_n:
        top = (ctx.get("collect_prep_top") or [{}])[0]
        actions.append(
            {
                "id": f"r{pid}",
                "module": "health",
                "priority": pid,
                "title": t("准备 {n} 单到店收款", n=collect_n),
                "body": t("近48h入住、到店付口径未结清共 {n} 单，属正常待收，非欠费。", n=collect_n),
                "suggestion": t("写入前台交接：到店办理时收款，勿对客人发催付短信。"),
                "confidence": "high",
                "confidence_note": t("散客/私域等到店付渠道，未付属预期"),
                "sample_size": collect_n,
                "action_type": "prep_collect",
                "action_label": t("到店收款"),
                "order_id": top.get("order_id"),
                "guest_id": top.get("guest_id"),
                "channel_hint": top.get("channel"),
                "deep_link": None,
            }
        )
        pid += 1

    od_n = int(kpi.get("overdue_count") or 0)
    if od_n:
        top = (ctx.get("overdue_top") or [{}])[0]
        actions.append(
            {
                "id": f"r{pid}",
                "module": "health",
                "priority": pid,
                "title": t("核查 {n} 单逾期未办", n=od_n),
                "body": t("入住日已过仍为待入住/已确认共 {n} 单，需人工确认是否到店。", n=od_n),
                "suggestion": t("联系客人确认行程；确认未到则标记 No-show，避免库存虚占。"),
                "confidence": "high",
                "confidence_note": t("入住日与状态均来自订单主数据"),
                "sample_size": od_n,
                "action_type": "confirm_noshow",
                "action_label": t("去核查"),
                "order_id": top.get("order_id"),
                "guest_id": top.get("guest_id"),
                "channel_hint": None,
                "deep_link": f"/orders/{top.get('order_id')}" if top.get("order_id") else "/orders",
            }
        )
        pid += 1

    chans = ctx.get("channel_quality") or []
    risky = next((c for c in chans if c.get("bookings", 0) >= 5 and c.get("cancel_rate_pct", 0) >= 20), None)
    if risky:
        actions.append(
            {
                "id": f"r{pid}",
                "module": "channel",
                "priority": pid,
                "title": t("{channel} 取消率偏高", channel=risky["channel"]),
                "body": t(
                    "近30日 {n} 单，取消/未到店率 {rate}%，ADR≈¥{adr}。",
                    n=risky["bookings"],
                    rate=risky["cancel_rate_pct"],
                    adr=risky["adr"],
                ),
                "suggestion": t("评估提前入住窗口改为预付不可退，或压缩该渠道配额。"),
                "confidence": "medium",
                "confidence_note": t("渠道历史推断，样本 {n} 单", n=risky["bookings"]),
                "sample_size": risky["bookings"],
                "action_type": "open_channel_policy",
                "action_label": t("策略任务"),
                "order_id": None,
                "guest_id": None,
                "channel_hint": risky["channel"],
                "deep_link": "/analytics/channel-insight/omni",
            }
        )
        pid += 1

    elastic = sorted(
        [c for c in chans if c.get("bookings", 0) >= 5],
        key=lambda x: (x.get("cancel_rate_pct", 99), -x.get("bookings", 0)),
    )
    if elastic and elastic[0].get("cancel_rate_pct", 99) <= 12:
        good = elastic[0]
        actions.append(
            {
                "id": f"r{pid}",
                "module": "channel",
                "priority": pid,
                "title": t("{channel} 可试探提价", channel=good["channel"]),
                "body": t(
                    "取消率 {rate}% · {n} 单 · ADR¥{adr}，相对稳健。",
                    rate=good["cancel_rate_pct"],
                    n=good["bookings"],
                    adr=good["adr"],
                ),
                "suggestion": t("周末房型可试探 +5%～8% 提价，观察转化与取消联动。"),
                "confidence": "medium",
                "confidence_note": t("相对取消率排序的启发式，非需求弹性计量模型"),
                "sample_size": good["bookings"],
                "action_type": "open_pricing",
                "action_label": t("价格助手"),
                "order_id": None,
                "guest_id": None,
                "channel_hint": good["channel"],
                "deep_link": "/pricing",
            }
        )
        pid += 1

    xhs_roi = kpi.get("xhs_roi")
    attr_n = int(kpi.get("attribution_rows") or 0)
    if xhs_roi and float(xhs_roi) >= 3:
        conf = "medium" if attr_n >= 20 else "low"
        actions.append(
            {
                "id": f"r{pid}",
                "module": "attribution",
                "priority": pid,
                "title": t("小红书 ROI {roi}x，评估加投", roi=xhs_roi),
                "body": t(
                    "活动表 ROI={roi}；归因触点行 {attr}；近30日小红书预订 {n} 单（环比 {delta}%）。",
                    roi=xhs_roi,
                    attr=attr_n,
                    n=kpi.get("xhs_bookings_30d"),
                    delta=kpi.get("xhs_delta_pct"),
                ),
                "suggestion": t("若归因样本充足，可小步加预算；否则先补齐多触点数据再决策。"),
                "confidence": conf,
                "confidence_note": t("依赖 campaigns/attribution 完备度，ROAS 易偏差")
                if conf == "low"
                else t("有活动 ROI 与一定归因样本，仍建议复核花费口径"),
                "sample_size": attr_n,
                "action_type": "open_acquisition",
                "action_label": t("营销任务"),
                "order_id": None,
                "guest_id": None,
                "channel_hint": t("小红书"),
                "deep_link": "/acquisition",
            }
        )
        pid += 1

    if not actions:
        actions.append(
            {
                "id": "r0",
                "module": "health",
                "priority": 1,
                "title": t("窗口内风险可控"),
                "body": t(
                    "近窗预订 {win} 单；预付跟进 {pay}；到店收款 {collect}；逾期 {od}。",
                    win=kpi.get("win_bookings"),
                    pay=pay_n,
                    collect=collect_n,
                    od=od_n,
                ),
                "suggestion": t("维持晨检：预付未到账跟进核对，到店付只做收款准备，逾期核查未到店。"),
                "confidence": "high",
                "confidence_note": t("直接聚合订单主数据"),
                "sample_size": int(kpi.get("win_bookings") or 0),
                "action_type": "create_task",
                "action_label": t("生成巡检"),
                "order_id": None,
                "guest_id": None,
                "channel_hint": None,
                "deep_link": "/analytics",
            }
        )

    conf = "high" if pay_n or collect_n or od_n else "medium"
    return {
        "briefing": {
            "headline": t("今日经营行动焦点"),
            "summary": t(
                "预付跟进 {pay} 单 · 到店收款准备 {collect} 单 · 逾期未办 {od}；"
                "已取消 {cancelled} · 确认未到店 {noshow}；"
                "待到店 {awaiting}（不计流失）。",
                pay=pay_n,
                collect=collect_n,
                od=od_n,
                cancelled=kpi.get("cancelled"),
                noshow=kpi.get("confirmed_noshow"),
                awaiting=kpi.get("awaiting"),
            ),
            "confidence": conf,
            "confidence_note": t("规则引擎基于订单硬字段聚合；LLM 未启用或调用失败时使用本结果"),
        },
        "actions": actions[:6],
    }


def _normalize(result: dict, ctx: dict) -> dict:
    briefing = result.get("briefing") if isinstance(result.get("briefing"), dict) else {}
    actions_in = result.get("actions") if isinstance(result.get("actions"), list) else []
    actions = []
    for i, a in enumerate(actions_in[:8]):
        if not isinstance(a, dict):
            continue
        at = str(a.get("action_type") or "create_task")
        if at not in {
            "remind_pay",
            "prep_collect",
            "confirm_noshow",
            "create_task",
            "open_order",
            "open_pricing",
            "open_acquisition",
            "open_channel_policy",
        }:
            at = "create_task"
        conf = str(a.get("confidence") or "medium").lower()
        if conf not in ("high", "medium", "low"):
            conf = "medium"
        actions.append(
            {
                "id": str(a.get("id") or f"a{i + 1}"),
                "module": a.get("module") if a.get("module") in ("health", "channel", "attribution") else "health",
                "priority": int(a.get("priority") or i + 1),
                "title": _localize_text(str(a.get("title") or "经营建议"))[:40],
                "body": _localize_text(str(a.get("body") or ""))[:200],
                "suggestion": _localize_text(str(a.get("suggestion") or ""))[:200],
                "confidence": conf,
                "confidence_note": _localize_text(str(a.get("confidence_note") or ""))[:120],
                "sample_size": int(a.get("sample_size") or 0),
                "action_type": at,
                "action_label": _localize_text(str(a.get("action_label") or "执行"))[:10],
                "order_id": a.get("order_id"),
                "guest_id": a.get("guest_id"),
                "channel_hint": a.get("channel_hint"),
                "deep_link": a.get("deep_link"),
            }
        )
    actions.sort(key=lambda x: (x["priority"], -_conf_rank(x["confidence"])))
    if not actions:
        return {"briefing": {}, "actions": []}
    return {
        "briefing": {
            "headline": _localize_text(str(briefing.get("headline") or "今日经营行动"))[:40],
            "summary": _localize_text(str(briefing.get("summary") or ""))[:280],
            "confidence": briefing.get("confidence")
            if briefing.get("confidence") in ("high", "medium", "low")
            else "medium",
            "confidence_note": _localize_text(str(briefing.get("confidence_note") or ""))[:160],
        },
        "actions": actions,
    }


def generate_analytics_actions(db: Session, hotel_id: int) -> dict:
    ctx = build_analytics_context(db, hotel_id)
    cfg = load_llm_config(db)

    user_prompt = narrate_user_prompt_actions(json.dumps(ctx, ensure_ascii=False, default=str))
    excerpt = [
        {"title": a.get("title"), "suggestion": a.get("suggestion")}
        for a in (_rule_fallback(ctx).get("actions") or [])[:6]
    ]
    if excerpt:
        user_prompt += "\n【规则摘录·仅素材】须基于数据重写 JSON，禁止把摘录当最终建议原文。\n" + json.dumps(
            excerpt, ensure_ascii=False
        )

    try:
        if not cfg.get("enabled", True):
            return {
                "source": "unavailable",
                "actions": [],
                "briefing": {},
                "order_risks": ctx.get("order_risks") or [],
                "kpi": ctx.get("kpi"),
                "llm_error": t("大模型未启用"),
            }

        res = llm_chat(
            db,
            [{"role": "user", "content": user_prompt}],
            extra_system=analytics_system_prompt(ANALYTICS_SYSTEM),
        )
        parsed = _normalize(_extract_json(res.get("content") or ""), ctx)
        if not parsed.get("actions"):
            return {
                "source": "unavailable",
                "actions": [],
                "briefing": {},
                "order_risks": ctx.get("order_risks") or [],
                "kpi": ctx.get("kpi"),
                "llm_error": t("模型未返回可用建议"),
            }
        parsed["source"] = "llm"
        parsed.update(llm_identity(cfg, res))
        parsed["order_risks"] = ctx.get("order_risks") or []
        parsed["kpi"] = ctx.get("kpi")
        parsed["raw_preview"] = (res.get("content") or "")[:400]
        return parsed
    except HTTPException as e:
        return {
            "source": "unavailable",
            "actions": [],
            "briefing": {},
            "order_risks": ctx.get("order_risks") or [],
            "kpi": ctx.get("kpi"),
            "llm_error": str(e.detail) if hasattr(e, "detail") else str(e),
        }
    except Exception as e:
        return {
            "source": "unavailable",
            "actions": [],
            "briefing": {},
            "order_risks": ctx.get("order_risks") or [],
            "kpi": ctx.get("kpi"),
            "llm_error": str(e)[:200],
        }


def execute_analytics_action(
    db: Session,
    hotel_id: int,
    action: dict,
) -> dict:
    """一键闭环：优先写库（CRM 任务 / 标记未到店）；deep_link 仅可选。"""
    at = action.get("action_type") or "create_task"
    title = (action.get("title") or action.get("action_label") or "经营跟进").strip()
    suggestion = (action.get("suggestion") or action.get("body") or "").strip()
    order_id = action.get("order_id")
    guest_id = action.get("guest_id")
    order_no = (action.get("order_no") or "").strip()
    wrote_noshow = False

    order_row = None
    if order_id:
        order_row = db.get(Order, int(order_id))
        if order_row and order_row.hotel_id == hotel_id:
            if not guest_id:
                guest_id = order_row.guest_id
            if not order_no:
                order_no = order_row.order_no or ""
        else:
            order_row = None
            order_id = None

    # 真实写操作：逾期单标记未到店
    if at == "confirm_noshow" and order_row:
        from orders.pms_ops import mark_no_show

        mark_no_show(
            db,
            int(order_id),
            reason=str(action.get("reason") or suggestion or "AI 监测：逾期未办确认未到店"),
        )
        wrote_noshow = True
        if not title or title == "经营跟进":
            title = f"已标记未到店 · {order_no or order_id}"

    deep = action.get("deep_link")
    if at == "open_order" and order_id:
        deep = f"/orders/{order_id}"
    elif at == "open_pricing":
        deep = deep or "/pricing"
    elif at == "open_acquisition":
        deep = deep or "/acquisition"
    elif at == "open_channel_policy":
        deep = deep or "/analytics/channel-insight/omni"
    elif at == "confirm_noshow" and order_id:
        deep = f"/orders/{order_id}"
    elif at in ("remind_pay", "prep_collect", "create_task"):
        deep = deep or None

    if at == "prep_collect" and (not title or title == "经营跟进"):
        title = f"到店收款准备 · {order_no or order_id or '清单'}"

    task_type = {
        "remind_pay": "care",
        "prep_collect": "care",
        "confirm_noshow": "recall",
        "create_task": "recall",
        "open_channel_policy": "recall",
        "open_acquisition": "coupon",
        "open_pricing": "care",
        "open_order": "care",
    }.get(at, "recall")

    blob = json.dumps(
        {
            "source": "analytics_ai",
            "action_type": at,
            "order_id": order_id,
            "order_no": order_no or None,
            "channel_hint": action.get("channel_hint"),
            "suggestion": suggestion,
            "confidence": action.get("confidence"),
            "wrote_noshow": wrote_noshow,
        },
        ensure_ascii=False,
    )

    task = CrmTask(
        hotel_id=hotel_id,
        guest_id=int(guest_id) if guest_id else None,
        task_type=task_type,
        status="done" if wrote_noshow else "open",
        title=title[:200],
        payload_json=blob,
        done_at=datetime.utcnow() if wrote_noshow else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    msg = {
        "remind_pay": t("已写入预付跟进任务，可复制话术发送"),
        "prep_collect": t("已写入前台到店收款准备任务"),
        "confirm_noshow": (t("已标记未到店并写入跟进记录") if wrote_noshow else t("已生成逾期核查任务")),
        "create_task": t("已写入运营任务列表"),
        "open_pricing": t("已写入定价复核任务"),
        "open_acquisition": t("已生成营销跟进任务"),
        "open_channel_policy": t("已写入渠道政策评估任务"),
        "open_order": t("已生成订单跟进任务"),
    }.get(at, t("已创建跟进任务"))

    draft = suggestion
    oid = order_no or order_id or "—"
    if at == "remind_pay":
        draft = t(
            "【预付提醒】您好，您预订的入住日临近，订单预付款项尚未确认到账。"
            "请尽快完成支付，以便我们为您保留房态。"
            "订单号：{oid}。",
            oid=oid,
        )
    elif at == "prep_collect":
        draft = t(
            "【前台交接·到店收款】订单 {oid} 为到店付口径，未付属正常。请在办理入住时收款，勿对客人发送催付短信。",
            oid=oid,
        )

    return {
        "ok": True,
        "message": msg,
        "task_id": task.id,
        "deep_link": deep,
        "wrote_noshow": wrote_noshow,
        "draft_message": draft,
    }


CHANNEL_NARRATIVE_SYSTEM = """你是「AI-Native PMS」的渠道收益参谋。
根据用户给出的渠道事实 JSON，分别列出「事实」与「建议」。

## 要求
1. 数字必须与 JSON 一致，禁止编造渠道名或样本外结论。
2. facts：2～4 条，只陈述客观数据（量、增速、取消率、ADR、转化等），不要写动作建议。
3. suggestions：1～3 条，每条一个可执行动作（如核查价差、调整退改、加投试探、控价等）。
4. 区分「已确认流失（取消/确认未到店）」与「待到店/到店付」——后者不是流失。
5. 文案全部中文；条目内可用 <strong> 强调关键数字或渠道名，不要用其他 HTML。
6. 输出单一 JSON，不要 Markdown 代码围栏，不要额外解释：
{"facts":["..."],"suggestions":["..."],"confidence":"high|medium|low","confidence_note":"..."}
"""


def _format_channel_narrative_html(facts: list, suggestions: list) -> str:
    """统一排版：事实 / 建议 两栏列表。"""
    facts_zh = [_localize_text(str(x).strip()) for x in (facts or []) if str(x).strip()]
    sugs_zh = [_localize_text(str(x).strip()) for x in (suggestions or []) if str(x).strip()]
    return format_insight_html(t("事实"), facts_zh, t("建议"), sugs_zh)


def _split_rule_insight_html(rule_html: str) -> tuple[list[str], list[str]]:
    """规则模板段落 → 事实/建议粗分（含「建议」的进建议栏）。"""
    import re

    text = (rule_html or "").strip()
    if not text:
        return [], []
    chunks = [c.strip() for c in re.split(r"(?<=[。！？])\s*", text) if c.strip()]
    facts, suggestions = [], []
    for c in chunks:
        plain = re.sub(r"<[^>]+>", "", c)
        if any(k in plain for k in ("建议", "宜", "可考虑", "应")):
            suggestions.append(c)
        else:
            facts.append(c)
    if not suggestions and facts:
        # 末条若偏行动，仍保留在事实；补一条通用建议
        suggestions.append(t("结合下方排行与质量分档，优先复核高取消渠道的价差与退改政策。"))
    return facts, suggestions


def narrate_channel_insight(db: Session, facts: dict) -> dict:
    """手动触发：LLM 解读渠道事实；失败则标明不可用，不把规则稿当 AI。"""
    cfg = load_llm_config(db)
    rule_html = str(facts.get("rule_template_html") or "").strip()
    fb_facts, fb_sugs = _split_rule_insight_html(rule_html)
    fb_html = _format_channel_narrative_html(fb_facts, fb_sugs) or (
        rule_html or t("暂无足够渠道样本生成洞察，请确认窗口内有入住日订单。")
    )
    fallback = {
        "narrative_html": "",
        "facts": fb_facts,
        "suggestions": [],
        "confidence": "",
        "confidence_note": "",
        "source": "unavailable",
        "actions": [],
        "llm_error": t("未能调用大模型"),
    }

    if not cfg.get("enabled", True):
        return fallback

    user_prompt = narrate_user_prompt_channel(json.dumps(facts, ensure_ascii=False, default=str))
    try:
        res = llm_chat(
            db,
            [{"role": "user", "content": user_prompt}],
            extra_system=channel_narrative_system(CHANNEL_NARRATIVE_SYSTEM),
        )
        parsed = _extract_json(res.get("content") or "")
        fact_list = parsed.get("facts") if isinstance(parsed.get("facts"), list) else []
        sug_list = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []
        # 兼容旧模型只回 narrative_html
        html = _format_channel_narrative_html(fact_list, sug_list)
        if not html:
            raw = _localize_text(str(parsed.get("narrative_html") or "")).strip()
            if raw:
                f2, s2 = _split_rule_insight_html(raw)
                html = _format_channel_narrative_html(f2, s2) or raw
                fact_list, sug_list = f2 or fact_list, s2 or sug_list
        if not html:
            raise ValueError("洞察内容为空")
        conf = str(parsed.get("confidence") or "medium").lower()
        if conf not in ("high", "medium", "low"):
            conf = "medium"
        return {
            "narrative_html": html[:2400],
            "facts": [_localize_text(str(x))[:200] for x in fact_list[:6]],
            "suggestions": [_localize_text(str(x))[:200] for x in sug_list[:6]],
            "confidence": conf,
            "confidence_note": _localize_text(str(parsed.get("confidence_note") or ""))[:160],
            "source": "llm",
            "actions": [
                {
                    "action_type": "open_path",
                    "action_label": t("查看渠道归因"),
                    "path": "/analytics/marketing-attribution/path",
                }
            ],
            **llm_identity(cfg, res),
        }
    except Exception as e:
        fallback["source"] = "unavailable"
        fallback["narrative_html"] = ""
        fallback["suggestions"] = []
        fallback["actions"] = []
        fallback["llm_error"] = str(e)[:200]
        return fallback


ATTR_NARRATIVE_SYSTEM = """你是「AI-Native PMS」的营销归因参谋。
根据用户给出的订单归因事实 JSON，分别列出「事实」与「建议」。

## 要求
1. 数字必须与 JSON 一致，禁止编造路径或样本外结论。
2. facts：2～4 条，只陈述客观数据（归因单量、单触点/跨渠道占比、Top 路径、首触分布等）。
3. suggestions：1～3 条，每条一个可执行动作（如加强跨渠道承接、加投 Top 种草渠道、核查同渠道转化断点等）。
4. 口径说明：归因首触 → 订单成单渠道；不要假装有完整中间浏览链路。
5. 文案全部中文；条目内可用 <strong> 强调关键数字或渠道名，不要用其他 HTML。
6. 输出单一 JSON，不要 Markdown 代码围栏，不要额外解释：
{"facts":["..."],"suggestions":["..."],"confidence":"high|medium|low","confidence_note":"..."}
"""


def narrate_attribution_insight(db: Session, facts: dict) -> dict:
    """手动触发：LLM 解读归因事实；失败则标明不可用，不把规则稿当 AI。"""
    cfg = load_llm_config(db)
    rule_html = str(facts.get("rule_template_html") or "").strip()
    fb_facts, fb_sugs = _split_rule_insight_html(rule_html)
    if not fb_sugs and fb_facts:
        fb_sugs = [t("对照下方路径与旅程，优先复盘跨渠道承接断点与 Top 种草渠道投放。")]
    fb_html = _format_channel_narrative_html(fb_facts, fb_sugs) or (rule_html or t("暂无足够归因样本生成洞察。"))
    actions = [
        {
            "action_type": "open_path",
            "action_label": t("查看全渠道订单洞察"),
            "path": "/c5-frontdesk/ai-new",
        },
        {
            "action_type": "open_path",
            "action_label": t("打开获客投放"),
            "path": "/acquisition",
        },
    ]
    fallback = {
        "narrative_html": "",
        "facts": fb_facts,
        "suggestions": [],
        "confidence": "",
        "confidence_note": "",
        "source": "unavailable",
        "actions": [],
        "llm_error": t("未能调用大模型"),
    }

    if not cfg.get("enabled", True):
        return fallback

    user_prompt = narrate_user_prompt_attr(json.dumps(facts, ensure_ascii=False, default=str))
    try:
        res = llm_chat(
            db,
            [{"role": "user", "content": user_prompt}],
            extra_system=attr_narrative_system(ATTR_NARRATIVE_SYSTEM),
        )
        parsed = _extract_json(res.get("content") or "")
        fact_list = parsed.get("facts") if isinstance(parsed.get("facts"), list) else []
        sug_list = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []
        html = _format_channel_narrative_html(fact_list, sug_list)
        if not html:
            raw = _localize_text(str(parsed.get("narrative_html") or "")).strip()
            if raw:
                f2, s2 = _split_rule_insight_html(raw)
                html = _format_channel_narrative_html(f2, s2) or raw
                fact_list, sug_list = f2 or fact_list, s2 or sug_list
        if not html:
            raise ValueError("洞察内容为空")
        conf = str(parsed.get("confidence") or "medium").lower()
        if conf not in ("high", "medium", "low"):
            conf = "medium"
        return {
            "narrative_html": html[:2400],
            "facts": [_localize_text(str(x))[:200] for x in fact_list[:6]],
            "suggestions": [_localize_text(str(x))[:200] for x in sug_list[:6]],
            "confidence": conf,
            "confidence_note": _localize_text(str(parsed.get("confidence_note") or ""))[:160],
            "source": "llm",
            "actions": actions,
            **llm_identity(cfg, res),
        }
    except Exception as e:
        fallback["source"] = "unavailable"
        fallback["narrative_html"] = ""
        fallback["suggestions"] = []
        fallback["actions"] = []
        fallback["llm_error"] = str(e)[:200]
        return fallback
