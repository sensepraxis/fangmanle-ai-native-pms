# SPDX-License-Identifier: BUSL-1.1
"""积分规则 AI · #15 倍率建议 / #16 失效唤醒 / #17 场景试算自然语言。

约定：点击后才调 LLM；前端只展示 narrative_html + actions；用户可见文案全中文。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from commercial.ai_core.ai_narrative import format_insight_html, run_narrate
from commercial.ai_core.ai_narrative import safe_path as _safe_path_core
from commercial.mkt.mkt_ai_locale import (
    is_en_locale,
    kind_meta,
    localize_insight_payload,
    localize_machine_codes,
    narrate_user_prompt,
)
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

_POINTS_CODE_ZH = [
    ("BIRTHDAY_5X", "生日入住试算"),
    ("HOLIDAY", "节假日试算"),
    ("SPEND_1000", "消费试算"),
    ("REVIEW_GOOD", "好评奖励试算"),
    ("REFUND", "退款冲销试算"),
    ("EXPIRE", "积分失效试算"),
    ("level_multipliers", "等级基础倍率"),
    ("birthday_bonus_by_level", "生日额外倍率"),
    ("holiday_bonus_by_level", "节假日额外倍率"),
    ("holiday_enabled", "节假日倍率开关"),
    ("daily_cap", "每日获取上限"),
    ("single_order_cap", "单笔订单上限"),
    ("expire_after_days", "有效天数"),
    ("expiry_remind_days", "提前提醒"),
    ("frozen_before_days", "提前冻结"),
    ("points_per_yuan", "积分兑人民币"),
    ("apply_point_rates", "应用倍率建议"),
    ("apply_expire_policy", "应用失效策略"),
    ("create_expire_coupon", "创建唤醒券"),
    ("run_preview", "运行试算"),
    ("open_path", "前往对应页面"),
    ("CASH_ALL", "无门槛代金券"),
    ("supreme", "至尊卡"),
    ("platinum", "白金卡"),
    ("diamond", "钻石卡"),
    ("silver", "银卡"),
    ("gold", "金卡"),
]

ALLOWED_PATHS = [
    "/acquisition/points",
    "/acquisition/coupons",
    "/acquisition/coupons?tab=grant&sub=rules",
    "/acquisition/members",
    "/acquisition",
]

ACTION_TYPES = {
    "apply_point_rates",
    "apply_expire_policy",
    "create_expire_coupon",
    "run_preview",
    "open_path",
}

LEVEL_CODES = ["silver", "gold", "platinum", "diamond", "supreme"]
LEVEL_NAMES = {
    "silver": "银卡",
    "gold": "金卡",
    "platinum": "白金卡",
    "diamond": "钻石卡",
    "supreme": "至尊卡",
}

NARRATIVE_KINDS = {
    "rate_suggest": {
        "label": "积分倍率智能建议",
        "left_h": "负债测算",
        "right_h": "倍率建议",
        "prompt_domain": "mkt_points",
        "prompt_scene": "rate_suggest",
    },
    "expire_wakeup": {
        "label": "积分失效与唤醒策略",
        "left_h": "高积分客",
        "right_h": "唤醒动作",
        "prompt_domain": "mkt_points",
        "prompt_scene": "expire_wakeup",
    },
    "scenario_nl": {
        "label": "场景试算自然语言",
        "left_h": "语句理解",
        "right_h": "试算映射",
        "prompt_domain": "mkt_points",
        "prompt_scene": "scenario_nl",
    },
}


def _safe_path(path: Optional[str], default: str = "/acquisition/points") -> str:
    return _safe_path_core(path, ALLOWED_PATHS, default)


def _zh_user_text(text: Any) -> str:
    return localize_machine_codes(text, _POINTS_CODE_ZH)


def _localize_insight_payload(data: dict[str, Any]) -> dict[str, Any]:
    return localize_insight_payload(data, replacements=_POINTS_CODE_ZH)


def _estimate_liability(rule: dict, kpi: dict) -> dict[str, Any]:
    month_earn = float(kpi.get("month_earn") or 0)
    total_issued = float(kpi.get("total_issued") or 0)
    lm = rule.get("level_multipliers") or {}
    avg_m = 0.0
    n = 0
    for code in LEVEL_CODES:
        try:
            avg_m += float(lm.get(code) or 1)
            n += 1
        except (TypeError, ValueError):
            pass
    avg_m = avg_m / n if n else 1.0
    # 粗估：按当前月获取 × 平均等级倍率相对基础的溢价
    premium = max(0.0, avg_m - 1.0)
    monthly_extra = round(month_earn * premium * 0.35)
    liability_est = round(total_issued * 0.12 + monthly_extra)
    redeem = float(rule.get("points_per_yuan") or 100) or 100
    cash_est = round(liability_est / redeem, 1)
    return {
        "avg_level_multiplier": round(avg_m, 2),
        "monthly_extra_points": monthly_extra,
        "liability_points_est": liability_est,
        "liability_cash_est": cash_est,
        "redeem_points_per_yuan": redeem,
    }


def _high_point_guests(db: Session, hotel_id: int, limit: int = 8) -> list[dict]:
    from models import Guest, MktGuestWallet

    rows = (
        db.query(MktGuestWallet)
        .filter(MktGuestWallet.hotel_id == hotel_id)
        .order_by(MktGuestWallet.points_balance.desc())
        .limit(limit)
        .all()
    )
    out = []
    for w in rows:
        bal = int(w.points_balance or 0)
        if bal <= 0:
            continue
        g = db.get(Guest, w.guest_id) if w.guest_id else None
        out.append(
            {
                "guest_id": w.guest_id,
                "name": (g.name if g else None) or f"客人{w.guest_id}",
                "level_code": w.level_code or "silver",
                "level_name": LEVEL_NAMES.get(w.level_code or "silver", w.level_code or "银卡"),
                "points": bal,
            }
        )
    return out


def _build_snapshot(db: Session, hotel_id: int, opts: Optional[dict] = None) -> dict[str, Any]:
    from mkt.mkt_member_system import SCENARIOS, get_point_rule

    opts = opts or {}
    bundle = get_point_rule(db, hotel_id)
    rule = bundle.get("rule") or {}
    kpi = bundle.get("kpi") or {}
    liability = _estimate_liability(rule, kpi)
    return {
        "nl_query": str(opts.get("query") or opts.get("nl") or "").strip() or None,
        "rule_brief": {
            "base_rate": rule.get("base_rate"),
            "holiday_enabled": rule.get("holiday_enabled"),
            "level_multipliers": {c: (rule.get("level_multipliers") or {}).get(c) for c in LEVEL_CODES},
            "birthday_bonus_by_level": {c: (rule.get("birthday_bonus_by_level") or {}).get(c) for c in LEVEL_CODES},
            "holiday_bonus_by_level": {c: (rule.get("holiday_bonus_by_level") or {}).get(c) for c in LEVEL_CODES},
            "daily_cap": rule.get("daily_cap"),
            "single_order_cap": rule.get("single_order_cap"),
            "expire_after_days": rule.get("expire_after_days"),
            "expiry_remind_days": rule.get("expiry_remind_days"),
            "frozen_before_days": rule.get("frozen_before_days"),
            "points_per_yuan": rule.get("points_per_yuan"),
            "max_deduct_ratio": rule.get("max_deduct_ratio"),
        },
        "kpi": kpi,
        "liability": liability,
        "high_point_guests": _high_point_guests(db, hotel_id),
        "scenarios": [{"key": s["key"], "label": s["label"], "params": s.get("params")} for s in SCENARIOS],
        "customers": bundle.get("customers") or [],
        "level_names": LEVEL_NAMES,
        "allowed_paths": ALLOWED_PATHS,
    }


def _suggest_rate_patch(rule: dict, liability: dict) -> dict:
    """偏保守的倍率组合，抑制通胀。"""
    hot = float(liability.get("avg_level_multiplier") or 1) >= 2.2
    scale = 0.85 if hot else 0.95
    base = [1.0, 1.3, 1.6, 2.0, 2.4]
    bday = [4, 6, 8, 10, 12]
    hol = [1.5, 2, 3, 4, 5]
    lm, bb, hb = {}, {}, {}
    for i, code in enumerate(LEVEL_CODES):
        cur = float((rule.get("level_multipliers") or {}).get(code) or base[i])
        target = base[i] * scale
        lm[code] = round(cur * 0.4 + target * 0.6, 2)
        bb[code] = round(
            float((rule.get("birthday_bonus_by_level") or {}).get(code) or bday[i]) * (0.9 if hot else 1), 1
        )
        hb[code] = round(
            float((rule.get("holiday_bonus_by_level") or {}).get(code) or hol[i]) * (0.85 if hot else 1), 1
        )
    return {
        "holiday_enabled": True,
        "level_multipliers": lm,
        "birthday_bonus_by_level": bb,
        "holiday_bonus_by_level": hb,
        "daily_cap": min(int(rule.get("daily_cap") or 50000), 40000 if hot else 50000),
        "single_order_cap": min(int(rule.get("single_order_cap") or 10000), 8000 if hot else 10000),
    }


def _map_nl_to_preview(query: str, snap: dict) -> dict:
    q = (query or "").strip()
    customers = snap.get("customers") or []
    cust_id = "c_gold"
    if any(k in q for k in ("白金", "李")):
        cust_id = "c_plat"
    elif any(k in q for k in ("银", "新客", "赵")):
        cust_id = "c_sil"
    elif customers:
        cust_id = str(customers[0].get("id") or cust_id)

    scenario = "SPEND_1000"
    params: dict[str, Any] = {"amount": 1000, "nights": 0}
    if any(k in q for k in ("生日",)):
        scenario = "BIRTHDAY_5X"
        params = {"amount": 1800, "nights": 3, "is_birthday_month": True}
    elif any(k in q for k in ("国庆", "节假日", "春节", "五一")):
        scenario = "HOLIDAY"
        params = {"amount": 5500, "nights": 7, "is_holiday": True}
    elif any(k in q for k in ("退款", "冲销")):
        scenario = "REFUND"
        params = {"refund_amount": 1000, "orig_points": 1500}
    elif any(k in q for k in ("失效", "过期")):
        scenario = "EXPIRE"
        params = {"expire_points": 300}
    elif any(k in q for k in ("好评", "评价", "追评")) and not any(k in q for k in ("连住", "晚", "消费")):
        scenario = "REVIEW_GOOD"
        params = {"is_review": True, "is_first_review": True, "nights": 1}
    else:
        # 周中连住等 → 自定义消费+晚数+可选评价
        nights = 2
        m = re.search(r"(\d+)\s*晚", q)
        if m:
            nights = max(1, min(14, int(m.group(1))))
        amount = 800 + nights * 400
        if any(k in q for k in ("周中", "工作日")):
            amount = int(amount * 0.85)
        params = {"amount": amount, "nights": nights}
        if any(k in q for k in ("评价", "好评")):
            params["is_review"] = True
            params["is_first_review"] = True
        scenario = "SPEND_1000"
    return {"customer_id": cust_id, "scenario": scenario, "params": params}


def _sanitize_rate_patch(raw: Any, snap: dict) -> dict:
    rule = snap.get("rule_brief") or {}
    base = _suggest_rate_patch(rule, snap.get("liability") or {})
    if not isinstance(raw, dict):
        return base
    out = dict(base)
    if "holiday_enabled" in raw:
        out["holiday_enabled"] = bool(raw.get("holiday_enabled"))
    for key in ("level_multipliers", "birthday_bonus_by_level", "holiday_bonus_by_level"):
        src = raw.get(key)
        if isinstance(src, dict):
            cleaned = {}
            for code in LEVEL_CODES:
                if code not in src:
                    cleaned[code] = out[key].get(code)
                    continue
                try:
                    cleaned[code] = round(float(src[code]), 2)
                except (TypeError, ValueError):
                    cleaned[code] = out[key].get(code)
            out[key] = cleaned
    for key in ("daily_cap", "single_order_cap", "single_customer_cap"):
        if raw.get(key) is not None:
            try:
                out[key] = max(100, int(raw[key]))
            except (TypeError, ValueError):
                pass
    return out


def _sanitize_expire_patch(raw: Any, snap: dict) -> dict:
    cur = snap.get("rule_brief") or {}
    out = {
        "expire_after_days": int(cur.get("expire_after_days") or 365),
        "frozen_before_days": int(cur.get("frozen_before_days") or 7),
        "expiry_remind_days": list(cur.get("expiry_remind_days") or [30, 7, 1]),
    }
    if not isinstance(raw, dict):
        return {**out, "expiry_remind_days": [30, 7, 1], "frozen_before_days": 7}
    if raw.get("expire_after_days") is not None:
        out["expire_after_days"] = max(30, min(730, int(raw["expire_after_days"])))
    if raw.get("frozen_before_days") is not None:
        out["frozen_before_days"] = max(0, min(30, int(raw["frozen_before_days"])))
    rem = raw.get("expiry_remind_days")
    if isinstance(rem, list) and rem:
        nums = []
        for x in rem[:3]:
            try:
                nums.append(max(1, int(x)))
            except (TypeError, ValueError):
                pass
        if nums:
            out["expiry_remind_days"] = nums
    return out


def _sanitize_preview(raw: Any, snap: dict) -> dict:
    mapped = _map_nl_to_preview(str(snap.get("nl_query") or ""), snap)
    if not isinstance(raw, dict):
        return mapped
    cust_ids = {str(c.get("id")) for c in (snap.get("customers") or [])}
    sc_keys = {str(s.get("key")) for s in (snap.get("scenarios") or [])}
    cust = str(raw.get("customer_id") or mapped["customer_id"])
    if cust not in cust_ids:
        cust = mapped["customer_id"]
    scenario = str(raw.get("scenario") or mapped["scenario"])
    if scenario not in sc_keys:
        scenario = mapped["scenario"]
    params = dict(mapped.get("params") or {})
    if isinstance(raw.get("params"), dict):
        params.update(raw["params"])
    return {"customer_id": cust, "scenario": scenario, "params": params}


def _default_action(kind: str, snap: dict) -> dict:
    if kind == "rate_suggest":
        return {
            "id": "apply-rates",
            "action_type": "apply_point_rates",
            "action_label": "应用倍率建议",
            "title": "写入防通胀倍率组合",
            "body": "下调偏高的等级/节假日倍率，并收紧日获取上限。",
            "path": "/acquisition/points",
            "rate_patch": _sanitize_rate_patch(None, snap),
        }
    if kind == "expire_wakeup":
        return {
            "id": "expire-coupon",
            "action_type": "create_expire_coupon",
            "action_label": "创建唤醒券",
            "title": "积分换房优惠券草稿",
            "body": "给高积分将失效客人准备换券入口，可再到优惠券中心发放。",
            "path": "/acquisition/coupons",
            "coupon_payload": {
                "name": "积分换房优惠券",
                "coupon_type": "CASH_ALL",
                "reduce_amount": 50,
                "threshold": 0,
                "total_qty": 300,
                "validity_mode": "RELATIVE",
                "validity_days": 21,
            },
        }
    return {
        "id": "run-prev",
        "action_type": "run_preview",
        "action_label": "运行试算",
        "title": "按映射结果试算积分",
        "body": "用理解到的场景参数刷新右侧试算。",
        "path": "/acquisition/points",
        "preview": _sanitize_preview(None, snap),
    }


def _normalize_actions(raw_actions: list, kind: str, snap: dict) -> list[dict]:
    out: list[dict] = []
    for i, a in enumerate(raw_actions or []):
        if not isinstance(a, dict):
            continue
        at = str(a.get("action_type") or "open_path")
        if at not in ACTION_TYPES:
            at = "open_path"
        item: dict[str, Any] = {
            "id": str(a.get("id") or f"a{i + 1}"),
            "action_type": at,
            "action_label": _t(str(a.get("action_label") or "执行"))[:48],
            "title": _t(str(a.get("title") or "建议动作"))[:48],
            "body": _t(str(a.get("body") or ""))[:120] if a.get("body") else "",
            "path": _safe_path(a.get("path"), "/acquisition/points"),
        }
        if at == "apply_point_rates":
            item["rate_patch"] = _sanitize_rate_patch(a.get("rate_patch"), snap)
        if at == "apply_expire_policy":
            item["expire_patch"] = _sanitize_expire_patch(a.get("expire_patch"), snap)
        if at == "create_expire_coupon":
            item["coupon_payload"] = a.get("coupon_payload") or _default_action("expire_wakeup", snap).get(
                "coupon_payload"
            )
        if at == "run_preview":
            item["preview"] = _sanitize_preview(a.get("preview"), snap)
        out.append(item)
    if not out:
        out = [_default_action(kind, snap)]
    seen = set()
    uniq = []
    for a in out:
        key = (a["action_type"], a.get("title"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:4]


def _rule_fallback(kind: str, snap: dict) -> dict[str, Any]:
    meta = NARRATIVE_KINDS[kind]
    kpi = snap.get("kpi") or {}
    liab = snap.get("liability") or {}
    guests = snap.get("high_point_guests") or []

    if kind == "rate_suggest":
        facts = [
            f"本月获取约 <strong>{int(kpi.get('month_earn') or 0)}</strong> 分，总发行约 {int(kpi.get('total_issued') or 0)}",
            f"平均等级倍率 <strong>{liab.get('avg_level_multiplier')}</strong>",
            f"估算积分负债约 <strong>{int(liab.get('liability_points_est') or 0)}</strong> 分（约 ¥{liab.get('liability_cash_est')}）",
        ]
        suggestions = [
            "保持等级倍率递增，但把高等级从过高区间回调，避免积分通胀。",
            "节假日额外倍率可保留梯度，同时收紧每日/单笔获取上限。",
        ]
    elif kind == "expire_wakeup":
        facts = [
            f"30 日内将失效约 <strong>{int(kpi.get('expire_soon') or 0)}</strong> 分",
        ]
        for g in guests[:4]:
            facts.append(f"「{g.get('name')}」（{g.get('level_name')}）持有 <strong>{g.get('points')}</strong> 分")
        if len(facts) == 1:
            facts.append("暂无高积分钱包样本，可先完善失效提醒节奏。")
        suggestions = [
            "对高积分客推送「积分换券/抵房」动作，形成再消费闭环。",
            "提前提醒建议保留 30 / 7 / 1 天三档，冻结窗口 7 天。",
        ]
    else:
        q = snap.get("nl_query") or "（未填写，将按默认消费场景）"
        prev = _map_nl_to_preview(str(snap.get("nl_query") or "周中连住2晚+评价"), snap)
        sc_label = next(
            (s.get("label") for s in (snap.get("scenarios") or []) if s.get("key") == prev["scenario"]), "消费试算"
        )
        facts = [
            f"输入：<strong>{q}</strong>",
            f"映射试算：<strong>{sc_label}</strong>",
            f"参数：金额 ¥{prev['params'].get('amount', 0)} · 晚数 {prev['params'].get('nights', 0)}"
            + (" · 含评价" if prev["params"].get("is_review") else ""),
        ]
        suggestions = [
            "点击「运行试算」后，右侧规则试算会按映射结果刷新。",
            "可改选客户身份（银卡/金卡/白金）对比不同倍率。",
        ]

    return _localize_insight_payload(
        {
            "narrative_html": format_insight_html(
                meta["left_h"],
                facts,
                meta["right_h"],
                suggestions,
            ),
            "facts": facts,
            "suggestions": suggestions,
            "actions": [_default_action(kind, snap)],
            "confidence": "medium",
            "confidence_note": "规则摘录：由积分规则与钱包快照拼装（仅素材）",
            "source": "material",
        }
    )


def narrate_points_ai(db: Session, hotel_id: int, kind: str, opts: Optional[dict] = None) -> dict[str, Any]:
    if kind not in NARRATIVE_KINDS:
        raise NotFoundError(f"未知 AI 能力: {kind}")
    meta = kind_meta(NARRATIVE_KINDS, kind)
    snap = _build_snapshot(db, hotel_id, opts)
    base = narrate_user_prompt(
        label=str(meta["label"]),
        allowed_paths=ALLOWED_PATHS,
        snapshot=snap,
    )
    lang_line = "User-visible strings must be English.\n" if is_en_locale() else "用户可见文案必须全中文。\n"
    return run_narrate(
        db,
        kind=kind,
        meta=meta,
        user_prompt=lang_line + base,
        build_fallback=lambda: _rule_fallback(kind, snap),
        normalize_actions=lambda acts: _normalize_actions(acts, kind, snap),
        polish=_localize_insight_payload,
    )


def execute_points_ai_action(db: Session, hotel_id: int, action: dict) -> dict[str, Any]:
    at = str((action or {}).get("action_type") or "")
    path = _safe_path((action or {}).get("path"))
    snap = _build_snapshot(db, hotel_id)

    if at == "open_path":
        return {
            "ok": True,
            "action_type": at,
            "message": _t("请前往对应页面处理"),
            "deep_link": path,
            "wrote": False,
        }

    if at == "apply_point_rates":
        from mkt.mkt_member_system import save_point_rule

        patch = _sanitize_rate_patch((action or {}).get("rate_patch"), snap)
        save_point_rule(db, hotel_id, {"rule": patch})
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已应用积分倍率建议（含上限）"),
            "rate_patch": patch,
            "deep_link": "/acquisition/points",
            "wrote": True,
            "tab": "rate",
        }

    if at == "apply_expire_policy":
        from mkt.mkt_member_system import save_point_rule

        patch = _sanitize_expire_patch((action or {}).get("expire_patch"), snap)
        save_point_rule(db, hotel_id, {"rule": patch})
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已更新失效提醒与冻结策略"),
            "expire_patch": patch,
            "deep_link": "/acquisition/points",
            "wrote": True,
            "tab": "exp",
        }

    if at == "create_expire_coupon":
        from mkt.mkt_service import create_coupon

        raw = (action or {}).get("coupon_payload") or {}
        payload = {
            "name": str(raw.get("name") or "积分换房优惠券")[:40],
            "coupon_type": "CASH_ALL",
            "reduce_amount": float(raw.get("reduce_amount") or 50),
            "threshold": 0,
            "status": "draft",
            "total_qty": max(50, min(2000, int(raw.get("total_qty") or 300))),
            "per_user_qty": 1,
            "validity_mode": "RELATIVE",
            "validity_days": max(7, min(90, int(raw.get("validity_days") or 21))),
            "created_by": "points_ai",
        }
        created = create_coupon(db, hotel_id, payload)
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已创建草稿券「{name}」，可去优惠券中心发放").format(name=created.get("name")),
            "coupon_id": created.get("id"),
            "deep_link": "/acquisition/coupons?tab=build",
            "wrote": True,
        }

    if at == "run_preview":
        from mkt.mkt_member_system import preview_points

        prev = _sanitize_preview((action or {}).get("preview"), snap)
        result = preview_points(db, hotel_id, prev)
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已按自然语言映射完成试算"),
            "preview": prev,
            "preview_result": result,
            "deep_link": "/acquisition/points",
            "wrote": False,
        }

    raise InvalidStateError(f"不支持的 action_type: {at}")
