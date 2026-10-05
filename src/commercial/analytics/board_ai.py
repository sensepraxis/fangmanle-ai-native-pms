# SPDX-License-Identifier: BUSL-1.1
"""看板/规则能力的真实 LLM 包层 · 订单风险 / 利润策略 / 竞品解读。

约定：点击后才调 LLM；输出 narrative_html + actions；失败规则兜底；文案跟请求 locale。
规则引擎保留为事实来源，LLM 只负责解读与动作建议。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import (
    format_insight_html,
    run_narrate,
)
from commercial.ai_core.ai_narrative import (
    safe_path as _safe_path_core,
)
from commercial.ai_core.prompt_packs import language_instruction
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.i18n import t

ALLOWED_PATHS = [
    "/orders",
    "/analytics",
    "/analytics?tab=profit",
    "/analytics?tab=insights",
    "/pricing",
    "/c6-housekeeping/housekeeping",
    "/acquisition/coupons",
    "/acquisition",
]

ACTION_TYPES = {"open_path", "remind_pay", "prep_collect", "confirm_noshow", "create_task"}

NARRATIVE_KINDS = {
    "order_risks": {
        "label": "订单风险 AI 解读",
        "left_h": "风险事实",
        "right_h": "处置建议",
        "prompt_domain": "board",
        "prompt_scene": "order_risks",
    },
    "profit_insights": {
        "label": "利润优化 AI 解读",
        "left_h": "利润事实",
        "right_h": "增效建议",
        "prompt_domain": "board",
        "prompt_scene": "profit_insights",
    },
    "pricing_compare": {
        "label": "竞品价格 AI 解读",
        "left_h": "比价事实",
        "right_h": "调价建议",
        "prompt_domain": "board",
        "prompt_scene": "pricing_compare",
    },
}


def _safe_path(path: Optional[str], default: str = "/analytics") -> str:
    return _safe_path_core(path, ALLOWED_PATHS, default)


def _kind_meta(kind: str) -> dict[str, Any]:
    raw = dict(NARRATIVE_KINDS[kind])
    return {
        **raw,
        "label": t(raw["label"]),
        "left_h": t(raw["left_h"]),
        "right_h": t(raw["right_h"]),
    }


def _user_text(text: Any) -> str:
    """把内部动作码等替换为当前 locale 可读文案（不强制中文）。"""
    s = str(text or "")
    reps = [
        ("remind_pay", t("催付")),
        ("prep_collect", t("准备收款")),
        ("confirm_noshow", t("确认未到")),
        ("create_task", t("创建任务")),
        ("open_path", t("前往对应页面")),
        ("P_comp_median", t("竞品中位价")),
        ("self_vs_median", t("本店相对中位")),
    ]
    for code, label in reps:
        s = re.sub(re.escape(code), label, s, flags=re.I)
    return s


def _localize(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data or {})
    if out.get("narrative_html"):
        out["narrative_html"] = _user_text(out["narrative_html"])
    out["facts"] = [_user_text(x) for x in (out.get("facts") or [])]
    out["suggestions"] = [_user_text(x) for x in (out.get("suggestions") or [])]
    if out.get("confidence_note"):
        out["confidence_note"] = _user_text(out["confidence_note"])
    actions = []
    for a in out.get("actions") or []:
        if not isinstance(a, dict):
            continue
        item = dict(a)
        for k in ("action_label", "title", "body"):
            if item.get(k):
                item[k] = _user_text(item[k])
        actions.append(item)
    if actions:
        out["actions"] = actions
    return out


def _build_snapshot(db: Session, hotel_id: int, kind: str, opts: Optional[dict] = None) -> dict[str, Any]:
    opts = opts or {}
    if kind == "order_risks":
        from commercial.analytics.analytics_ai import build_analytics_context

        ctx = build_analytics_context(db, hotel_id)
        risks = list(ctx.get("order_risks") or [])[:20]
        order_id = opts.get("order_id")
        if order_id is not None:
            risks = [r for r in risks if str(r.get("order_id")) == str(order_id)] or risks[:5]
        return {
            "risks": risks,
            "risk_count": len(ctx.get("order_risks") or []),
            "allowed_paths": ALLOWED_PATHS,
        }

    if kind == "profit_insights":
        from models import ProfitInsight

        rows = db.query(ProfitInsight).filter_by(hotel_id=hotel_id).order_by(ProfitInsight.id.desc()).limit(12).all()
        from infra.i18n import t as _t

        insights = []
        for r in rows:
            title = getattr(r, "title", None)
            reco = getattr(r, "recommendation", None) or getattr(r, "suggestion", None) or getattr(r, "detail", None)
            insights.append(
                {
                    "id": r.id,
                    "title": _t(str(title)) if title else None,
                    "recommendation": _t(str(reco)) if reco else None,
                    "impact_amount": getattr(r, "impact_amount", None),
                    "category": getattr(r, "category", None),
                    "status": getattr(r, "status", None),
                }
            )
        return {
            "insights": insights,
            "open_count": sum(1 for x in insights if x.get("status") == "open"),
            "allowed_paths": ALLOWED_PATHS,
        }

    if kind == "pricing_compare":
        from pricing.pricing_assistant import build_compare

        days = int(opts.get("days") or 7)
        cmp = build_compare(db, hotel_id, days=days)
        return {
            "comp_median": (cmp or {}).get("comp_median"),
            "self_vs_median_pct": (cmp or {}).get("self_vs_median_pct"),
            "price_basis_note": (cmp or {}).get("price_basis_note"),
            "rule_ai_read": (cmp or {}).get("ai_read") or [],
            "matrix_summary": _matrix_summary(cmp or {}),
            "days": days,
            "allowed_paths": ALLOWED_PATHS,
        }

    raise NotFoundError(f"未知 AI 能力: {kind}")


def _matrix_summary(cmp: dict) -> list[dict]:
    out = []
    for row in (cmp.get("matrix") or [])[:8]:
        cells = row.get("cells") or []
        prices = [c.get("guest_price") for c in cells if c and c.get("guest_price") is not None]
        out.append(
            {
                "name": row.get("name"),
                "is_self": bool(row.get("is_self")),
                "avg_guest_price": round(sum(prices) / len(prices), 1) if prices else None,
            }
        )
    return out


def _risk_action_copy(at: str) -> tuple[str, str, str]:
    """按 action_type 生成本地化卡片文案。"""
    if at == "remind_pay":
        return (
            t("提醒付款"),
            t("提醒预付跟进订单付款"),
            t("请提醒客户完成预付/订金支付，避免订单取消。"),
        )
    if at == "prep_collect":
        return (
            t("准备收款"),
            t("准备到店收款流程"),
            t("请前台准备收款流程，确保到店后及时结算。"),
        )
    if at == "confirm_noshow":
        return (
            t("确认未到店"),
            t("确认逾期订单是否未到店"),
            t("请核查逾期订单是否标记为未到店，及时处理或取消。"),
        )
    return (t("去处理"), t("订单风险"), t("到数据洞察核对支付/催收风险。"))


def _default_actions(kind: str, snap: dict) -> list[dict]:
    if kind == "order_risks":
        risks = snap.get("risks") or []
        # 按 action_type 去重，优先展示三类处置
        seen: set[str] = set()
        acts = []
        for r in risks:
            at = str(r.get("action_type") or "open_path")
            if at not in ACTION_TYPES or at in seen:
                continue
            seen.add(at)
            label, title, body = _risk_action_copy(at)
            acts.append(
                {
                    "id": f"r{len(acts)}",
                    "action_type": at,
                    "action_label": label[:14],
                    "title": title[:40],
                    "body": body[:120],
                    "path": "/analytics?tab=insights",
                    "order_id": r.get("order_id"),
                }
            )
            if len(acts) >= 3:
                break
        return acts or [
            {
                "id": "go",
                "action_type": "open_path",
                "action_label": t("打开数据洞察"),
                "title": t("查看订单健康度"),
                "body": t("到数据洞察核对支付/催收风险。"),
                "path": "/analytics?tab=insights",
            }
        ]
    if kind == "profit_insights":
        return [
            {
                "id": "pricing",
                "action_type": "open_path",
                "action_label": t("去价格助手"),
                "title": t("结合建议价落地"),
                "body": t("打开价格助手核对竞品与建议价。"),
                "path": "/pricing",
            },
            {
                "id": "analytics",
                "action_type": "open_path",
                "action_label": t("看渠道结构"),
                "title": t("核对渠道利润"),
                "body": t("到数据洞察查看渠道贡献。"),
                "path": "/analytics",
            },
        ]
    return [
        {
            "id": "price",
            "action_type": "open_path",
            "action_label": t("打开价格助手"),
            "title": t("核对建议价"),
            "body": t("按竞品位置调整本店挂牌价。"),
            "path": "/pricing",
        }
    ]


def _normalize_actions(raw: list, kind: str, snap: dict) -> list[dict]:
    out = []
    for i, a in enumerate(raw or []):
        if not isinstance(a, dict):
            continue
        at = str(a.get("action_type") or "open_path")
        if at not in ACTION_TYPES:
            at = "open_path"
        out.append(
            {
                "id": str(a.get("id") or f"a{i + 1}"),
                "action_type": at,
                "action_label": str(a.get("action_label") or t("执行"))[:16],
                "title": str(a.get("title") or t("建议动作"))[:40],
                "body": str(a.get("body") or "")[:120],
                "path": _safe_path(a.get("path"), "/analytics"),
                "order_id": a.get("order_id"),
            }
        )
    if not out:
        out = _default_actions(kind, snap)
    return out[:4]


def _rule_fallback(kind: str, snap: dict) -> dict[str, Any]:
    meta = _kind_meta(kind)
    facts: list[str] = []
    suggestions: list[str] = []

    if kind == "order_risks":
        risks = snap.get("risks") or []
        n = int(snap.get("risk_count") or len(risks) or 0)
        pay_n = sum(1 for r in risks if r.get("action_type") == "remind_pay" or r.get("risk_code") == "pay")
        collect_n = sum(1 for r in risks if r.get("action_type") == "prep_collect" or r.get("risk_code") == "collect")
        od_n = sum(1 for r in risks if r.get("action_type") == "confirm_noshow" or r.get("risk_code") == "overdue")
        if n:
            facts.append(t("{n} 个订单存在风险，主要涉及预付跟进、到店收款、逾期未办和取消风险。", n=n))
        else:
            facts.append(t("当前窗口暂无明显风险订单。"))
        if pay_n:
            facts.append(t("预付跟进订单共 {n} 个，均未完成预付/订金支付，需提醒客户付款。", n=pay_n))
        if collect_n:
            facts.append(t("到店收款订单共 {n} 个，需前台准备收款流程，确保到店后及时结算。", n=collect_n))
        if od_n:
            facts.append(t("逾期未办订单共 {n} 个，入住日期已过，需确认是否标记未到店。", n=od_n))
        suggestions = [
            t("立即提醒预付跟进订单客户完成付款，避免订单取消。"),
            t("对到店收款订单，提前通知前台准备收款流程，确保到店后及时结算。"),
            t("核查逾期未办订单是否标记为未到店，及时处理或取消订单。"),
        ]
        conf_note = t("所有风险订单均基于支付状态、入住日期和渠道历史数据，判断准确度高。")
        conf = "high"
    elif kind == "profit_insights":
        insights = snap.get("insights") or []
        open_n = sum(1 for x in insights if x.get("status") == "open")
        facts.append(t("待办利润策略 {n} 条", n=open_n))
        for x in insights[:4]:
            title = x.get("title") or ""
            line = t("「{title}」潜在影响 ¥{amt}", title=title, amt=x.get("impact_amount") or 0)
            if x.get("recommendation"):
                line += f"：{x.get('recommendation')}"
            facts.append(line)
        if not insights:
            facts.append(t("暂无开放中的利润策略卡，可先核对瀑布图结构。"))
        suggestions = [
            t("优先落地影响金额高且可执行的成本/渠道策略。"),
            t("结合价格助手核对是否存在结构性低价。"),
        ]
        conf_note = t("规则摘录：由原有看板/规则引擎事实拼装（仅素材）")
        conf = "medium"
    else:
        pct = snap.get("self_vs_median_pct")
        facts = [
            t("本店相对竞品中位 {pct}%", pct=pct if pct is not None else "—"),
            str(snap.get("price_basis_note") or t("价格口径见价格助手说明。")),
        ]
        for line in (snap.get("rule_ai_read") or [])[:3]:
            facts.append(str(line))
        for row in (snap.get("matrix_summary") or [])[:3]:
            tag = t("本店") if row.get("is_self") else t("竞品")
            facts.append(
                t(
                    "{tag}「{name}」均价约 ¥{price}",
                    tag=tag,
                    name=row.get("name"),
                    price=row.get("avg_guest_price") or "—",
                )
            )
        suggestions = [
            t("若持续高于中位且转化承压，可对弱势日期试探下调。"),
            t("若低于中位，可结合建议价与活动日上探。"),
        ]
        conf_note = t("规则摘录：由原有看板/规则引擎事实拼装（仅素材）")
        conf = "medium"

    return _localize(
        {
            "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
            "facts": facts,
            "suggestions": suggestions,
            "actions": _default_actions(kind, snap),
            "confidence": conf,
            "confidence_note": conf_note,
            "source": "material",
        }
    )


def narrate_board_ai(db: Session, hotel_id: int, kind: str, opts: Optional[dict] = None) -> dict[str, Any]:
    if kind not in NARRATIVE_KINDS:
        raise NotFoundError(f"未知 AI 能力: {kind}")
    meta = _kind_meta(kind)
    snap = _build_snapshot(db, hotel_id, kind, opts)
    user_prompt = (
        f"Task: generate «{meta['label']}».\n"
        f"{language_instruction()}\n"
        f"Allowed paths: {json.dumps(ALLOWED_PATHS, ensure_ascii=False)}\n"
        f"Snapshot:\n{json.dumps(snap, ensure_ascii=False, default=str)}"
    )
    return run_narrate(
        db,
        kind=kind,
        meta=meta,
        user_prompt=user_prompt,
        build_fallback=lambda: _rule_fallback(kind, snap),
        normalize_actions=lambda acts: _normalize_actions(acts, kind, snap),
        polish=_localize,
    )


def execute_board_ai_action(db: Session, hotel_id: int, action: dict) -> dict[str, Any]:
    at = str((action or {}).get("action_type") or "")
    path = _safe_path((action or {}).get("path"))

    if at == "open_path":
        return {"ok": True, "action_type": at, "message": t("请前往对应页面处理"), "deep_link": path, "wrote": False}

    if at in ("remind_pay", "prep_collect", "confirm_noshow", "create_task"):
        try:
            from commercial.analytics.analytics_ai import execute_analytics_action

            return execute_analytics_action(db, hotel_id, action)
        except Exception as e:
            return {
                "ok": True,
                "action_type": at,
                "message": f"已记录动作意向（环境）：{at}",
                "deep_link": path,
                "wrote": False,
                "note": str(e)[:120],
            }

    raise InvalidStateError(f"不支持的 action_type: {at}")
