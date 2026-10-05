# SPDX-License-Identifier: BUSL-1.1
"""会员体系 AI · #12 等级门槛校准 + #13 权益包推荐（触发式格式化解读）。

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

_MEMBER_CODE_ZH = [
    ("discount_rate", "房费折扣"),
    ("free_breakfast", "免费早餐"),
    ("upgrade_room", "免费升房"),
    ("late_checkout", "延迟退房"),
    ("free_cancellation", "免费取消窗口"),
    ("welcome_fruit", "迎宾果盘"),
    ("vip_lounge", "行政酒廊"),
    ("dedicated_concierge", "专属管家"),
    ("points_acceleration", "积分倍率加成"),
    ("birthday_gift", "生日礼包"),
    ("upgrade_points", "升级成长值"),
    ("retain_points", "保级成长值"),
    ("level_code", "等级"),
    ("apply_level_thresholds", "应用门槛校准"),
    ("apply_benefit_pack", "应用权益包"),
    ("open_path", "前往对应页面"),
    ("silver", "银卡"),
    ("gold", "金卡"),
    ("platinum", "白金卡"),
    ("diamond", "钻石卡"),
    ("supreme", "至尊卡"),
]

ALLOWED_PATHS = [
    "/acquisition/members",
    "/acquisition/points",
    "/acquisition/coupons",
    "/acquisition",
]

ACTION_TYPES = {
    "apply_level_thresholds",
    "apply_benefit_pack",
    "open_path",
}

NARRATIVE_KINDS = {
    "threshold_calibrate": {
        "label": "等级门槛智能校准",
        "left_h": "分布事实",
        "right_h": "校准建议",
        "prompt_domain": "mkt_member",
        "prompt_scene": "threshold_calibrate",
    },
    "benefit_pack": {
        "label": "权益包推荐",
        "left_h": "能力与现状",
        "right_h": "权益建议",
        "prompt_domain": "mkt_member",
        "prompt_scene": "benefit_pack",
    },
}


def _safe_path(path: Optional[str], default: str = "/acquisition/members") -> str:
    return _safe_path_core(path, ALLOWED_PATHS, default)


def _zh_user_text(text: Any) -> str:
    return localize_machine_codes(text, _MEMBER_CODE_ZH)


def _localize_insight_payload(data: dict[str, Any]) -> dict[str, Any]:
    return localize_insight_payload(data, replacements=_MEMBER_CODE_ZH)


def _hotel_room_caps(db: Session, hotel_id: int) -> dict[str, Any]:
    from models import RoomType

    rows = db.query(RoomType).filter(RoomType.hotel_id == hotel_id).order_by(RoomType.id.asc()).all()
    names: list[str] = []
    breakfast_n = 0
    has_lounge = False
    price_band: list[float] = []
    for r in rows:
        name = str(getattr(r, "name", "") or "").strip()
        if name:
            names.append(name)
        if getattr(r, "breakfast_included", None):
            breakfast_n += 1
        am = getattr(r, "amenities", None) or getattr(r, "tags", None) or ""
        am_s = am if isinstance(am, str) else json.dumps(am, ensure_ascii=False)
        if any(k in am_s for k in ("酒廊", "lounge", "行政", "executive")):
            has_lounge = True
        try:
            bp = float(getattr(r, "base_price", None) or 0)
            if bp > 0:
                price_band.append(bp)
        except (TypeError, ValueError):
            pass
    return {
        "room_types": names[:12],
        "room_type_count": len(names),
        "breakfast_capable": breakfast_n > 0,
        "breakfast_room_count": breakfast_n,
        "vip_lounge_capable": has_lounge,
        "avg_room_price": round(sum(price_band) / len(price_band), 0) if price_band else None,
    }


def _build_snapshot(db: Session, hotel_id: int) -> dict[str, Any]:
    from mkt.mkt_member_system import BENEFIT_CATALOG, member_system_bundle

    bundle = member_system_bundle(db, hotel_id)
    levels = bundle.get("levels") or []
    overview = bundle.get("overview") or {}
    dist = overview.get("level_dist") or []
    total = int(overview.get("members") or 0) or 1
    level_briefs = []
    for lv in levels:
        code = lv.get("level_code")
        members = next((d.get("members") for d in dist if d.get("level_code") == code), 0)
        bens = lv.get("benefits") or {}
        on_keys = [k for k, v in bens.items() if isinstance(v, dict) and v.get("on")]
        level_briefs.append(
            {
                "id": lv.get("id"),
                "level_code": code,
                "level_name": lv.get("level_name"),
                "upgrade_points": int(lv.get("upgrade_points") or lv.get("upgrade_value") or 0),
                "retain_points": int(lv.get("retain_points") or lv.get("retention_value") or 0),
                "valid_months": lv.get("valid_months"),
                "members": int(members or 0),
                "share_pct": round(int(members or 0) * 100 / total, 1),
                "benefit_on": on_keys,
                "benefits": bens,
            }
        )
    return {
        "overview": {
            "members": overview.get("members"),
            "total_points": overview.get("total_points"),
            "avg_discount": overview.get("avg_discount"),
        },
        "levels": level_briefs,
        "level_dist": dist,
        "catalog": [
            {
                "key": c["key"],
                "label": c["label"],
                "unit": c.get("unit"),
                "input": c.get("input"),
                "options": c.get("options"),
            }
            for c in BENEFIT_CATALOG
        ],
        "hotel_caps": _hotel_room_caps(db, hotel_id),
        "allowed_paths": ALLOWED_PATHS,
    }


def _suggest_thresholds(levels: list[dict]) -> list[dict]:
    """规则兜底：按分布拉开门槛，避免全挤在入门级。"""
    if not levels:
        return []
    ordered = sorted(levels, key=lambda x: int(x.get("upgrade_points") or 0))
    total = sum(int(x.get("members") or 0) for x in ordered) or 1
    base = [0, 800, 3000, 8000, 20000]
    # 若入门级占比过高，压低中档门槛；若高等级为空且门槛极高，再降一档
    top_share = max((int(x.get("members") or 0) / total for x in ordered), default=0)
    scale = 0.75 if top_share >= 0.7 else (0.9 if top_share >= 0.5 else 1.0)
    out = []
    for i, lv in enumerate(ordered):
        cur_up = int(lv.get("upgrade_points") or 0)
        target = int(base[i] * scale) if i < len(base) else max(cur_up, int(base[-1] * scale * (1 + 0.5 * (i - 4))))
        if i == 0:
            target = 0
        # 平滑：不要偏离现状太远
        if cur_up > 0 and i > 0:
            target = int(cur_up * 0.55 + target * 0.45)
        retain = 0 if target == 0 else max(int(target * 0.7), target - 500)
        out.append(
            {
                "level_code": lv.get("level_code"),
                "level_name": lv.get("level_name"),
                "upgrade_points": max(0, target),
                "retain_points": max(0, retain),
            }
        )
    # 保证严格递增
    prev = -1
    for row in out:
        if row["upgrade_points"] <= prev:
            row["upgrade_points"] = prev + 500
            row["retain_points"] = max(row["retain_points"], int(row["upgrade_points"] * 0.7))
        prev = row["upgrade_points"]
    return out


def _suggest_benefits(levels: list[dict], caps: dict, catalog: list) -> tuple[str, dict]:
    """为最高活跃或中档等级生成一包权益建议。"""
    keys = {c["key"] for c in catalog}
    target = None
    for pref in ("gold", "platinum", "silver", "diamond", "supreme"):
        hit = next((l for l in levels if l.get("level_code") == pref), None)
        if hit:
            target = hit
            break
    if not target and levels:
        target = levels[0]
    code = str(target.get("level_code") if target else "gold")
    name = str(target.get("level_name") if target else "金卡")
    rank = {"silver": 1, "gold": 2, "platinum": 3, "diamond": 4, "supreme": 5}.get(code, 2)
    pack: dict[str, Any] = {}
    if "discount_rate" in keys:
        rate = {1: 1.0, 2: 0.98, 3: 0.95, 4: 0.92, 5: 0.88}.get(rank, 0.98)
        pack["discount_rate"] = {"on": rate < 1, "value": rate}
    if "free_breakfast" in keys:
        n = 0 if not caps.get("breakfast_capable") else min(rank, 2)
        pack["free_breakfast"] = {"on": n > 0, "value": n}
    if "late_checkout" in keys:
        pack["late_checkout"] = {"on": rank >= 2, "value": {2: 2, 3: 4, 4: 6, 5: 6}.get(rank, 2)}
    if "upgrade_room" in keys:
        pack["upgrade_room"] = {
            "on": rank >= 3,
            "value": "any_one_level" if rank >= 4 else "deluxe_to_exec",
        }
    if "vip_lounge" in keys:
        pack["vip_lounge"] = {"on": bool(caps.get("vip_lounge_capable")) and rank >= 4, "value": True}
    if "welcome_fruit" in keys:
        pack["welcome_fruit"] = {"on": rank >= 3, "value": True}
    if "points_acceleration" in keys:
        pack["points_acceleration"] = {"on": rank >= 2, "value": {2: 1.2, 3: 1.5, 4: 2.0, 5: 2.5}.get(rank, 1.2)}
    if "birthday_gift" in keys:
        pack["birthday_gift"] = {
            "on": True,
            "value": "points_1000" if rank <= 2 else ("breakfast_coupon" if rank == 3 else "free_night"),
        }
    if "dedicated_concierge" in keys:
        pack["dedicated_concierge"] = {
            "on": rank >= 4,
            "value": "24h" if rank >= 5 else "work_hours",
        }
    if "free_cancellation" in keys:
        pack["free_cancellation"] = {"on": rank >= 3, "value": {3: 24, 4: 48, 5: 72}.get(rank, 24)}
    return code, pack


def _default_action(kind: str, snap: dict) -> dict:
    levels = snap.get("levels") or []
    if kind == "threshold_calibrate":
        th = _suggest_thresholds(levels)
        return {
            "id": "apply-th",
            "action_type": "apply_level_thresholds",
            "action_label": "应用门槛校准",
            "title": "一键校准升级/保级成长值",
            "body": "按当前会员分布拉开各等级门槛，避免全挤在入门级。",
            "path": "/acquisition/members",
            "thresholds": th,
        }
    code, pack = _suggest_benefits(levels, snap.get("hotel_caps") or {}, snap.get("catalog") or [])
    name = next((l.get("level_name") for l in levels if l.get("level_code") == code), code)
    return {
        "id": "apply-ben",
        "action_type": "apply_benefit_pack",
        "action_label": "应用权益包",
        "title": f"为「{name}」套用推荐权益",
        "body": "按酒店房型能力与等级梯度写入权益开关与强度。",
        "path": "/acquisition/members",
        "level_code": code,
        "benefits": pack,
    }


def _sanitize_thresholds(raw: Any, snap: dict) -> list[dict]:
    levels = {str(l.get("level_code")): l for l in (snap.get("levels") or [])}
    out = []
    if not isinstance(raw, list):
        return _suggest_thresholds(list(levels.values()))
    for row in raw:
        if not isinstance(row, dict):
            continue
        code = str(row.get("level_code") or "").strip()
        if code not in levels:
            continue
        up = max(
            0,
            int(
                row.get("upgrade_points")
                if row.get("upgrade_points") is not None
                else levels[code].get("upgrade_points") or 0
            ),
        )
        retain = max(
            0,
            int(
                row.get("retain_points")
                if row.get("retain_points") is not None
                else levels[code].get("retain_points") or 0
            ),
        )
        if up > 0 and retain > up:
            retain = int(up * 0.8)
        out.append(
            {
                "level_code": code,
                "level_name": levels[code].get("level_name"),
                "id": levels[code].get("id"),
                "upgrade_points": up,
                "retain_points": retain,
            }
        )
    return out or _suggest_thresholds(list(levels.values()))


def _sanitize_benefits(raw: Any, snap: dict) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    catalog = {c["key"]: c for c in (snap.get("catalog") or [])}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in catalog:
            continue
        if not isinstance(v, dict):
            continue
        on = bool(v.get("on"))
        val = v.get("value")
        meta = catalog[k]
        if meta.get("input") == "number":
            try:
                val = float(val) if val is not None else 0
            except (TypeError, ValueError):
                val = 0
            if k == "discount_rate" and val > 1:
                val = val / 10 if val <= 10 else 0.95
            if k == "discount_rate":
                val = max(0.8, min(1.0, float(val)))
        elif meta.get("input") == "bool":
            val = True if on else False
        elif meta.get("input") == "select":
            opts = [o.get("value") for o in (meta.get("options") or [])]
            if val not in opts and opts:
                val = opts[0]
        out[k] = {"on": on, "value": val}
    return out or None


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
            "path": _safe_path(a.get("path"), "/acquisition/members"),
        }
        if at == "apply_level_thresholds":
            item["thresholds"] = _sanitize_thresholds(a.get("thresholds"), snap)
        if at == "apply_benefit_pack":
            codes = {str(l.get("level_code")) for l in (snap.get("levels") or [])}
            code = str(a.get("level_code") or "").strip()
            if code not in codes:
                code = next(iter(codes), "gold")
            bens = _sanitize_benefits(a.get("benefits"), snap)
            if not bens:
                _, bens = _suggest_benefits(
                    snap.get("levels") or [], snap.get("hotel_caps") or {}, snap.get("catalog") or []
                )
            item["level_code"] = code
            item["benefits"] = bens
        out.append(item)
    if not out:
        out = [_default_action(kind, snap)]
    seen = set()
    uniq = []
    for a in out:
        key = (a["action_type"], a.get("title"), a.get("level_code"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:4]


def _rule_fallback(kind: str, snap: dict) -> dict[str, Any]:
    meta = NARRATIVE_KINDS[kind]
    levels = snap.get("levels") or []
    caps = snap.get("hotel_caps") or {}
    total = int((snap.get("overview") or {}).get("members") or 0)

    if kind == "threshold_calibrate":
        facts = [f"当前会员钱包共 <strong>{total}</strong> 人"]
        for lv in levels[:5]:
            facts.append(
                f"「{lv.get('level_name')}」{lv.get('members', 0)} 人（{lv.get('share_pct', 0)}%），"
                f"升级 <strong>{lv.get('upgrade_points', 0)}</strong> / 保级 {lv.get('retain_points', 0)}"
            )
        top = max(levels, key=lambda x: int(x.get("members") or 0), default=None)
        suggestions = []
        if top and float(top.get("share_pct") or 0) >= 60:
            suggestions.append(f"「{top.get('level_name')}」占比过高，建议下调中档升级门槛，引导向上流动。")
        empty_high = [l for l in levels if int(l.get("upgrade_points") or 0) > 0 and int(l.get("members") or 0) == 0]
        if empty_high:
            suggestions.append(
                f"高等级「{empty_high[-1].get('level_name')}」暂无会员，可略降升级门槛或加强对应权益感知。"
            )
        if not suggestions:
            suggestions.append("保持升级门槛递增，保级约为升级的七成，避免「全员卡在入门级」。")
        suggestions.append("校准后请到「等级体系」核对各档成长值再保存其他规则。")
    else:
        facts = [
            f"房型 <strong>{caps.get('room_type_count', 0)}</strong> 个"
            + (f"，均价约 ¥{int(caps['avg_room_price'])}" if caps.get("avg_room_price") else ""),
            f"含早房型：{'有' if caps.get('breakfast_capable') else '暂无明显含早能力'}",
            f"行政酒廊能力：{'可支持' if caps.get('vip_lounge_capable') else '暂不建议开启'}",
        ]
        for lv in levels[:3]:
            on_n = len(lv.get("benefit_on") or [])
            facts.append(f"「{lv.get('level_name')}」已开权益 <strong>{on_n}</strong> 项")
        suggestions = [
            "按等级拉开房费折扣、早餐与延迟退房强度，高等级再叠加升房/管家。",
            "权益设计对齐酒店真实能力，避免承诺无法履约的酒廊或多份早餐。",
        ]

    actions = [_default_action(kind, snap)]
    return _localize_insight_payload(
        {
            "narrative_html": format_insight_html(meta["left_h"], facts, meta["right_h"], suggestions),
            "facts": facts,
            "suggestions": suggestions,
            "actions": actions,
            "confidence": "medium",
            "confidence_note": "规则模板：由会员分布与房型能力拼装",
            "source": "material",
        }
    )


def narrate_member_ai(db: Session, hotel_id: int, kind: str, opts: Optional[dict] = None) -> dict[str, Any]:
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


def execute_member_ai_action(db: Session, hotel_id: int, action: dict) -> dict[str, Any]:
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

    if at == "apply_level_thresholds":
        from mkt.mkt_member_system import list_levels, upsert_level

        thresholds = _sanitize_thresholds((action or {}).get("thresholds"), snap)
        levels = {str(l.get("level_code")): l for l in list_levels(db, hotel_id)}
        updated = []
        for row in thresholds:
            code = row["level_code"]
            cur = levels.get(code)
            if not cur:
                continue
            upsert_level(
                db,
                hotel_id,
                {
                    "id": cur.get("id"),
                    "level_code": code,
                    "level_name": cur.get("level_name") or code,
                    "upgrade_points": row["upgrade_points"],
                    "retain_points": row["retain_points"],
                    "sort_order": cur.get("sort_order"),
                    "valid_months": cur.get("valid_months"),
                    "color_hex": cur.get("color_hex"),
                    "growth_rule": cur.get("growth_rule"),
                    "benefits": cur.get("benefits"),
                },
            )
            updated.append(f"{cur.get('level_name')}→升级{row['upgrade_points']}/保级{row['retain_points']}")
        if not updated:
            raise InvalidStateError("没有可更新的等级门槛")
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已校准 {n} 个等级门槛").format(n=len(updated)),
            "updated": updated,
            "thresholds": thresholds,
            "deep_link": "/acquisition/members",
            "wrote": True,
        }

    if at == "apply_benefit_pack":
        from mkt.mkt_member_system import put_benefits

        code = str((action or {}).get("level_code") or "").strip()
        bens = _sanitize_benefits((action or {}).get("benefits"), snap)
        if not code or not bens:
            code2, bens2 = _suggest_benefits(
                snap.get("levels") or [], snap.get("hotel_caps") or {}, snap.get("catalog") or []
            )
            code = code or code2
            bens = bens or bens2
        assert bens is not None
        put_benefits(db, hotel_id, {"level_code": code, "benefits": bens})
        name = next((l.get("level_name") for l in (snap.get("levels") or []) if l.get("level_code") == code), code)
        on_n = sum(1 for v in bens.values() if v.get("on"))
        return {
            "ok": True,
            "action_type": at,
            "message": _t("已为「{name}」应用推荐权益（开启 {on_n} 项）").format(name=name, on_n=on_n),
            "level_code": code,
            "benefits": bens,
            "deep_link": "/acquisition/members",
            "wrote": True,
        }

    raise InvalidStateError(f"不支持的 action_type: {at}")
