# SPDX-License-Identifier: Apache-2.0
"""
客户会员域补种：分群定义 + 成员归属。
在已有 demo.db 上可幂等执行，无需 --reset。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    AppSetting,
    Guest,
    GuestTag,
    Hotel,
    Order,
    Segment,
    SegmentMember,
    TagDefinition,
)

# (zh msgid, en seed, filter_rule, tone hint for UI)
DEFAULT_SEGMENT_DEFS: list[tuple[str, str, str, str]] = [
    ("高价值复购客", "High-value repeat guests", "ltv>5000 AND repeat", "vip"),
    ("亲子家庭客", "Family travelers", "family", "growth"),
    ("高流失风险", "High churn risk", "churn_risk>=0.7", "risk"),  # 与走查 B1「发起关怀」橙色条一致
    ("商务常旅客", "Business frequent guests", "business", "ai"),
    ("VIP 会员", "VIP members", "vip", "vip"),
    ("本月新客", "New guests this month", "new_guest", "neutral"),
]

# 兼容旧引用 (name, filter_rule, tone)
DEFAULT_SEGMENTS = [(zh, rule, tone) for zh, _en, rule, tone in DEFAULT_SEGMENT_DEFS]

AUTO_SEGMENT_RULES = {rule for _zh, _en, rule, _tone in DEFAULT_SEGMENT_DEFS}

DELETED_SEGMENTS_KEY = "deleted_segments:hotel:{hotel_id}"


def _segment_display_name(zh: str, en: str) -> str:
    from seed.locale_pack import seed_text

    return seed_text(zh, en)


def segment_msgid(seg: Segment) -> str:
    """API/展示用中文 msgid（与 DB 里 seed 后的 name 解耦）。"""
    rule = (seg.filter_rule or "").strip()
    for zh, en, r, _tone in DEFAULT_SEGMENT_DEFS:
        if rule == r or (seg.name or "") in (zh, _segment_display_name(zh, en)):
            return zh
    return (seg.name or "").strip()


def _deleted_segment_names(db: Session, hotel_id: int) -> set[str]:
    key = DELETED_SEGMENTS_KEY.format(hotel_id=hotel_id)
    row = db.query(AppSetting).filter_by(key=key).first()
    if not row or not row.value_json:
        return set()
    try:
        import json

        data = json.loads(row.value_json)
        if isinstance(data, list):
            return {str(x) for x in data if x}
    except Exception:
        pass
    return set()


def mark_segment_deleted(db: Session, hotel_id: int, name: str) -> None:
    """记录用户删除的分群名，避免默认分群被 ensure 再次种回。"""
    import json

    key = DELETED_SEGMENTS_KEY.format(hotel_id=hotel_id)
    names = _deleted_segment_names(db, hotel_id)
    names.add((name or "").strip())
    row = db.query(AppSetting).filter_by(key=key).first()
    if not row:
        row = AppSetting(key=key)
        db.add(row)
    row.value_json = json.dumps(sorted(names), ensure_ascii=False)


def clear_segment_deleted_mark(db: Session, hotel_id: int, name: str) -> None:
    """用户重新保存同名分群时，取消「已删除」标记。"""
    import json

    key = DELETED_SEGMENTS_KEY.format(hotel_id=hotel_id)
    names = _deleted_segment_names(db, hotel_id)
    n = (name or "").strip()
    if n not in names:
        return
    names.discard(n)
    row = db.query(AppSetting).filter_by(key=key).first()
    if not row:
        return
    row.value_json = json.dumps(sorted(names), ensure_ascii=False)


def _hotel_guest_ids(db: Session, hotel_id: int) -> list[int]:
    rows = db.query(Order.guest_id).filter(Order.hotel_id == hotel_id).distinct().all()
    return [gid for (gid,) in rows if gid]


def _guest_tag_codes(db: Session, guest_ids: list[int]) -> dict[int, set[str]]:
    if not guest_ids:
        return {}
    rows = (
        db.query(GuestTag.guest_id, TagDefinition.code)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id.in_(guest_ids))
        .all()
    )
    out: dict[int, set[str]] = {}
    for gid, code in rows:
        out.setdefault(gid, set()).add(code or "")
    return out


def match_rule(guest: Guest, tag_codes: set[str], rule: str) -> bool:
    r = (rule or "").strip().lower()
    ltv = float(guest.ltv or 0)
    churn = float(guest.churn_risk or 0)
    vip = (guest.vip_level or "").lower()
    if "ltv>5000" in r.replace(" ", "") and "repeat" in r:
        return ltv > 5000 and ("repeat" in tag_codes or "high_value" in tag_codes)
    if r == "family" or "family" in r:
        return "family" in tag_codes
    if "churn" in r:
        return churn >= 0.7
    if r == "business" or "business" in r:
        return "business" in tag_codes
    if r == "vip":
        return vip in ("gold", "platinum", "diamond", "silver") or "vip" in tag_codes
    if r == "new_guest":
        # 无可靠「本月」字段时：低 LTV + 非 VIP 近似新客
        return ltv < 800 and vip in ("", "normal")
    if "repeat" in r:
        return "repeat" in tag_codes
    return False


def _find_default_segment(db: Session, hotel_id: int, zh: str, en: str, rule: str) -> Segment | None:
    display = _segment_display_name(zh, en)
    for s in db.query(Segment).filter_by(hotel_id=hotel_id).all():
        if (s.filter_rule or "").strip() == rule:
            return s
        if (s.name or "").strip() in (zh, en, display):
            return s
    return None


def ensure_hotel_segments(db: Session, hotel_id: int) -> list[Segment]:
    churn_zh = "高流失风险"
    churn_display = _segment_display_name(churn_zh, "High churn risk")
    # 历史名「潜在流失客户」与走查「高流失风险」合并，避免两张卡规则相同却只有一张有橙色条
    legacy = db.query(Segment).filter_by(hotel_id=hotel_id, name="潜在流失客户").first()
    canonical = _find_default_segment(db, hotel_id, churn_zh, "High churn risk", "churn_risk>=0.7")
    if legacy and canonical and legacy.id != canonical.id:
        # 把成员并到规范名，删掉旧卡
        for m in db.query(SegmentMember).filter_by(segment_id=legacy.id).all():
            exists = db.query(SegmentMember).filter_by(segment_id=canonical.id, guest_id=m.guest_id).first()
            if not exists:
                m.segment_id = canonical.id
            else:
                db.delete(m)
        db.delete(legacy)
        db.flush()
    elif legacy and not canonical:
        legacy.name = churn_display
        legacy.filter_rule = "churn_risk>=0.7"
        db.flush()

    deleted = _deleted_segment_names(db, hotel_id)
    created = False
    for zh, en, rule, _tone in DEFAULT_SEGMENT_DEFS:
        if zh in deleted or _segment_display_name(zh, en) in deleted:
            continue
        display = _segment_display_name(zh, en)
        row = _find_default_segment(db, hotel_id, zh, en, rule)
        if row:
            row.name = display
            if not (row.filter_rule or "").strip():
                row.filter_rule = rule
            continue
        s = Segment(hotel_id=hotel_id, name=display, filter_rule=rule)
        db.add(s)
        created = True
    if created:
        db.flush()
    return db.query(Segment).filter_by(hotel_id=hotel_id).order_by(Segment.id.asc()).all()


def _auto_rule_segment_names() -> set[str]:
    """系统规则分群（可按字段重算）。不含 NL 查询保存的快照客群。"""
    names: set[str] = set()
    for zh, en, _rule, _tone in DEFAULT_SEGMENT_DEFS:
        names.add(zh)
        names.add(_segment_display_name(zh, en))
    try:
        from bootstrap.ensure_crm_extended import EXTRA_SEGMENTS

        for n, _r, _t in EXTRA_SEGMENTS:
            names.add(n)
    except Exception:
        pass
    return names


def _is_managed_auto_segment(seg: Segment) -> bool:
    if _is_nl_snapshot_rule(seg.filter_rule):
        return False
    rule = (seg.filter_rule or "").strip()
    if rule in AUTO_SEGMENT_RULES:
        return True
    return (seg.name or "").strip() in _auto_rule_segment_names()


def _is_nl_snapshot_rule(rule: str | None) -> bool:
    """NL 查询落库多为 JSON 或自然语言原文，不能用 match_rule 清空重算。"""
    r = (rule or "").strip()
    if not r:
        return True
    if r.startswith("{"):
        return True
    # 纯中文查询句（无 DSL 关键字）视为快照
    lower = r.lower().replace(" ", "")
    dsl_keys = (
        "ltv",
        "churn",
        "vip",
        "family",
        "business",
        "repeat",
        "new_guest",
        "high_intent",
        "tag:",
    )
    has_cjk = any("\u4e00" <= c <= "\u9fff" for c in r)
    if has_cjk and not any(k in lower for k in dsl_keys):
        return True
    return False


def rebuild_segment_members(db: Session, hotel_id: int) -> None:
    """按规则重算「系统规则分群」成员；NL/手工快照客群原样保留。"""
    from bootstrap.ensure_crm_extended import match_rule_extended

    try:
        from bootstrap.ensure_crm_extended import ensure_extra_segments

        ensure_extra_segments(db, hotel_id)
    except Exception:
        pass

    segs = ensure_hotel_segments(db, hotel_id)
    gids = _hotel_guest_ids(db, hotel_id)
    if not gids:
        guests = db.query(Guest).order_by(Guest.ltv.desc()).limit(120).all()
        gids = [g.id for g in guests]
    guests = db.query(Guest).filter(Guest.id.in_(gids)).all() if gids else []
    tag_map = _guest_tag_codes(db, gids)

    for seg in segs:
        # 只重算系统规则客群，避免把 NL 快照成员清空
        if not _is_managed_auto_segment(seg):
            continue
        db.query(SegmentMember).filter_by(segment_id=seg.id).delete(synchronize_session=False)
        rule = seg.filter_rule or ""
        for g in guests:
            if match_rule_extended(g, tag_map.get(g.id, set()), rule):
                db.add(SegmentMember(segment_id=seg.id, guest_id=g.id))
    db.flush()


def ensure_member_crm(db: Session, hotel_id: int | None = None) -> None:
    hotels = db.query(Hotel).all()
    targets = [h for h in hotels if hotel_id is None or h.id == hotel_id]
    for h in targets:
        # 规则客群必须随客人属性变化重算；旧逻辑「有成员就不重建」会漏掉后补种 VIP
        ensure_hotel_segments(db, h.id)
        rebuild_segment_members(db, h.id)
    db.commit()
