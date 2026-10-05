# SPDX-License-Identifier: BUSL-1.1
"""优惠券中心 AI · #7–#11 触发式格式化解读（对齐私域总览约定）。

约定：
1. 用户点击后才调用 LLM
2. 前端只展示 narrative_html + actions，不展示模型原始 JSON
3. actions 提供可写操作或 open_path / 前端回填
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import format_insight_html, run_narrate
from commercial.ai_core.ai_narrative import safe_path as _safe_path_core
from commercial.mkt.mkt_ai_locale import is_en_locale, kind_meta, localize_insight_payload, narrate_user_prompt
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

ALLOWED_PATHS = [
    "/acquisition/coupons",
    "/acquisition/coupons?tab=build",
    "/acquisition/coupons?tab=grant&sub=segment",
    "/acquisition/coupons?tab=grant&sub=rules",
    "/acquisition/coupons?tab=grant&sub=records",
    "/acquisition/coupons?tab=redeem",
    "/acquisition/members",
    "/acquisition",
]

ACTION_TYPES = {
    "create_coupon_draft",
    "create_coupon_rule_pack",
    "open_wizard_prefill",
    "select_segment",
    "create_rule_draft",
    "open_path",
}

NARRATIVE_KINDS = {
    "smart_create": {
        "label": "智能建券助手",
        "left_h": "目标解读",
        "right_h": "建券建议",
        "prompt_domain": "mkt_coupon",
        "prompt_scene": "smart_create",
    },
    "audience": {
        "label": "发券对象智能圈选",
        "left_h": "推荐客群",
        "right_h": "为何这些人",
        "prompt_domain": "mkt_coupon",
        "prompt_scene": "audience",
    },
    "rule_recommend": {
        "label": "自动发券规则推荐",
        "left_h": "规则参数",
        "right_h": "防骚扰与节奏",
        "prompt_domain": "mkt_coupon",
        "prompt_scene": "rule_recommend",
    },
    "budget": {
        "label": "发券预算与面额建议",
        "left_h": "成本测算",
        "right_h": "面额与上限",
        "prompt_domain": "mkt_coupon",
        "prompt_scene": "budget",
    },
    "redeem_insight": {
        "label": "核销归因解读",
        "left_h": "谁在核销",
        "right_h": "无效与机会",
        "prompt_domain": "mkt_coupon",
        "prompt_scene": "redeem_insight",
    },
}


def _safe_path(path: Optional[str], default: str = "/acquisition/coupons") -> str:
    return _safe_path_core(path, ALLOWED_PATHS, default)


def _coupon_brief(c: dict) -> dict:
    granted = int(c.get("granted") or c.get("granted_qty") or 0)
    used = int(c.get("used") or 0)
    rate = round(used * 100 / granted, 1) if granted else 0
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "batch_no": c.get("batch_no"),
        "coupon_type": c.get("coupon_type") or c.get("type"),
        "face_text": c.get("face_text") or c.get("discount_label"),
        "status": c.get("status"),
        "total_qty": c.get("total_qty"),
        "granted": granted,
        "used": used,
        "redeem_rate": rate,
        "reduce_amount": c.get("reduce_amount"),
        "threshold": c.get("threshold"),
        "discount_rate": c.get("discount_rate"),
    }


def _build_snapshot(db: Session, hotel_id: int, opts: Optional[dict] = None) -> dict[str, Any]:
    from mkt.mkt_auto_rules import list_rules
    from mkt.mkt_coupon_engine import list_redeem_log
    from mkt.mkt_service import list_coupons, list_grant_segments

    opts = opts or {}
    coupons = [_coupon_brief(c) for c in list_coupons(db, hotel_id)]
    active = [c for c in coupons if c.get("status") == "active"]
    segments = list_grant_segments(db, hotel_id)[:20]
    rules = list_rules(db, hotel_id)[:15]
    rule_briefs = []
    for r in rules:
        rule_briefs.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "event_type": r.get("event_type"),
                "status": r.get("status"),
                "rule_cooldown_days": r.get("rule_cooldown_days"),
                "global_silence_days": r.get("global_silence_days"),
                "triggered": r.get("triggered_count") or r.get("trigger_count") or r.get("run_count"),
                "granted": r.get("granted_count") or r.get("grant_count"),
            }
        )

    redeem = list_redeem_log(db, hotel_id, limit=40)
    by_batch: dict[str, int] = {}
    guests: dict[str, int] = {}
    for row in redeem:
        bn = str(row.get("batch_no") or row.get("coupon_name") or "未知")
        by_batch[bn] = by_batch.get(bn, 0) + 1
        gn = str(row.get("guest_name") or row.get("guest_id") or "未知")
        guests[gn] = guests.get(gn, 0) + 1
    top_batches = sorted(by_batch.items(), key=lambda x: -x[1])[:5]
    top_guests = sorted(guests.items(), key=lambda x: -x[1])[:5]

    total_granted = sum(int(c.get("granted") or 0) for c in coupons)
    total_used = sum(int(c.get("used") or 0) for c in coupons)
    low_redeem = [c for c in active if int(c.get("granted") or 0) >= 5 and float(c.get("redeem_rate") or 0) < 15][:5]

    return {
        "goal": str(opts.get("goal") or "").strip() or None,
        "target_redeem_rate": opts.get("target_redeem_rate"),
        "target_roi": opts.get("target_roi"),
        "kpi": {
            "batches": len(coupons),
            "active": len(active),
            "granted": total_granted,
            "used": total_used,
            "redeem_rate": round(total_used * 100 / total_granted, 1) if total_granted else 0,
        },
        "coupons": coupons[:25],
        "low_redeem_coupons": low_redeem,
        "segments": [
            {
                "key": str(s.get("key") or s.get("segment_id")),
                "label": s.get("label") or s.get("name"),
                "member_count": s.get("member_count"),
                "reachable_count": s.get("reachable_count"),
                "reach_pct": s.get("reach_pct"),
                "desc": s.get("desc"),
            }
            for s in segments
        ],
        "rules": rule_briefs,
        "allowed_events": [
            "NEW_WECHAT_MEMBER",
            "REG_DAYS",
            "CHECKOUT_DAYS",
            "SILENT_DAYS",
            "BIRTHDAY",
            "HOLIDAY",
            "HIGH_VALUE_NEW",
        ],
        "event_labels_zh": {
            "NEW_WECHAT_MEMBER": "新客加入企微",
            "REG_DAYS": "注册满 N 天",
            "CHECKOUT_DAYS": "退房后 N 天",
            "SILENT_DAYS": "客户沉默 N 天",
            "BIRTHDAY": "客户生日",
            "HOLIDAY": "节假日",
            "HIGH_VALUE_NEW": "高价值新客",
            "CUSTOM": "自定义事件",
        },
        "redeem_summary": {
            "recent_count": len(redeem),
            "top_batches": [{"name": k, "count": v} for k, v in top_batches],
            "top_guests": [{"name": k, "count": v} for k, v in top_guests],
        },
        "allowed_paths": ALLOWED_PATHS,
        "default_batch_id": (active[0]["id"] if active else (coupons[0]["id"] if coupons else None)),
        "room_types": _hotel_room_type_names(db, hotel_id),
    }


def _hotel_room_type_names(db: Session, hotel_id: int) -> list[str]:
    from models import RoomType

    rows = db.query(RoomType).filter(RoomType.hotel_id == hotel_id).order_by(RoomType.id.asc()).all()
    out: list[str] = []
    seen: set[str] = set()
    for r in rows:
        name = str(getattr(r, "name", "") or "").strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _resolve_scope_rooms(raw: dict, snap: dict) -> list[str]:
    """CASH_ROOM 必填：优先用模型给的房型，否则用酒店房型快照兜底。"""
    known = [str(x).strip() for x in (snap.get("room_types") or []) if str(x).strip()]
    known_set = set(known)
    raw_rooms = raw.get("scope_rooms") or raw.get("rooms") or (raw.get("scope") or {}).get("rooms") or []
    if isinstance(raw_rooms, str):
        raw_rooms = [x.strip() for x in raw_rooms.replace("，", ",").split(",") if x.strip()]
    if not isinstance(raw_rooms, list):
        raw_rooms = []
    picked = [str(x).strip() for x in raw_rooms if str(x).strip()]
    if known_set:
        matched = [x for x in picked if x in known_set]
        if matched:
            return matched[:5]
        # 模型写了不存在的房型名时，用酒店实际房型兜底
        return known[: min(3, len(known))]
    return picked[:5]


def _sanitize_coupon_payload(raw: Any, snap: dict) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    typ = str(raw.get("coupon_type") or raw.get("type") or "CASH_ALL").upper()
    if typ not in ("CASH_ALL", "CASH_ROOM", "DISCOUNT", "BENEFIT"):
        typ = "CASH_ALL"
    name = str(raw.get("name") or "").strip() or "AI 建议券"
    payload: dict[str, Any] = {
        "name": name[:40],
        "coupon_type": typ,
        "type": typ,
        "status": "draft",
        "total_qty": max(10, min(5000, int(raw.get("total_qty") or 500))),
        "per_user_qty": max(1, min(5, int(raw.get("per_user_qty") or 1))),
        "validity_mode": "RELATIVE" if str(raw.get("validity_mode") or "").upper() == "RELATIVE" else "FIXED",
        "validity_days": max(7, min(365, int(raw.get("validity_days") or 30))),
        "threshold": float(raw.get("threshold") or 0),
    }
    if typ in ("CASH_ALL", "CASH_ROOM"):
        amt = float(raw.get("reduce_amount") or raw.get("face_value") or 50)
        payload["reduce_amount"] = max(5, min(500, amt))
        if typ == "CASH_ROOM":
            rooms = _resolve_scope_rooms(raw, snap)
            if rooms:
                payload["scope_rooms"] = rooms
                payload["scope_type"] = "ROOM_SPECIFIED"
                payload["scope"] = {"rooms": rooms}
            else:
                # 无可用房型时降级为全场券，避免创建失败
                typ = "CASH_ALL"
                payload["coupon_type"] = typ
                payload["type"] = typ
                payload["threshold"] = 0
                payload["scope_type"] = "ALL"
        if typ == "CASH_ALL":
            payload["threshold"] = 0
    elif typ == "DISCOUNT":
        rate = float(raw.get("discount_rate") or raw.get("face_value") or 0.9)
        if rate > 1:
            rate = rate / 10 if rate <= 10 else 0.9
        payload["discount_rate"] = max(0.5, min(0.99, rate))
        if raw.get("max_discount") is not None:
            payload["max_discount"] = float(raw.get("max_discount"))
    else:
        payload["benefit_key"] = str(raw.get("benefit_key") or "BREAKFAST").upper()
        payload["benefit_value"] = str(raw.get("benefit_value") or raw.get("face_text") or "免费双早")
        payload["face_text"] = payload["benefit_value"]

    if payload["validity_mode"] == "FIXED":
        now = datetime.now()
        payload["valid_from"] = now.strftime("%Y-%m-%dT00:00")
        payload["valid_to"] = (now + timedelta(days=int(payload["validity_days"]))).strftime("%Y-%m-%dT23:59")
    return payload


def _sanitize_rule_payload(raw: Any, snap: dict) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    allowed = set(snap.get("allowed_events") or [])
    event = str(raw.get("event_type") or "SILENT_DAYS").upper()
    if event == "DORMANT":
        event = "SILENT_DAYS"
    if event not in allowed:
        event = "SILENT_DAYS"
    batch_id = raw.get("batch_id") or snap.get("default_batch_id")
    if not batch_id:
        return None
    params = raw.get("event_params") if isinstance(raw.get("event_params"), dict) else {}
    if event == "SILENT_DAYS" and "silent_days" not in params:
        params = {**params, "silent_days": int(params.get("days") or 30)}
    if event == "CHECKOUT_DAYS" and "days" not in params:
        params = {**params, "days": 7}
    filters = (
        raw.get("filters")
        if isinstance(raw.get("filters"), list)
        else [{"field": "channel_reachable", "op": "=", "value": True}]
    )
    return {
        "name": str(raw.get("name") or "AI·自动发券建议")[:40],
        "description": str(raw.get("description") or "由优惠券 AI 生成的规则草稿")[:120],
        "event_type": event,
        "event_params": params,
        "coupons": [{"batch_id": int(batch_id), "qty": 1}],
        "filters": filters[:5],
        "rule_cooldown_days": max(
            0, min(90, int(raw.get("rule_cooldown_days") if raw.get("rule_cooldown_days") is not None else 30))
        ),
        "global_silence_days": max(
            0, min(30, int(raw.get("global_silence_days") if raw.get("global_silence_days") is not None else 7))
        ),
        "as_draft": True,
        "updated_by": "coupon_ai",
    }


def _default_action(kind: str, snap: dict) -> dict:
    goal = snap.get("goal") or "提升核销与召回"
    if kind == "smart_create":
        return {
            "id": "create-draft",
            "action_type": "create_coupon_draft",
            "action_label": "一键建草稿券",
            "title": "按目标生成草稿券",
            "body": f"围绕「{goal}」创建无门槛代金券草稿，可再编辑。",
            "path": "/acquisition/coupons?tab=build",
            "coupon_payload": {
                "name": f"AI·{str(goal)[:10]}券",
                "coupon_type": "CASH_ALL",
                "reduce_amount": 50,
                "threshold": 0,
                "total_qty": 500,
                "validity_mode": "RELATIVE",
                "validity_days": 30,
            },
        }
    if kind == "audience":
        segs = snap.get("segments") or []
        top = segs[0] if segs else None
        if top:
            return {
                "id": "pick-seg",
                "action_type": "select_segment",
                "action_label": "选中推荐客群",
                "title": str(top.get("label") or "推荐客群"),
                "body": str(top.get("desc") or "企微可达客群"),
                "path": "/acquisition/coupons?tab=grant&sub=segment",
                "segment_key": str(top.get("key")),
                "segment_label": top.get("label"),
            }
        return {
            "id": "go-seg",
            "action_type": "open_path",
            "action_label": "去客群运营",
            "title": "先创建全局分群",
            "body": "暂无可用客群，请先到会员/客群运营建分群。",
            "path": "/acquisition/members",
        }
    if kind == "rule_recommend":
        return {
            "id": "rule-draft",
            "action_type": "create_rule_draft",
            "action_label": "生成规则草稿",
            "title": "沉默客自动发券",
            "body": "沉默 30 天触发，冷却 30 天，全局静默 7 天。",
            "path": "/acquisition/coupons?tab=grant&sub=rules",
            "rule_payload": {
                "name": "AI·沉默客自动发券",
                "event_type": "SILENT_DAYS",
                "event_params": {"silent_days": 30},
                "rule_cooldown_days": 30,
                "global_silence_days": 7,
            },
        }
    if kind == "budget":
        return {
            "id": "budget-prefill",
            "action_type": "open_wizard_prefill",
            "action_label": "填入建券向导",
            "title": "建议面额与发放上限",
            "body": "按目标核销率给出面额与总量，打开向导可再调。",
            "path": "/acquisition/coupons?tab=build",
            "coupon_payload": {
                "name": "AI·预算优化券",
                "coupon_type": "CASH_ALL",
                "reduce_amount": 40,
                "threshold": 0,
                "total_qty": 300,
                "validity_mode": "RELATIVE",
                "validity_days": 21,
            },
        }
    # redeem_insight
    return {
        "id": "go-build",
        "action_type": "open_path",
        "action_label": "去优化批次",
        "title": "优化低核销批次",
        "body": "到建券页调整面额、门槛或补发规则。",
        "path": "/acquisition/coupons?tab=build",
    }


def _normalize_actions(raw_actions: list, kind: str, snap: dict) -> list[dict]:
    out: list[dict] = []
    seg_keys = {str(s.get("key")) for s in (snap.get("segments") or [])}
    for i, a in enumerate(raw_actions or []):
        if not isinstance(a, dict):
            continue
        at = str(a.get("action_type") or "open_path")
        if at not in ACTION_TYPES:
            at = "open_path"
        label_blob = f"{a.get('action_label') or ''}{a.get('title') or ''}{a.get('body') or ''}"
        # 文案写「结合规则」却给了 open_wizard_prefill 时，纠正为真正的券+规则落地
        if at == "open_wizard_prefill" and (
            a.get("rule_payload") or any(k in label_blob for k in ("规则", "自动发", "绑定"))
        ):
            at = "create_coupon_rule_pack"
        item: dict[str, Any] = {
            "id": str(a.get("id") or f"a{i + 1}"),
            "action_type": at,
            "action_label": _t(str(a.get("action_label") or "执行"))[:48],
            "title": _t(str(a.get("title") or "建议动作"))[:48],
            "body": _t(str(a.get("body") or ""))[:120] if a.get("body") else "",
            "path": _safe_path(a.get("path"), "/acquisition/coupons"),
        }
        cp = _sanitize_coupon_payload(a.get("coupon_payload"), snap)
        if cp and at in ("create_coupon_draft", "open_wizard_prefill", "create_coupon_rule_pack"):
            item["coupon_payload"] = cp
        sk = str(a.get("segment_key") or "").strip()
        if at == "select_segment":
            if sk and sk in seg_keys:
                item["segment_key"] = sk
                item["segment_label"] = str(a.get("segment_label") or "")[:40]
            else:
                item["action_type"] = "open_path"
                item["path"] = "/acquisition/coupons?tab=grant&sub=segment"
        need_rule = at in ("create_rule_draft", "create_coupon_rule_pack")
        rp = _sanitize_rule_payload(a.get("rule_payload") or a, snap) if need_rule else None
        if at == "create_rule_draft":
            if rp:
                item["rule_payload"] = rp
            else:
                item["action_type"] = "open_path"
                item["path"] = "/acquisition/coupons?tab=grant&sub=rules"
        if at == "create_coupon_rule_pack":
            if not cp:
                item["action_type"] = "open_path"
                item["path"] = "/acquisition/coupons?tab=build"
            else:
                # 规则里的 batch_id 由执行时写入；先保留其余参数
                if not rp:
                    rp = _sanitize_rule_payload(
                        {
                            "name": "AI·沉睡唤醒自动发券",
                            "event_type": "SILENT_DAYS",
                            "event_params": {"silent_days": 60},
                            "rule_cooldown_days": 30,
                            "global_silence_days": 7,
                        },
                        snap,
                    )
                if rp:
                    # batch_id 稍后用新建券覆盖；此处先去掉以免指向旧券
                    rp = {**rp, "coupons": [{"batch_id": 0, "qty": 1}]}
                    item["rule_payload"] = rp
                    item["path"] = "/acquisition/coupons?tab=grant&sub=rules"
                else:
                    item["action_type"] = "create_coupon_draft"
        out.append(item)
    if not out:
        out = [_default_action(kind, snap)]
    seen = set()
    uniq = []
    for a in out:
        key = (a["action_type"], a.get("title"), a.get("segment_key"), a.get("path"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:4]


def _localize_insight_payload(data: dict[str, Any]) -> dict[str, Any]:
    """对 narrative / facts / suggestions / actions 做 locale 清洗（EN 不强制译中）。"""
    return localize_insight_payload(data, replacements=_CODE_ZH_REPLACEMENTS)


_CODE_ZH_REPLACEMENTS = [
    ("NEW_WECHAT_MEMBER", "新客加入企微"),
    ("HIGH_VALUE_NEW", "高价值新客"),
    ("CHECKOUT_DAYS", "退房后 N 天"),
    ("SILENT_DAYS", "客户沉默 N 天"),
    ("REG_DAYS", "注册满 N 天"),
    ("BIRTHDAY", "客户生日"),
    ("HOLIDAY", "节假日"),
    ("CASH_ROOM", "指定房型代金券"),
    ("CASH_ALL", "无门槛代金券"),
    ("DISCOUNT", "折价券"),
    ("BENEFIT", "权益券"),
    ("channel_reachable", "已绑定私域通道"),
    ("create_rule_draft", "生成规则草稿"),
    ("create_coupon_draft", "创建草稿券"),
    ("create_coupon_rule_pack", "建券并绑定规则"),
    ("open_wizard_prefill", "打开建券向导"),
    ("select_segment", "选中客群"),
    ("open_path", "前往对应页面"),
]


def _zh_user_text(text: Any) -> str:
    """兼容旧调用；EN locale 原样返回。"""
    from commercial.mkt.mkt_ai_locale import localize_machine_codes

    s = str(text or "")
    if not s:
        return ""
    if is_en_locale():
        return s
    s = re.sub(r"SILENT_DAYS\s*=\s*(\d+)", r"客户沉默 \1 天", s, flags=re.I)
    s = re.sub(r"CHECKOUT_DAYS\s*=\s*(\d+)", r"退房后 \1 天", s, flags=re.I)
    s = re.sub(r"REG_DAYS\s*=\s*(\d+)", r"注册满 \1 天", s, flags=re.I)
    return localize_machine_codes(s, _CODE_ZH_REPLACEMENTS)


def _rule_fallback(kind: str, snap: dict) -> dict[str, Any]:
    meta = NARRATIVE_KINDS[kind]
    kpi = snap.get("kpi") or {}
    goal = snap.get("goal") or "提升核销与私域召回"
    segs = snap.get("segments") or []
    redeem = snap.get("redeem_summary") or {}
    low = snap.get("low_redeem_coupons") or []

    if kind == "smart_create":
        facts = [
            f"经营目标：<strong>{goal}</strong>",
            f"当前活跃批次 <strong>{kpi.get('active', 0)}</strong>，核销率 <strong>{kpi.get('redeem_rate', 0)}%</strong>",
        ]
        if segs:
            facts.append(
                f"可用客群 <strong>{len(segs)}</strong> 个，示例「{segs[0].get('label')}」可达 "
                f"{segs[0].get('reachable_count', 0)} 人"
            )
        suggestions = [
            "建议用 <strong>无门槛代金券</strong> 降低使用摩擦，面额控制在客单价 5%～10%。",
            "有效期建议 <strong>相对领取后 21～30 天</strong>，便于催核销。",
            "先存草稿，确认客群后再投放。",
        ]
    elif kind == "audience":
        facts = []
        for s in segs[:3]:
            facts.append(
                f"<strong>{s.get('label')}</strong> — 共 {s.get('member_count', 0)} 人，"
                f"企微可达 {s.get('reachable_count', 0)}（{s.get('reach_pct', 0)}%）"
            )
        if not facts:
            facts = ["暂无全局分群，请先到客群运营创建。"]
        suggestions = [
            f"围绕目标「{goal}」，优先选可达率高、近期未密集发券的客群。",
            "实际推送 = 分群 ∩ 企微私域；未建联客人需短信/前台引导。",
        ]
    elif kind == "rule_recommend":
        rules = snap.get("rules") or []
        facts = [
            f"已有自动规则 <strong>{len(rules)}</strong> 条",
            "推荐触发：<strong>客户沉默 30 天</strong>",
            "条件建议保留「已加企微好友 = 是」",
        ]
        suggestions = [
            "规则冷却 <strong>30 天</strong>，全局静默 <strong>7 天</strong>，避免骚扰。",
            "先存草稿，核对券批次后再启用。",
        ]
    elif kind == "budget":
        target = snap.get("target_redeem_rate") or 25
        facts = [
            f"目标核销率约 <strong>{target}%</strong>"
            + (f"，目标投产比 <strong>{snap.get('target_roi')}</strong>" if snap.get("target_roi") else ""),
            f"历史整体核销率 <strong>{kpi.get('redeem_rate', 0)}%</strong>（已发 {kpi.get('granted', 0)}）",
        ]
        suggestions = [
            "建议面额 <strong>¥40～¥60</strong> 无门槛，发放上限 <strong>200～400</strong> 张。",
            "若核销率持续低于目标，优先降门槛而非盲目加面额。",
        ]
    else:
        tops = redeem.get("top_batches") or []
        facts = [
            f"近段核销流水 <strong>{redeem.get('recent_count', 0)}</strong> 笔",
        ]
        for t in tops[:3]:
            facts.append(f"批次「{t.get('name')}」核销 <strong>{t.get('count')}</strong> 次")
        if not tops:
            facts.append("暂无足够核销样本，建议先完成一轮发放。")
        suggestions = []
        for c in low[:2]:
            suggestions.append(
                f"「{c.get('name')}」核销率仅 <strong>{c.get('redeem_rate')}%</strong>，建议降门槛或改相对有效期"
            )
        if not suggestions:
            suggestions = [
                "核销集中在少数批次时，可对低核销券停发并改发更轻门槛券。",
                "再订信号需结合订单号回访高核销客人。",
            ]

    actions = [_default_action(kind, snap)]
    return _localize_insight_payload(
        {
            "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
            "facts": facts,
            "suggestions": suggestions,
            "actions": actions,
            "confidence": "medium",
            "confidence_note": "规则模板：由券批次/客群/核销快照拼装",
            "source": "material",
        }
    )


def narrate_coupon_ai(db: Session, hotel_id: int, kind: str, opts: Optional[dict] = None) -> dict[str, Any]:
    if kind not in NARRATIVE_KINDS:
        raise NotFoundError(f"未知 AI 能力: {kind}")
    meta = kind_meta(NARRATIVE_KINDS, kind)
    snap = _build_snapshot(db, hotel_id, opts)
    base = narrate_user_prompt(
        label=str(meta["label"]),
        allowed_paths=ALLOWED_PATHS,
        snapshot=snap,
    )
    if is_en_locale():
        lang_line = (
            "User-visible strings must be English. "
            "Do not put raw event codes (e.g. SILENT_DAYS) in facts/suggestions/title/body.\n"
        )
    else:
        lang_line = (
            "用户可见文案必须全中文，禁止英文事件码（如 SILENT_DAYS）出现在 facts/suggestions/title/body。\n"
            f"事件中文对照：{json.dumps(snap.get('event_labels_zh') or {}, ensure_ascii=False)}\n"
        )
    user_prompt = lang_line + base
    return run_narrate(
        db,
        kind=kind,
        meta=meta,
        user_prompt=user_prompt,
        build_fallback=lambda: _rule_fallback(kind, snap),
        normalize_actions=lambda acts: _normalize_actions(acts, kind, snap),
        polish=_localize_insight_payload,
    )


def execute_coupon_ai_action(db: Session, hotel_id: int, action: dict) -> dict[str, Any]:
    action = dict(action or {})
    at = str(action.get("action_type") or "")
    label_blob = f"{action.get('action_label') or ''}{action.get('title') or ''}{action.get('body') or ''}"
    # 兼容旧结果：按钮写「结合规则」却是 open_wizard_prefill
    if at == "open_wizard_prefill" and (
        action.get("rule_payload") or any(k in label_blob for k in ("规则", "自动发", "绑定"))
    ):
        at = "create_coupon_rule_pack"
        action["action_type"] = at
    path = _safe_path(action.get("path"))

    if at == "open_path":
        return {
            "ok": True,
            "action_type": at,
            "message": _t("请前往对应页面处理"),
            "deep_link": path,
            "wrote": False,
        }

    if at == "open_wizard_prefill":
        snap = _build_snapshot(db, hotel_id)
        cp = _sanitize_coupon_payload(action.get("coupon_payload"), snap)
        if not cp:
            raise InvalidStateError("缺少有效的建券参数")
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已打开「新建优惠券批次」向导，请在本页上方确认参数后保存"),
            "prefill": {
                "name": cp.get("name"),
                "coupon_type": cp.get("coupon_type"),
                "type": cp.get("coupon_type"),
                "defaults": {
                    "reduce_amount": cp.get("reduce_amount"),
                    "discount_rate": cp.get("discount_rate"),
                    "threshold": cp.get("threshold"),
                    "max_discount": cp.get("max_discount"),
                    "face_text": cp.get("face_text") or cp.get("benefit_value"),
                    "benefit_key": cp.get("benefit_key"),
                    "benefit_value": cp.get("benefit_value"),
                    "validity_mode": cp.get("validity_mode"),
                    "validity_days": cp.get("validity_days"),
                    "total_qty": cp.get("total_qty"),
                    "per_user_qty": cp.get("per_user_qty"),
                    "scope_rooms": cp.get("scope_rooms") or [],
                    "rooms": cp.get("scope_rooms") or [],
                },
            },
            "deep_link": "/acquisition/coupons?tab=build",
            "wrote": False,
        }

    if at == "select_segment":
        sk = str(action.get("segment_key") or "").strip()
        if not sk:
            raise InvalidStateError("缺少 segment_key")
        from mkt.mkt_service import list_grant_segments

        segs = list_grant_segments(db, hotel_id)
        hit = next((s for s in segs if str(s.get("key") or s.get("segment_id")) == sk), None)
        if not hit:
            raise NotFoundError("客群不存在")
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已选中客群「{name}」").format(name=hit.get("label") or hit.get("name")),
            "segment_key": sk,
            "segment_label": hit.get("label") or hit.get("name"),
            "deep_link": "/acquisition/coupons?tab=grant&sub=segment",
            "wrote": False,
        }

    if at == "create_coupon_draft":
        from mkt.mkt_service import create_coupon

        snap = _build_snapshot(db, hotel_id)
        cp = _sanitize_coupon_payload(action.get("coupon_payload"), snap)
        if not cp:
            raise InvalidStateError("缺少有效的建券参数")
        cp["status"] = "draft"
        created = create_coupon(db, hotel_id, cp)
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已创建草稿券「{name}」").format(name=created.get("name")),
            "coupon_id": created.get("id"),
            "coupon": created,
            "deep_link": "/acquisition/coupons?tab=build",
            "wrote": True,
        }

    if at == "create_coupon_rule_pack":
        from mkt.mkt_auto_rules import upsert_rule
        from mkt.mkt_service import create_coupon

        snap = _build_snapshot(db, hotel_id)
        cp = _sanitize_coupon_payload(action.get("coupon_payload"), snap)
        if not cp:
            # 没有券参数时，给一张默认唤醒券
            cp = _sanitize_coupon_payload(
                {
                    "name": "沉睡客唤醒券",
                    "coupon_type": "CASH_ALL",
                    "reduce_amount": 50,
                    "threshold": 0,
                    "total_qty": 500,
                    "validity_mode": "RELATIVE",
                    "validity_days": 30,
                },
                snap,
            )
        assert cp is not None
        # 规则要能发券，批次需可投放
        cp["status"] = "active"
        created = create_coupon(db, hotel_id, cp)
        batch_id = int(created["id"])
        rp = _sanitize_rule_payload(action.get("rule_payload") or {}, snap) or _sanitize_rule_payload(
            {
                "name": "AI·沉睡唤醒自动发券",
                "event_type": "SILENT_DAYS",
                "event_params": {"silent_days": 60},
                "rule_cooldown_days": 30,
                "global_silence_days": 7,
            },
            {**snap, "default_batch_id": batch_id},
        )
        if not rp:
            return {
                "ok": True,
                "action_type": at,
                "message": _t("已创建券「{name}」，但规则未生成（请先检查批次）").format(name=created.get("name")),
                "coupon_id": batch_id,
                "deep_link": "/acquisition/coupons?tab=build",
                "wrote": True,
            }
        rp["coupons"] = [{"batch_id": batch_id, "qty": 1}]
        rp["as_draft"] = True
        # 保证名称可用
        if not str(rp.get("name") or "").strip():
            rp["name"] = "AI·沉睡唤醒自动发券"
        # silent_days 优先用文案/参数里的 60
        params = dict(rp.get("event_params") or {})
        if "60" in label_blob and rp.get("event_type") == "SILENT_DAYS":
            params["silent_days"] = 60
            rp["event_params"] = params
        rule = upsert_rule(db, hotel_id, rp)
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已落地：券「{coupon}」+ 规则草稿「{rule}」，可在「发放→基于规则」启用").format(
                coupon=created.get("name"), rule=rule.get("name")
            ),
            "coupon_id": batch_id,
            "rule_id": rule.get("id"),
            "deep_link": "/acquisition/coupons?tab=grant&sub=rules",
            "wrote": True,
        }

    if at == "create_rule_draft":
        from mkt.mkt_auto_rules import upsert_rule

        snap = _build_snapshot(db, hotel_id)
        rp = _sanitize_rule_payload(action.get("rule_payload") or action, snap)
        if not rp:
            raise InvalidStateError("无法生成规则：请先创建并投放至少一张券批次")
        rule = upsert_rule(db, hotel_id, rp)
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已生成规则草稿「{name}」").format(name=rule.get("name")),
            "rule_id": rule.get("id"),
            "rule": rule,
            "deep_link": "/acquisition/coupons?tab=grant&sub=rules",
            "wrote": True,
        }

    raise InvalidStateError(f"不支持的 action_type: {at}")
