# SPDX-License-Identifier: Apache-2.0
"""Domain service extracted from thick API handlers."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models as _models
from api_common import row_to_dict
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
from models import (
    CrmTask,
    Guest,
    GuestCoupon,
    GuestIdentity,
    GuestTag,
    OneIdMergeEvent,
    OneIdPhoneConflict,
    Order,
    Reservation,
    Review,
    Room,
    Segment,
    SegmentMember,
    TagDefinition,
    WecomBindTicket,
)

# models.__all__ 未覆盖全部 ORM；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})


def _ensure_today_arrival_demo(db: Session, hotel_id: int) -> None:
    """兜底：若尚无今日到店单，则补齐近几日到店数据（含到店时刻/房号）。"""
    today = date.today()
    marker = f"DEMO-ARR-{hotel_id}-{today.strftime('%m%d')}-01"
    if db.query(Order).filter_by(hotel_id=hotel_id, order_no=marker).first():
        return
    from bootstrap.ensure_order_arrival import seed_arrival_calendar_demo

    seed_arrival_calendar_demo(db, hotel_id)


def build_guests_list(db: Session, hotel_id: int):
    """客户全景列表：guests + 身份来源 + 标签 + 最近到访（本店订单）。"""
    _ensure_today_arrival_demo(db, hotel_id)
    today = date.today()
    sub = db.query(Order.guest_id).filter_by(hotel_id=hotel_id).distinct()
    gids = [x[0] for x in sub if x[0]]
    guests = (
        db.query(Guest)
        .filter(Guest.id.in_(gids), Guest.merged_into_guest_id.is_(None))
        .order_by(Guest.ltv.desc())
        .all()
        if gids
        else []
    )
    if not guests:
        return []

    # 批量标签
    tag_rows = (
        db.query(GuestTag.guest_id, TagDefinition.name)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id.in_(gids))
        .all()
    )
    tags_by_g: dict[int, list[str]] = {}
    for gid, tname in tag_rows:
        tags_by_g.setdefault(gid, []).append(_t(tname) if tname else tname)

    # 批量身份来源
    id_rows = db.query(GuestIdentity).filter(GuestIdentity.guest_id.in_(gids)).all()
    src_by_g: dict[int, list[str]] = {}
    from guests.i18n_cn import source_cn as identity_source_cn

    for i in id_rows:
        label = identity_source_cn(i.source, default="其他")
        bag = src_by_g.setdefault(i.guest_id, [])
        if label not in bag:
            bag.append(label)

    # 最近到访（本店）
    last_rows = (
        db.query(Order.guest_id, func.max(Order.check_in))
        .filter(Order.hotel_id == hotel_id, Order.guest_id.in_(gids))
        .group_by(Order.guest_id)
        .all()
    )
    last_by_g = {gid: cin for gid, cin in last_rows}

    # 今日到店 / 在住（与订单日历口径一致）；房号来自 reservations
    stay_rows = (
        db.query(Order)
        .filter(Order.hotel_id == hotel_id, Order.guest_id.in_(gids))
        .order_by(Order.check_in.desc())
        .all()
    )
    order_ids = [o.id for o in stay_rows]
    room_by_order: dict[int, str] = {}
    if order_ids:
        res_rows = (
            db.query(Reservation.order_id, Room.room_no)
            .join(Room, Reservation.room_id == Room.id)
            .filter(Reservation.order_id.in_(order_ids))
            .all()
        )
        for oid, rno in res_rows:
            if oid not in room_by_order and rno:
                room_by_order[oid] = rno

    arriving_today: dict[int, dict] = {}
    in_stay: dict[int, dict] = {}
    for o in stay_rows:
        if not o.guest_id:
            continue
        cin = o.check_in
        cout = o.check_out
        snap = {
            "order_id": o.id,
            "check_in": cin.isoformat() if cin else None,
            "check_out": cout.isoformat() if cout else None,
            "arrival_time": getattr(o, "arrival_time", None),
            "room_no": room_by_order.get(o.id),
            "status": o.status,
        }
        if cin == today and o.guest_id not in arriving_today:
            arriving_today[o.guest_id] = snap
        if (
            cin
            and cout
            and cin <= today < cout
            and (o.status or "") in ("checked_in", "confirmed")
            and o.guest_id not in in_stay
        ):
            in_stay[o.guest_id] = snap

    out = []
    for g in guests:
        d = row_to_dict(g)
        d["tags"] = tags_by_g.get(g.id, [])
        d["sources"] = " / ".join(src_by_g.get(g.id, [])[:3]) or _t("散客")
        lv = last_by_g.get(g.id)
        d["last_visit"] = lv.isoformat() if hasattr(lv, "isoformat") else (str(lv) if lv else None)
        d["spend"] = float(g.ltv or 0)
        arr = arriving_today.get(g.id)
        stay = in_stay.get(g.id)
        d["arriving_today"] = arr is not None
        d["in_stay"] = stay is not None
        d["today_stay"] = arr or stay
        d["arrival_date"] = (arr or stay or {}).get("check_in")
        d["arrival_time"] = (arr or stay or {}).get("arrival_time")
        out.append(d)
    return out


def build_guest_360(db: Session, guest_id: int):
    from guests.guest_aliases import (
        guest_unified_scope_ids,
        list_guest_alias_names,
        list_guest_aliases,
        resolve_canonical_guest_id,
    )
    from guests.identity_sim import enrich_identity_dict
    from guests.private_identity import guest_private_channel_summary
    from mkt.wallet_service import list_guest_coupons

    canonical_id = resolve_canonical_guest_id(db, guest_id)
    g = db.get(Guest, canonical_id)
    if not g:
        raise NotFoundError("guest not found")
    scope_ids = guest_unified_scope_ids(db, canonical_id)
    guest_name_by_id = {row.id: row.name for row in db.query(Guest).filter(Guest.id.in_(scope_ids)).all()}

    identities = [enrich_identity_dict(row_to_dict(i)) for i in db.query(GuestIdentity).filter_by(guest_id=g.id)]
    tags = (
        db.query(GuestTag, TagDefinition.name, TagDefinition.category)
        .join(TagDefinition, GuestTag.tag_id == TagDefinition.id)
        .filter(GuestTag.guest_id == g.id)
        .all()
    )
    tag_list = [
        {"name": _t(tname) if tname else tname, "category": tcat, "confidence": float(t.confidence)}
        for t, tname, tcat in tags
    ]

    orders_out = []
    for o in db.query(Order).filter(Order.guest_id.in_(scope_ids)).order_by(Order.check_in.desc()).all():
        d = row_to_dict(o)
        if o.guest_id and o.guest_id != canonical_id:
            d["record_guest_id"] = o.guest_id
            d["record_guest_name"] = guest_name_by_id.get(o.guest_id)
        orders_out.append(d)

    reviews_out = []
    for r in db.query(Review).filter(Review.guest_id.in_(scope_ids)).order_by(Review.created_at.desc()).all():
        d = row_to_dict(r)
        if r.guest_id and r.guest_id != canonical_id:
            d["record_guest_id"] = r.guest_id
            d["record_guest_name"] = guest_name_by_id.get(r.guest_id)
        reviews_out.append(d)

    coupon_map: dict[str, dict] = {}
    for gid in scope_ids:
        for c in list_guest_coupons(db, gid):
            code = c.get("code")
            if code and code not in coupon_map:
                item = dict(c)
                if gid != canonical_id:
                    item["record_guest_id"] = gid
                    item["record_guest_name"] = guest_name_by_id.get(gid)
                coupon_map[code] = item
    coupons = list(coupon_map.values())

    private_ch = guest_private_channel_summary(db, g.id)
    guest_d = row_to_dict(g)
    guest_d["alias_names"] = list_guest_alias_names(db, g.id)
    channel_reachable = bool(
        (private_ch or {}).get("channel_reachable")
        or (private_ch or {}).get("bound")
        or (private_ch or {}).get("in_wecom_private")
    )
    from guests.guest_churn import compute_churn_risk

    churn = compute_churn_risk(
        orders=orders_out,
        reviews=reviews_out,
        wecom_bound=channel_reachable,
    )
    guest_d["churn_risk"] = churn["churn_risk"]
    guest_d["churn_method"] = churn["churn_method"]
    guest_d["churn_factors"] = churn["churn_factors"]
    guest_d["churn_inputs"] = churn["churn_inputs"]
    h5_membership = None
    # 私域口径：仅通道建联才返回/补齐 H5 私域资产；未建联不 ensure 造钱包
    if channel_reachable:
        try:
            from mkt.mkt_service import get_guest_h5_membership

            o = db.query(Order).filter(Order.guest_id.in_(scope_ids)).order_by(Order.id.desc()).first()
            hid = int(o.hotel_id) if o and o.hotel_id else 1
            h5_membership = get_guest_h5_membership(db, hid, g.id, ensure=True)
        except Exception:
            h5_membership = None
    return {
        "guest": guest_d,
        "aliases": list_guest_aliases(db, g.id),
        "identities": identities,
        "tags": tag_list,
        "orders": orders_out,
        "reviews": reviews_out,
        "private_channel": private_ch,
        "wecom": private_ch,  # compat：历史前端读 wecom
        "coupons": coupons,
        "unified_scope_guest_ids": scope_ids,
        "h5_membership": h5_membership,
        "channel_reachable": channel_reachable,
        "in_wecom_private": channel_reachable,  # compat
    }


def build_guest_oneid_audit(db: Session, guest_id: int):
    """单客 OneID 归并审计：身份链路 + 持久化归并事件。"""
    from guests.i18n_cn import action_cn, merge_method_cn, source_cn
    from guests.identity_sim import build_event_note, enrich_identity_dict
    from infra.i18n import t

    g = db.get(Guest, guest_id)
    if not g:
        raise NotFoundError("guest not found")
    idents = (
        db.query(GuestIdentity)
        .filter_by(guest_id=g.id)
        .order_by(GuestIdentity.linked_at.asc(), GuestIdentity.id.asc())
        .all()
    )
    ev_rows = (
        db.query(OneIdMergeEvent)
        .filter_by(guest_id=g.id)
        .order_by(OneIdMergeEvent.occurred_at.asc(), OneIdMergeEvent.id.asc())
        .all()
    )
    events = []
    for ev in ev_rows:
        # 按当前 locale 重算 note，避免 DB 里种子中文固化
        note = build_event_note(
            ev.action or "",
            g,
            ev.source or "",
            ev.external_id or "",
            float(ev.confidence or 0.9),
            ev.merge_method or "",
        )
        events.append(
            {
                "id": ev.id,
                "at": ev.occurred_at.isoformat(sep=" ", timespec="seconds") if ev.occurred_at else None,
                "action": ev.action,
                "action_cn": action_cn(ev.action),
                "source": ev.source,
                "source_cn": source_cn(ev.source, default="—"),
                "external_id": ev.external_id,
                "confidence": float(ev.confidence) if ev.confidence is not None else None,
                "merge_method": ev.merge_method,
                "merge_method_cn": merge_method_cn(ev.merge_method),
                "operator": t(str(ev.operator)) if ev.operator else None,
                "note": note,
            }
        )
    avg_conf = round(sum(float(i.confidence or 0) for i in idents) / len(idents), 2) if idents else 1.0
    return {
        "guest": row_to_dict(g),
        "identities": [enrich_identity_dict(row_to_dict(i)) for i in idents],
        "events": events,
        "summary": {
            "one_id": g.one_id,
            "channel_count": len(idents) or 1,
            "avg_confidence": avg_conf,
            "merge_status": "merged" if len(idents) > 1 else "single",
            "merge_status_cn": t("已多渠道归并") if len(idents) > 1 else t("单渠道档案"),
        },
    }


def build_segments_list(db: Session, hotel_id: int):
    """客群分群：segments + segment_members 覆盖人数（缺成员时自动补种）。"""
    from bootstrap.ensure_member_crm import DEFAULT_SEGMENTS, ensure_member_crm, rebuild_segment_members
    from guests.crm_defaults import EXTRA_SEGMENTS

    ensure_member_crm(db, hotel_id)
    # 合并历史重复分群后，若「高流失风险」仍无成员则重建
    risk = db.query(Segment).filter(Segment.hotel_id == hotel_id, Segment.name == "高流失风险").first()
    if risk:
        n_risk = (db.query(func.count(SegmentMember.id)).filter(SegmentMember.segment_id == risk.id).scalar()) or 0
        if n_risk == 0:
            rebuild_segment_members(db, hotel_id)
            db.commit()

    segs = db.query(Segment).filter(Segment.hotel_id == hotel_id).order_by(Segment.id.asc()).all()
    seg_ids = [s.id for s in segs]
    counts: dict[int, int] = {}
    if seg_ids:
        counts = dict(
            db.query(SegmentMember.segment_id, func.count(SegmentMember.id))
            .filter(SegmentMember.segment_id.in_(seg_ids))
            .group_by(SegmentMember.segment_id)
            .all()
        )
    members_by_seg: dict[int, list[int]] = {}
    if seg_ids:
        for sid, gid in (
            db.query(SegmentMember.segment_id, SegmentMember.guest_id)
            .filter(SegmentMember.segment_id.in_(seg_ids))
            .all()
        ):
            members_by_seg.setdefault(sid, []).append(gid)
    from mkt.segment_sql import rule_to_sql

    tone_by_name = {n: t for n, _r, t in DEFAULT_SEGMENTS}
    tone_by_name.update({n: t for n, _r, t in EXTRA_SEGMENTS})
    out = []
    for s in segs:
        d = row_to_dict(s)
        d["member_count"] = int(counts.get(s.id, 0) or 0)
        d["guest_ids"] = members_by_seg.get(s.id, [])
        d["tone"] = tone_by_name.get(s.name, "neutral")
        d["rule"] = s.filter_rule
        compiled = rule_to_sql(s.filter_rule)
        d["sql"] = compiled.get("sql") or ""
        d["rule_meaning"] = compiled.get("meaning") or ""
        d["rule_bullets"] = compiled.get("bullets") or []
        d["rule_source"] = compiled.get("source") or "unknown"
        out.append(d)
    return out


def create_guest_segment(db: Session, hotel_id: int, payload: dict):
    """创建或更新客群分群，并写入 segment_members。"""
    from bootstrap.ensure_member_crm import _guest_tag_codes, _hotel_guest_ids
    from guests.crm_defaults import match_rule_extended

    name = (payload.name or "").strip()
    if not name:
        raise InvalidStateError("分群名称不能为空")

    from bootstrap.ensure_member_crm import clear_segment_deleted_mark

    clear_segment_deleted_mark(db, hotel_id, name)

    seg = db.query(Segment).filter_by(hotel_id=hotel_id, name=name).first()
    if not seg:
        seg = Segment(hotel_id=hotel_id, name=name, filter_rule=payload.filter_rule or "")
        db.add(seg)
        db.flush()
    elif payload.filter_rule:
        seg.filter_rule = payload.filter_rule

    db.query(SegmentMember).filter_by(segment_id=seg.id).delete(synchronize_session=False)

    guest_ids: list[int] = []
    if payload.guest_ids:
        for gid in payload.guest_ids:
            if db.get(Guest, gid):
                guest_ids.append(gid)
    elif payload.filter_rule:
        hotel_gids = _hotel_guest_ids(db, hotel_id)
        guests = (
            db.query(Guest).filter(Guest.id.in_(hotel_gids)).all()
            if hotel_gids
            else db.query(Guest).order_by(Guest.ltv.desc()).limit(120).all()
        )
        tag_map = _guest_tag_codes(db, [g.id for g in guests])
        for g in guests:
            if match_rule_extended(g, tag_map.get(g.id, set()), payload.filter_rule):
                guest_ids.append(g.id)

    for gid in guest_ids:
        db.add(SegmentMember(segment_id=seg.id, guest_id=gid))
    db.commit()
    db.refresh(seg)

    from mkt.segment_sql import rule_to_sql

    compiled = rule_to_sql(seg.filter_rule)
    return {
        "id": seg.id,
        "name": seg.name,
        "filter_rule": seg.filter_rule,
        "member_count": len(guest_ids),
        "guest_ids": guest_ids,
        "tone": "neutral",
        "sql": compiled.get("sql") or "",
        "rule_meaning": compiled.get("meaning") or "",
        "rule_bullets": compiled.get("bullets") or [],
        "rule_source": compiled.get("source") or "unknown",
    }


def merge_oneid_guests(db: Session, payload=None):
    from bootstrap.ensure_oneid_audit import rebuild_events_for_guest
    from guests.guest_aliases import absorb_guest_aliases, merge_vip_level
    from models import GuestCoupon, GuestTag, WecomBindTicket

    primary = db.get(Guest, payload.primary_guest_id)
    secondary = db.get(Guest, payload.secondary_guest_id)
    if not primary or not secondary or primary.id == secondary.id:
        raise InvalidStateError("无效的合并客人")

    moved = 0
    for ident in list(db.query(GuestIdentity).filter_by(guest_id=secondary.id).all()):
        dup = (
            db.query(GuestIdentity)
            .filter_by(guest_id=primary.id, source=ident.source, external_id=ident.external_id)
            .first()
        )
        if dup:
            db.delete(ident)
            continue
        ident.guest_id = primary.id
        ident.is_primary = False
        ident.merge_method = ident.merge_method or "manual_review"
        ident.matched_by = "前台运营"
        ident.linked_at = datetime.now()
        moved += 1

    # 合规：订单/评价原始 guest_id 不改，360 通过 OneID 统一视图聚合展示。

    for sm in list(db.query(SegmentMember).filter_by(guest_id=secondary.id).all()):
        if db.query(SegmentMember).filter_by(segment_id=sm.segment_id, guest_id=primary.id).first():
            db.delete(sm)
        else:
            sm.guest_id = primary.id

    for coupon in list(db.query(GuestCoupon).filter_by(guest_id=secondary.id).all()):
        dup = (
            db.query(GuestCoupon)
            .filter_by(guest_id=primary.id, source=coupon.source, coupon_type=coupon.coupon_type)
            .first()
        )
        if dup:
            db.delete(coupon)
        else:
            coupon.guest_id = primary.id

    for gt in list(db.query(GuestTag).filter_by(guest_id=secondary.id).all()):
        if db.query(GuestTag).filter_by(guest_id=primary.id, tag_id=gt.tag_id).first():
            db.delete(gt)
        else:
            gt.guest_id = primary.id

    db.query(WecomBindTicket).filter_by(guest_id=secondary.id).update({"guest_id": primary.id})

    aliases_added = absorb_guest_aliases(db, primary, secondary)
    primary.ltv = float(primary.ltv or 0) + float(secondary.ltv or 0)
    merge_vip_level(primary, secondary)
    if not primary.one_id and secondary.one_id:
        primary.one_id = secondary.one_id
    if not primary.city and secondary.city:
        primary.city = secondary.city

    # 次档保留为历史档案（merged_into 指向主档），不删行、不改其订单归属。
    db.flush()
    idents = db.query(GuestIdentity).filter_by(guest_id=primary.id).order_by(GuestIdentity.linked_at.asc()).all()
    rebuild_events_for_guest(db, primary, list(idents))
    db.commit()
    guest_d = row_to_dict(primary)
    guest_d["alias_names"] = aliases_added  # 本次新增；完整列表见 GET assets
    return {
        "merged_into": primary.id,
        "guest": guest_d,
        "identities_moved": moved,
        "aliases_added": aliases_added,
    }


def create_crm_tasks(db: Session, hotel_id: int, payload: dict):
    import json

    from bootstrap.ensure_crm_extended import ensure_crm_extended

    ensure_crm_extended(db, hotel_id)
    created = []
    gids = list(payload.guest_ids or [])
    if payload.segment_id and not gids:
        gids = [gid for (gid,) in db.query(SegmentMember.guest_id).filter_by(segment_id=payload.segment_id).all()]
    if not gids:
        raise InvalidStateError("需要 guest_ids 或 segment_id")
    title = (payload.title or "").strip() or {
        "recall": "流失召回",
        "care": "住中关怀",
        "coupon": "专属优惠券",
    }.get(payload.task_type, "客户运营")
    blob = json.dumps(payload.payload or {}, ensure_ascii=False)
    for gid in gids:
        if not db.get(Guest, gid):
            continue
        t = CrmTask(
            hotel_id=hotel_id,
            guest_id=gid,
            segment_id=payload.segment_id,
            task_type=payload.task_type or "recall",
            status="open",
            title=title,
            payload_json=blob,
        )
        db.add(t)
        created.append(t)
    db.commit()
    return {"created": len(created), "tasks": [row_to_dict(t) for t in created]}


def build_guest_arrival_calendar(db: Session, hotel_id: int, days: int = 7):
    """近 N 日到店人数（按订单 check_in），供全景列表迷你日历联动。"""
    _ensure_today_arrival_demo(db, hotel_id)
    today = date.today()
    half = days // 2
    start = today - timedelta(days=half)
    end = today + timedelta(days=days - half - 1)
    rows = (
        db.query(Order.check_in, func.count(Order.id))
        .filter(
            Order.hotel_id == hotel_id,
            Order.check_in.isnot(None),
            Order.check_in >= start,
            Order.check_in <= end,
        )
        .group_by(Order.check_in)
        .all()
    )
    counts = {d: int(n) for d, n in rows if d}
    out = []
    d = start
    while d <= end:
        out.append(
            {
                "date": d.isoformat(),
                "weekday": d.weekday(),
                "arrivals": counts.get(d, 0),
                "is_today": d == today,
            }
        )
        d += timedelta(days=1)
    return out


def build_oneid_board(db: Session):
    """OneID 作业台：多源身份客、低置信链路、待处理冲突统计。"""
    counts = dict(db.query(GuestIdentity.guest_id, func.count(GuestIdentity.id)).group_by(GuestIdentity.guest_id).all())
    multi_ids = [gid for gid, n in counts.items() if n >= 2]
    low_conf_n = (
        db.query(func.count(GuestIdentity.id))
        .filter(GuestIdentity.confidence.isnot(None), GuestIdentity.confidence < 0.85)
        .scalar()
    ) or 0

    from models import OneIdPhoneConflict

    phone_conflicts_pending = int(
        db.query(func.count(OneIdPhoneConflict.id)).filter(OneIdPhoneConflict.status == "pending").scalar() or 0
    )

    return {
        "identity_total": int(db.query(func.count(GuestIdentity.id)).scalar() or 0),
        "multi_source_guests": len(multi_ids),
        "low_confidence_links": int(low_conf_n),
        "phone_conflicts_pending": phone_conflicts_pending,
    }


def compare_guest_segments(db: Session, hotel_id: int, segment_a=None, segment_b=None):
    from bootstrap.ensure_member_crm import ensure_member_crm

    ensure_member_crm(db, hotel_id)

    def _stats(name: str):
        seg = db.query(Segment).filter_by(hotel_id=hotel_id, name=name).first()
        if not seg:
            return {"name": name, "count": 0, "avg_ltv": 0}
        gids = [gid for (gid,) in db.query(SegmentMember.guest_id).filter_by(segment_id=seg.id).all()]
        if not gids:
            return {"name": name, "count": 0, "avg_ltv": 0}
        guests = db.query(Guest).filter(Guest.id.in_(gids)).all()
        avg = sum(float(x.ltv or 0) for x in guests) / max(len(guests), 1)
        return {"name": name, "count": len(guests), "avg_ltv": round(avg, 0)}

    a = _stats(segment_a)
    b = _stats(segment_b)
    return {
        "a": a,
        "b": b,
        "delta_ltv_pct": round((b["avg_ltv"] - a["avg_ltv"]) / max(a["avg_ltv"], 1) * 100, 1) if a["avg_ltv"] else 0,
        "delta_count": b["count"] - a["count"],
    }


def export_guest_segment(db: Session, hotel_id: int, segment_id: int, plaintext=None, ctx: Any = None):
    """分群导出：默认脱敏手机号；拒绝一键明文导出。"""
    from infra.compliance import mask_guest_dict, write_id_doc_audit

    seg = db.query(Segment).filter_by(id=segment_id, hotel_id=hotel_id).first()
    if not seg:
        raise NotFoundError("分群不存在")
    if plaintext:
        write_id_doc_audit(
            db,
            hotel_id=hotel_id,
            checkin_id=None,
            order_id=None,
            operator_id=ctx.user_id,
            action="export_blocked",
            reason=f"拒绝分群 {seg.id} 明文导出",
        )
        db.commit()
        raise AuthorizationError("合规策略：禁止一键导出明文手机号/证件；请使用默认脱敏导出")
    gids = [gid for (gid,) in db.query(SegmentMember.guest_id).filter_by(segment_id=seg.id).all()]
    guests = db.query(Guest).filter(Guest.id.in_(gids)).all() if gids else []
    return {
        "segment_id": seg.id,
        "name": seg.name,
        "guest_ids": gids,
        "masked": True,
        "guests": [mask_guest_dict(row_to_dict(g)) for g in guests],
    }


def post_guest_event(db: Session, hotel_id: int, payload: dict):
    """房务/IoT 信号写入客史（E3 占位）：自动打 iot_anomaly 标签并创建关怀任务。"""
    import json

    from bootstrap.ensure_crm_extended import ensure_crm_extended

    ensure_crm_extended(db, hotel_id)
    g = db.get(Guest, payload.guest_id)
    if not g:
        raise NotFoundError("客人不存在")
    tag = db.query(TagDefinition).filter_by(code="iot_anomaly").first()
    if tag and not db.query(GuestTag).filter_by(guest_id=g.id, tag_id=tag.id).first():
        db.add(GuestTag(guest_id=g.id, tag_id=tag.id, confidence=0.88, source="iot"))
    t = CrmTask(
        hotel_id=hotel_id,
        guest_id=g.id,
        task_type="care",
        status="open",
        title="IoT/房务异常关怀",
        payload_json=json.dumps({"event": payload.event_type, "note": payload.note or ""}, ensure_ascii=False),
    )
    db.add(t)
    db.commit()
    return {"guest_id": g.id, "task_id": t.id}
