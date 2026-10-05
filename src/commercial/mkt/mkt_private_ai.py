# SPDX-License-Identifier: BUSL-1.1
"""私域总览 AI · 触发式格式化解读（对齐渠道解读：不展示 JSON，输出文案 + 可写操作）。

约定（全站 AI 应遵循）：
1. 用户点击后才调用 LLM（本地 Ollama / 系统可替换配置）
2. 前端只展示格式化 narrative_html + actions，永不展示模型原始 JSON
3. actions 尽量提供可写操作（create_*）或 open_path 跳转
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import format_insight_html, run_narrate
from commercial.ai_core.ai_narrative import safe_path as _safe_path_core
from commercial.mkt.mkt_ai_locale import kind_meta, narrate_user_prompt
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.i18n import t as _t
from mkt.mkt_private_overview import private_overview

ALLOWED_PATHS = [
    "/acquisition",
    "/acquisition/landing-pages",
    "/acquisition/coupons",
    "/acquisition/coupons?tab=grant&sub=rules",
    "/acquisition/coupons?tab=grant&sub=records",
    "/acquisition/coupons?tab=redeem",
    "/acquisition/members",
    "/acquisition/points",
    "/a-ai-core/wecom-integration",
]

ACTION_TYPES = {
    "create_recall_pack",
    "create_recall_coupon",
    "create_recall_rule",
    "open_path",
}

# 兼容旧名
DIAGNOSIS_ACTION_TYPES = ACTION_TYPES
KIND_META = {}  # stream 已弃用；保留空表避免旧 import 崩

NARRATIVE_KINDS = {
    "diagnosis": {
        "label": "健康度诊断",
        "left_h": "事实",
        "right_h": "建议",
        "btn": "开始诊断",
        "prompt_domain": "mkt",
        "prompt_scene": "diagnosis",
    },
    "week_plan": {
        "label": "本周养客作战计划",
        "left_h": "本周重点",
        "right_h": "执行要点",
        "btn": "生成本周计划",
        "prompt_domain": "mkt",
        "prompt_scene": "week_plan",
    },
    "radar": {
        "label": "异常与机会雷达",
        "left_h": "异常信号",
        "right_h": "机会信号",
        "btn": "扫描雷达",
        "prompt_domain": "mkt",
        "prompt_scene": "radar",
    },
}


def _safe_path(path: Optional[str], default: str = "/acquisition") -> str:
    p = str(path or "").strip()
    if p in ALLOWED_PATHS:
        return p
    for allowed in ALLOWED_PATHS:
        if p.startswith(allowed.split("?")[0]):
            return p if "?" in p or p == allowed.split("?")[0] else allowed
    return default


def _facts_from_overview(overview: dict[str, Any]) -> dict[str, Any]:
    health = overview.get("health") or {}
    dims = health.get("dims") or {}
    kpis = {k.get("key"): k for k in (overview.get("hero_kpis") or []) if isinstance(k, dict)}
    flow = overview.get("flow") or []
    return {
        "health_score": health.get("score"),
        "health_level": health.get("level"),
        "dims": dims,
        "dormant": health.get("dormant"),
        "private_customers": (kpis.get("private_cust") or {}).get("value"),
        "link_rate": (kpis.get("link_rate") or {}).get("value"),
        "month_active": (kpis.get("month_active") or {}).get("value"),
        "mkt_revenue": (kpis.get("mkt_revenue") or {}).get("value"),
        "kpi_notes": {
            k: {"value": v.get("value"), "unit": v.get("unit"), "delta_label": v.get("delta_label")}
            for k, v in kpis.items()
        },
        "flow": [{"name": f.get("name"), "status": f.get("status"), "badge": f.get("badge")} for f in flow],
        "funnel": overview.get("funnel"),
        "wecom": overview.get("wecom"),
        "board": overview.get("board"),
        "kpi": overview.get("kpi"),
    }


_RECALL_COUPON_NAME_ZH = "沉默客回归券"
_RECALL_RULE_NAME_ZH = "AI·沉默客回归自动发券"
_RECALL_RULE_NAME_EN = "AI · dormant recall auto-grant"
_RECALL_RULE_DESC_ZH = "由私域 AI 一键创建：沉默 30 天自动发回归券"
_RECALL_SIGNAL_KW_ZH = ("沉默", "核销", "自动", "召回", "未核销")
_RECALL_SIGNAL_KW_EN = ("dormant", "recall", "redeem", "auto", "unused")


def _text_has_recall_signal(text: str) -> bool:
    s = str(text or "")
    if any(k in s for k in _RECALL_SIGNAL_KW_ZH):
        return True
    low = s.lower()
    return any(k in low for k in _RECALL_SIGNAL_KW_EN)


def _is_recall_coupon_name(raw: str) -> bool:
    s = str(raw or "")
    if "回归" in s:
        return True
    low = s.lower()
    if any(k in low for k in ("recall", "dormant")):
        return True
    loc = _t(_RECALL_COUPON_NAME_ZH)
    return bool(loc and loc in s)


def _recall_rule_name_variants() -> set[str]:
    return {_RECALL_RULE_NAME_ZH, _RECALL_RULE_NAME_EN, _t(_RECALL_RULE_NAME_ZH)}


def _default_recall_action() -> dict:
    return {
        "id": "recall-pack",
        "action_type": "create_recall_pack",
        "action_label": _t("一键建回归养客"),
        "title": _t("创建回归券并启用沉默规则"),
        "body": _t("写入回归券批次，并启用「沉默 N 天」自动发券规则。"),
        "path": "/acquisition/coupons?tab=grant&sub=rules",
    }


def _normalize_actions(raw_actions: list, overview: dict[str, Any]) -> list[dict]:
    out: list[dict] = []
    for i, a in enumerate(raw_actions or []):
        if not isinstance(a, dict):
            continue
        at = str(a.get("action_type") or "open_path")
        if at not in ACTION_TYPES:
            at = "open_path"
        out.append(
            {
                "id": str(a.get("id") or f"a{i + 1}"),
                "action_type": at,
                "action_label": _t(str(a.get("action_label") or "执行"))[:48],
                "title": _t(str(a.get("title") or "建议动作"))[:48],
                "body": _t(str(a.get("body") or ""))[:120] if a.get("body") else "",
                "path": _safe_path(a.get("path"), "/acquisition/coupons?tab=grant&sub=rules"),
            }
        )
    if not out:
        return [_default_recall_action()]
    # 去重
    seen = set()
    uniq = []
    for a in out:
        key = (a["action_type"], a["path"], a["title"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:4]


def _rule_fallback(kind: str, overview: dict[str, Any]) -> dict[str, Any]:
    meta = kind_meta(NARRATIVE_KINDS, kind)
    health = overview.get("health") or {}
    dims = health.get("dims") or {}
    ai = overview.get("ai_ops") or {}
    kpi = overview.get("kpi") or {}

    if kind == "diagnosis":
        facts = [
            _t("私域健康度 <strong>{score}</strong> 分（{level}）").format(
                score=health.get("score") or "—",
                level=health.get("level") or "—",
            ),
            _t("四维：接入 {access} · 引流 {attract} · 活跃 {active} · 转化 {convert}").format(
                access=dims.get("access", dims.get("接入", "—")),
                attract=dims.get("attract", dims.get("引流", "—")),
                active=dims.get("active", dims.get("活跃", "—")),
                convert=dims.get("convert", dims.get("转化", "—")),
            ),
        ]
        if health.get("dormant"):
            facts.append(_t("近 30 天沉默客户约 <strong>{n}</strong> 人").format(n=health.get("dormant")))
        if kpi.get("redeem_rate") is not None:
            facts.append(
                _t("累计核销率 <strong>{rate}%</strong>（已发 {grants}）").format(
                    rate=kpi.get("redeem_rate"),
                    grants=kpi.get("grants") or 0,
                )
            )
        suggestions = []
        actions = []
        for d in (ai.get("diagnosis") or [])[:3]:
            problem = str(d.get("problem") or "").strip()
            cause = str(d.get("cause") or "").strip()
            if problem:
                suggestions.append(problem + (f"：{cause}" if cause else ""))
            path = _safe_path(d.get("path"))
            sev = str(d.get("severity") or "")
            if sev in ("bad", "warn") and _text_has_recall_signal(problem):
                actions.append(_default_recall_action())
                break
            if path != "/acquisition":
                actions.append(
                    {
                        "id": f"open-{len(actions) + 1}",
                        "action_type": "open_path",
                        "action_label": str(d.get("action") or _t("去处理"))[:48],
                        "title": problem if problem else _t("去对应页面"),
                        "body": cause or "",
                        "path": path,
                    }
                )
        if not suggestions:
            suggestions.append(_t("保持发券与核销节奏，定期巡检自动规则触发记录。"))
        if not actions:
            actions = [_default_recall_action()]
        return {
            "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
            "facts": facts,
            "suggestions": suggestions,
            "actions": actions[:4],
            "confidence": "medium",
            "confidence_note": _t("规则模板：由私域看板指标拼装"),
            "source": "material",
        }

    if kind == "week_plan":
        plans = list(ai.get("week_plan") or [])
        facts = []
        suggestions = []
        actions = []
        for p in plans[:5]:
            title = str(p.get("title") or "").strip() if p.get("title") else ""
            detail = str(p.get("detail") or "").strip() if p.get("detail") else ""
            tag = str(p.get("tag") or "").strip() if p.get("tag") else ""
            if title:
                line = f"<strong>{title}</strong>"
                if tag:
                    line += f"（{tag}）"
                if detail:
                    line += f" — {detail}"
                facts.append(line)
            path = _safe_path(p.get("path"))
            actions.append(
                {
                    "id": str(p.get("id") or f"plan-{len(actions) + 1}"),
                    "action_type": "open_path",
                    "action_label": str(p.get("action") or _t("去处理"))[:48],
                    "title": title or _t("执行本周动作"),
                    "body": detail,
                    "path": path,
                }
            )
        if any(
            _text_has_recall_signal(str(p.get("title") or "")) or _text_has_recall_signal(str(p.get("tag") or ""))
            for p in plans
        ):
            actions.insert(0, _default_recall_action())
        if not facts:
            facts = [_t("本周无紧急短板，建议巡检自动发券规则与核销流水。")]
        suggestions = [
            _t("优先处理转化与库存类动作，再补获客入口。"),
            _t("写操作完成后，到优惠券中心核对批次与规则状态。"),
        ]
        if not actions:
            actions = [_default_recall_action()]
        return {
            "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
            "facts": facts,
            "suggestions": suggestions,
            "actions": _normalize_actions(actions, overview),
            "confidence": "medium",
            "confidence_note": _t("规则模板：由私域看板指标拼装"),
            "source": "material",
        }

    # radar
    radar = list(ai.get("radar") or [])
    alerts = [r for r in radar if r.get("kind") == "alert"]
    opps = [r for r in radar if r.get("kind") != "alert"]
    facts = []
    suggestions = []
    actions = []
    for r in alerts[:4]:
        title = str(r.get("title") or "").strip() if r.get("title") else ""
        hyp = str(r.get("hypothesis") or "").strip() if r.get("hypothesis") else ""
        metric = str(r.get("metric") or "").strip() if r.get("metric") else ""
        line = f"<strong>{title}</strong>"
        if metric:
            line += f"（{metric}）"
        if hyp:
            line += f" — {hyp}"
        facts.append(line)
        actions.append(
            {
                "id": str(r.get("id") or f"rd-{len(actions) + 1}"),
                "action_type": "open_path",
                "action_label": str(r.get("action") or _t("去处理"))[:48],
                "title": title,
                "body": hyp,
                "path": _safe_path(r.get("path")),
            }
        )
    for r in opps[:3]:
        title = str(r.get("title") or "").strip() if r.get("title") else ""
        hyp = str(r.get("hypothesis") or "").strip() if r.get("hypothesis") else ""
        metric = str(r.get("metric") or "").strip() if r.get("metric") else ""
        line = f"<strong>{title}</strong>"
        if metric:
            line += f"（{metric}）"
        if hyp:
            line += f" — {hyp}"
        suggestions.append(line)
    if not facts:
        facts = [_t("近一周发放/核销/建联波动平稳，暂无显著异常。")]
    if not suggestions:
        suggestions = [_t("可顺势检查自动规则覆盖面，把握沉默客召回窗口。")]
    if any(_text_has_recall_signal(str(r.get("title") or "")) for r in radar):
        actions.insert(0, _default_recall_action())
    if not actions:
        actions = [_default_recall_action()]
    return {
        "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
        "facts": facts,
        "suggestions": suggestions,
        "actions": _normalize_actions(actions, overview),
        "confidence": "medium",
        "confidence_note": _t("规则摘录：由私域看板指标拼装（仅素材）"),
        "source": "material",
    }


def narrate_mkt_ai(db: Session, hotel_id: int, kind: str) -> dict[str, Any]:
    """统一入口：diagnosis | week_plan | radar → 格式化文案 + actions。"""
    if kind not in NARRATIVE_KINDS:
        raise NotFoundError(f"未知 AI 能力: {kind}")
    meta = kind_meta(NARRATIVE_KINDS, kind)
    overview = private_overview(db, hotel_id)
    facts_snap = _facts_from_overview(overview)
    user_prompt = narrate_user_prompt(
        label=str(meta["label"]),
        allowed_paths=ALLOWED_PATHS,
        snapshot=facts_snap,
    )
    return run_narrate(
        db,
        kind=kind,
        meta=meta,
        user_prompt=user_prompt,
        build_fallback=lambda: _rule_fallback(kind, overview),
        normalize_actions=lambda acts: _normalize_actions(acts, overview),
    )


def narrate_mkt_diagnosis(db: Session, hotel_id: int) -> dict[str, Any]:
    return narrate_mkt_ai(db, hotel_id, "diagnosis")


def _pick_or_create_recall_coupon(db: Session, hotel_id: int) -> dict[str, Any]:
    from mkt.mkt_service import create_coupon
    from models import MktCoupon

    existing = (
        db.query(MktCoupon)
        .filter(MktCoupon.hotel_id == hotel_id, MktCoupon.status.in_(("active", "draft")))
        .order_by(MktCoupon.id.desc())
        .all()
    )
    for c in existing:
        if _is_recall_coupon_name(c.name):
            if c.status != "active":
                c.status = "active"
                db.commit()
            return {"id": c.id, "name": c.name, "created": False}
    recall_name = _t(_RECALL_COUPON_NAME_ZH)
    created = create_coupon(
        db,
        hotel_id,
        {
            "name": recall_name,
            "coupon_type": "CASH_ALL",
            "reduce_amount": 50,
            "threshold": 0,
            "status": "active",
            "total_qty": 500,
            "per_user_qty": 1,
            "validity_mode": "RELATIVE",
            "validity_days": 30,
            "created_by": "ai_diagnosis",
        },
    )
    return {"id": created.get("id"), "name": created.get("name") or recall_name, "created": True}


def _ensure_recall_rule(db: Session, hotel_id: int, batch_id: int) -> dict[str, Any]:
    from mkt.mkt_auto_rules import rule_to_dict, set_status, upsert_rule
    from models import MktCouponAutoRule

    name = _t(_RECALL_RULE_NAME_ZH)
    desc = _t(_RECALL_RULE_DESC_ZH)
    names = _recall_rule_name_variants()
    row = (
        db.query(MktCouponAutoRule)
        .filter(MktCouponAutoRule.property_id == hotel_id, MktCouponAutoRule.name.in_(names))
        .first()
    )
    if row:
        if row.name != name:
            row.name = name
            if not (row.description or "").strip():
                row.description = desc
            db.commit()
        if row.status != "active":
            return set_status(db, hotel_id, row.id, "active")
        return rule_to_dict(db, row)
    return upsert_rule(
        db,
        hotel_id,
        {
            "name": name,
            "description": desc,
            "event_type": "SILENT_DAYS",
            "event_params": {"silent_days": 30},
            "coupons": [{"batch_id": int(batch_id), "qty": 1}],
            "filters": [{"field": "channel_reachable", "op": "=", "value": True}],
            "rule_cooldown_days": 30,
            "global_silence_days": 7,
            "enable_now": True,
            "updated_by": "ai_ops",
        },
    )


def execute_mkt_diagnosis_action(db: Session, hotel_id: int, action: dict) -> dict[str, Any]:
    """执行 AI 可写操作按钮。"""
    at = str((action or {}).get("action_type") or "")
    path = _safe_path((action or {}).get("path"))

    if at == "open_path":
        return {
            "ok": True,
            "action_type": at,
            "message": _t("请前往对应页面处理"),
            "deep_link": path,
            "wrote": False,
        }

    if at == "create_recall_coupon":
        coupon = _pick_or_create_recall_coupon(db, hotel_id)
        return {
            "ok": True,
            "action_type": at,
            "message": (
                _t("已创建回归券「{name}」").format(name=coupon.get("name"))
                if coupon.get("created")
                else _t("已启用回归券「{name}」").format(name=coupon.get("name"))
            ),
            "coupon_id": coupon.get("id"),
            "deep_link": "/acquisition/coupons",
            "wrote": True,
        }

    if at == "create_recall_rule":
        coupon = _pick_or_create_recall_coupon(db, hotel_id)
        rule = _ensure_recall_rule(db, hotel_id, int(coupon["id"]))
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已启用自动规则「{name}」").format(name=rule.get("name") or _t("沉默回归")),
            "rule_id": rule.get("id"),
            "coupon_id": coupon.get("id"),
            "deep_link": "/acquisition/coupons?tab=grant&sub=rules",
            "wrote": True,
        }

    if at == "create_recall_pack":
        coupon = _pick_or_create_recall_coupon(db, hotel_id)
        rule = _ensure_recall_rule(db, hotel_id, int(coupon["id"]))
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已落地：券「{coupon}」+ 规则「{rule}」").format(
                coupon=coupon.get("name"),
                rule=rule.get("name") or _t("沉默回归"),
            ),
            "rule_id": rule.get("id"),
            "coupon_id": coupon.get("id"),
            "deep_link": "/acquisition/coupons?tab=grant&sub=rules",
            "wrote": True,
        }

    raise InvalidStateError(f"不支持的 action_type: {at}")


def stream_mkt_ai_ops(db: Session, hotel_id: int, kind: str):
    """兼容旧流式接口：改为一次性产出 done（不再吐 JSON token）。"""
    data = narrate_mkt_ai(db, hotel_id, kind)
    yield {
        "type": "meta",
        "kind": kind,
        "label": data.get("label"),
        "model": data.get("model"),
        "provider": data.get("provider"),
    }
    yield {"type": "done", "data": {**data, "items": []}}
