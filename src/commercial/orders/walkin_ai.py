# SPDX-License-Identifier: BUSL-1.1
"""散客入住 AI 推房：解析自然语言诉求，从可售空净房中排序推荐。"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from infra.i18n import t
from models import Guest, Order, PriceSuggestion, Reservation, Room, RoomType

AVAILABLE_STATUSES = ("vacant", "clean", "inspected")


def _parse_json_blob(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def list_sellable_rooms(db: Session, hotel_id: int) -> list[dict]:
    """可售且未占用：空净/查房，且无在住 reservation。"""
    occupied_ids = {
        r.room_id
        for r, o in (
            db.query(Reservation, Order)
            .join(Order, Reservation.order_id == Order.id)
            .filter(Order.hotel_id == hotel_id, Order.status == "checked_in")
            .all()
        )
        if r.room_id
    }
    price_by_type: dict[int, float] = {}
    for p in (
        db.query(PriceSuggestion)
        .filter(PriceSuggestion.hotel_id == hotel_id, PriceSuggestion.biz_date == date.today())
        .all()
    ):
        price_by_type[p.room_type_id] = float(p.suggested_price or p.current_price or 0)

    rows = (
        db.query(Room, RoomType)
        .outerjoin(RoomType, Room.room_type_id == RoomType.id)
        .filter(Room.hotel_id == hotel_id, Room.status.in_(AVAILABLE_STATUSES))
        .order_by(Room.floor.asc(), Room.room_no.asc())
        .all()
    )
    out = []
    for room, rt in rows:
        if room.id in occupied_ids:
            continue
        base = float(rt.base_price) if rt and rt.base_price is not None else 0.0
        ai = price_by_type.get(room.room_type_id) or base
        name = (rt.name or "") if rt else ""
        bed = (rt.bed_type or "") if rt else ""
        out.append(
            {
                "id": room.id,
                "room_no": room.room_no,
                "floor": room.floor,
                "building": room.building,
                "status": room.status,
                "room_type_id": room.room_type_id,
                "room_type_name": name,
                "bed_type": bed,
                "base_price": base,
                "ai_price": ai,
                "amenities": (rt.amenities or "") if rt else "",
            }
        )
    return out


def _rule_rank(need: str, candidates: list[dict]) -> tuple[list[dict], dict]:
    """无 LLM 时的规则兜底。"""
    text = (need or "").lower()
    prefer_twin = any(k in text for k in ("双床", "双人床", "twin", "两张床"))
    prefer_king = any(k in text for k in ("大床", "king", "一张床", "双人房")) and not prefer_twin
    prefer_quiet = any(k in text for k in ("安静", "静音", "不靠街", "远离电梯", "quiet"))
    prefer_high = any(k in text for k in ("高楼", "高层", "景观", "高楼层"))
    budget = None
    m = re.search(r"(\d{2,5})\s*元", need or "")
    if m:
        budget = int(m.group(1))
    m2 = re.search(r"预算\s*(\d{2,5})", need or "")
    if m2:
        budget = int(m2.group(1))

    scored: list[tuple[float, dict, str]] = []
    for c in candidates:
        score = 0.0
        reasons = []
        name = (c.get("room_type_name") or "") + (c.get("bed_type") or "")
        price = float(c.get("ai_price") or c.get("base_price") or 0)
        floor = int(c.get("floor") or 0)

        if prefer_twin and any(k in name for k in ("双床", "Twin", "twin")):
            score += 40
            reasons.append("匹配双床")
        if prefer_king and any(k in name for k in ("大床", "King", "king", "床")):
            score += 35
            reasons.append("匹配大床")
        if prefer_quiet:
            # ：中高楼层、房号不以 01/02（靠电梯常见）加分
            if floor >= 5:
                score += 15
                reasons.append("楼层偏高更安静")
            rn = str(c.get("room_no") or "")
            if rn and not rn.endswith(("01", "02")):
                score += 10
                reasons.append("相对远离电梯端")
        if prefer_high and floor >= 6:
            score += 12
            reasons.append("高楼层")
        if budget is not None:
            if price <= budget:
                score += 25
                reasons.append(f"价格≤预算¥{budget}")
            else:
                score -= 20
                reasons.append(f"高于预算¥{budget}")
        if c.get("status") in ("clean", "inspected"):
            score += 8
            reasons.append("空净可即办")
        if not reasons:
            reasons.append("可售空房")
        tip = f"AI 建议售价 ¥{int(price)}"
        if c.get("base_price") and price != c["base_price"]:
            tip += f"（相对基价 {int(price - float(c['base_price'])):+d}）"
        tip += " · " + "，".join(reasons[:3])
        item = {**c, "ai_tip": tip, "match_score": round(score, 1)}
        scored.append((score, item, tip))

    scored.sort(key=lambda x: (-x[0], x[1].get("room_no") or ""))
    ranked = [x[1] for x in scored]
    parsed = {
        "bed": "twin" if prefer_twin else ("king" if prefer_king else None),
        "quiet": prefer_quiet,
        "high_floor": prefer_high,
        "budget_max": budget,
        "summary": need.strip()[:80] if need else "散客即时入住",
    }
    return ranked, parsed


def _llm_rank(db: Session, need: str, candidates: list[dict]) -> tuple[list[dict], dict, str]:
    from commercial.ai_core.llm_service import chat as llm_chat
    from commercial.ai_core.llm_service import load_llm_config

    cfg = load_llm_config(db)
    if not cfg.get("enabled", True):
        ranked, parsed = _rule_rank(need, candidates)
        return ranked, parsed, "rules_disabled"

    slim = [
        {
            "id": c["id"],
            "room_no": c["room_no"],
            "floor": c["floor"],
            "status": c["status"],
            "room_type_name": c["room_type_name"],
            "bed_type": c["bed_type"],
            "base_price": c["base_price"],
            "ai_price": c["ai_price"],
        }
        for c in candidates[:40]
    ]
    system = (
        "你是酒店前台智能分房助手。根据客人自然语言诉求，从候选可售空净房中排序推荐。"
        "只输出 JSON，不要 markdown。格式："
        '{"parsed":{"summary":"一句话诉求","bed":"king|twin|null","quiet":true/false,'
        '"high_floor":true/false,"budget_max":number|null,"tags":["安静","大床"]},'
        '"ranked":[{"id":房间id,"reason":"中文推荐理由≤40字","score":0-100}]}'
        "规则：只能使用候选里的 id；优先匹配房型/床型/安静/预算；空净可即办优先。"
    )
    user = f"客人诉求：{need}\n\n候选房间 JSON：\n{json.dumps(slim, ensure_ascii=False)}"
    out = llm_chat(db, [{"role": "user", "content": user}], system)
    content = out.get("content") if isinstance(out, dict) else str(out)
    data = _parse_json_blob(content or "")
    if not data or not isinstance(data.get("ranked"), list):
        ranked, parsed = _rule_rank(need, candidates)
        return ranked, parsed, "rules_parse_fallback"

    by_id = {c["id"]: c for c in candidates}
    ranked: list[dict] = []
    seen = set()
    for row in data["ranked"]:
        try:
            rid = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        if rid in seen or rid not in by_id:
            continue
        seen.add(rid)
        c = dict(by_id[rid])
        reason = str(row.get("reason") or "匹配诉求").strip()
        price = float(c.get("ai_price") or c.get("base_price") or 0)
        tip = f"AI 建议售价 ¥{int(price)}"
        if c.get("base_price") and price != c["base_price"]:
            tip += f"（相对基价 {int(price - float(c['base_price'])):+d}）"
        tip += f" · {reason}"
        c["ai_tip"] = tip
        c["match_score"] = float(row.get("score") or 0)
        ranked.append(c)

    # 补全未出现的候选
    for c in candidates:
        if c["id"] not in seen:
            item = dict(c)
            price = float(item.get("ai_price") or item.get("base_price") or 0)
            item["ai_tip"] = f"备选 · ¥{int(price)}"
            item["match_score"] = 0
            ranked.append(item)

    parsed = data.get("parsed") if isinstance(data.get("parsed"), dict) else {}
    if not parsed.get("summary"):
        parsed["summary"] = (need or "")[:80]
    return ranked, parsed, "llm"


def recommend_rooms(db: Session, hotel_id: int, need: str, limit: int = 8) -> dict[str, Any]:
    candidates = list_sellable_rooms(db, hotel_id)
    if not candidates:
        return {
            "need": need,
            "source": "empty",
            "parsed": {"summary": need, "tags": []},
            "rooms": [],
            "total_candidates": 0,
            "message": "当前无空净可售房，请先调整房态",
        }

    source = "rules"
    identity: dict[str, Any] = {}
    try:
        from commercial.ai_core.llm_service import llm_identity, load_llm_config

        cfg = load_llm_config(db)
        identity = llm_identity(cfg)
        ranked, parsed, source = _llm_rank(db, need, candidates)
        # 成功路径用实际返回刷新 model
        if source == "llm":
            identity = llm_identity(cfg)
    except Exception as e:
        ranked = [dict(c) for c in candidates]
        for item in ranked:
            item.pop("ai_tip", None)
        parsed = {"summary": "", "tags": []}
        source = "unavailable"
        identity = {}
        return {
            "need": need,
            "source": source,
            "parsed": parsed,
            "rooms": ranked[: max(1, min(limit, 12))],
            "total_candidates": len(candidates),
            "message": t("未能调用大模型。下面是可售房清单，不是 AI 推荐。"),
            "llm_error": str(e)[:200],
        }

    tags = list(parsed.get("tags") or [])
    if parsed.get("quiet") and "安静" not in tags:
        tags.append("安静")
    if parsed.get("bed") == "twin" and "双床" not in tags:
        tags.append("双床")
    if parsed.get("bed") == "king" and "大床" not in tags:
        tags.append("大床")
    if parsed.get("budget_max") and f"预算¥{parsed['budget_max']}" not in tags:
        tags.append(f"预算¥{parsed['budget_max']}")
    if parsed.get("high_floor") and "高楼层" not in tags:
        tags.append("高楼层")
    parsed["tags"] = tags

    top = ranked[: max(1, min(limit, 12))]
    if source != "llm":
        identity = {}
    return {
        "need": need,
        "source": source,
        "parsed": parsed,
        "rooms": top,
        "total_candidates": len(candidates),
        "message": f"从 {len(candidates)} 间可售空净房中推荐 {len(top)} 间",
        **identity,
    }


def pick_demo_guest(db: Session, hotel_id: int) -> dict | None:
    """：取本店有过订单的常客做身份预填（证件号仍脱敏合成）。"""
    g = (
        db.query(Guest)
        .join(Order, Order.guest_id == Guest.id)
        .filter(Order.hotel_id == hotel_id)
        .order_by(Guest.id.asc())
        .first()
    )
    if not g:
        g = db.query(Guest).order_by(Guest.id.asc()).first()
    if not g:
        return None
    return {
        "id": g.id,
        "name": g.name,
        "phone": g.phone,
        "one_id": g.one_id,
        "vip_level": g.vip_level,
    }
