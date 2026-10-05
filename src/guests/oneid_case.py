# SPDX-License-Identifier: Apache-2.0
"""OneID 同号冲突 / 归并案例：供 Wizard 页面读取数据库数据。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from bootstrap.ensure_oneid_audit import merge_method_cn, source_cn
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from guests.guest_aliases import (
    guest_unified_scope_ids,
    list_guest_alias_names,
    list_guest_aliases,
    resolve_canonical_guest_id,
)
from guests.i18n_cn import merge_method_cn, source_cn
from guests.order_status_labels import ORDER_ST_CN_H5
from guests.phone_utils import _normalize_phone_storage
from guests.vip_labels import vip_label as _vip_label
from infra.i18n import t as _t
from mkt.wallet_service import list_guest_coupons
from models import Guest, GuestCoupon, GuestIdentity, OneIdPhoneConflict, Order, RoomType


def _status_label(status: str | None) -> str:
    raw = str(status or "")
    msgid = ORDER_ST_CN_H5.get(raw, raw or "—")
    return _t(msgid) if msgid != "—" else "—"


def _mask_phone(phone: str | None) -> str:
    d = _normalize_phone_storage(phone) or "".join(c for c in str(phone or "") if c.isdigit())
    if len(d) >= 7:
        return f"{d[:3]}****{d[-4:]}"
    return phone or "—"


def _guest_card(db: Session, guest: Guest, *, unified: bool = False) -> dict[str, Any]:
    scope_ids = guest_unified_scope_ids(db, guest.id) if unified else [guest.id]
    canonical_id = resolve_canonical_guest_id(db, guest.id) if unified else guest.id
    guest_name_by_id = {row.id: row.name for row in db.query(Guest).filter(Guest.id.in_(scope_ids)).all()}

    orders = db.query(Order).filter(Order.guest_id.in_(scope_ids)).order_by(Order.check_in.desc()).limit(5).all()
    order_list = []
    for o in orders:
        rt_name = None
        if o.room_type_id:
            rt = db.get(RoomType, o.room_type_id)
            rt_name = rt.name if rt else None
        order_list.append(
            {
                "id": o.id,
                "order_no": o.order_no,
                "check_in": str(o.check_in) if o.check_in else None,
                "check_out": str(o.check_out) if o.check_out else None,
                "nights": int(o.nights or 1),
                "room_type": rt_name,
                "total_amount": float(o.total_amount or 0),
                "status": o.status,
                "status_cn": _status_label(o.status),
                **(
                    {
                        "record_guest_id": o.guest_id,
                        "record_guest_name": guest_name_by_id.get(o.guest_id),
                    }
                    if unified and o.guest_id and o.guest_id != canonical_id
                    else {}
                ),
            }
        )
    idents = db.query(GuestIdentity).filter_by(guest_id=guest.id).order_by(GuestIdentity.id.asc()).all()
    coupons = []
    seen_codes: set[str] = set()
    for gid in scope_ids:
        for c in list_guest_coupons(db, gid):
            code = c.get("code")
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)
            item = dict(c)
            if unified and gid != canonical_id:
                item["record_guest_id"] = gid
                item["record_guest_name"] = guest_name_by_id.get(gid)
            coupons.append(item)
    order_n = db.query(Order).filter(Order.guest_id.in_(scope_ids)).count()
    aliases = list_guest_aliases(db, guest.id)
    alias_names = [a["alias_name"] for a in aliases]
    return {
        "guest_id": guest.id,
        "id": guest.id,
        "name": guest.name,
        "phone": guest.phone,
        "phone_mask": _mask_phone(guest.phone),
        "phone_norm": _normalize_phone_storage(guest.phone),
        "one_id": guest.one_id,
        "vip_level": guest.vip_level,
        "vip_label": _vip_label(guest.vip_level or "normal"),
        "city": guest.city,
        "ltv": float(guest.ltv or 0),
        "order_count": order_n,
        "orders": order_list,
        "identities": [
            {
                "source": i.source,
                "source_cn": source_cn(i.source),
                "external_id": i.external_id,
                "confidence": float(i.confidence or 0),
                "merge_method": i.merge_method,
                "merge_method_cn": merge_method_cn(i.merge_method),
            }
            for i in idents
        ],
        "coupons": coupons,
        "coupon_count": len(coupons),
        "aliases": aliases,
        "alias_names": alias_names,
    }


def list_duplicate_phone_groups(db: Session, hotel_id: int, *, limit: int = 20) -> list[dict]:
    """扫描客人手机号归一化后相同的分组（≥2）。"""
    buckets: dict[str, list[Guest]] = {}
    for g in db.query(Guest).filter(Guest.merged_into_guest_id.is_(None)).all():
        key = _normalize_phone_storage(g.phone)
        if len(key) < 8:
            continue
        buckets.setdefault(key, []).append(g)
    out = []
    for phone, guests in buckets.items():
        if len(guests) < 2:
            continue
        guests_sorted = sorted(guests, key=lambda x: (-float(x.ltv or 0), x.id))
        out.append(
            {
                "phone": phone,
                "phone_mask": _mask_phone(phone),
                "count": len(guests_sorted),
                "guests": [_guest_card(db, g) for g in guests_sorted],
                "suggested_primary_id": guests_sorted[0].id,
            }
        )
    out.sort(key=lambda x: (-x["count"], x["phone"]))
    return out[:limit]


def get_oneid_merge_case(db: Session, hotel_id: int, conflict_id: int | None = None) -> dict:
    """
    Wizard 当前案例：优先指定/待处理手机号冲突；否则取同号分组。
    """
    conflict_row = None
    if conflict_id:
        conflict_row = db.get(OneIdPhoneConflict, conflict_id)
        if not conflict_row:
            raise NotFoundError("冲突不存在")
    else:
        conflict_row = (
            db.query(OneIdPhoneConflict)
            .filter_by(hotel_id=hotel_id, status="pending")
            .order_by(OneIdPhoneConflict.id.desc())
            .first()
        )

    if conflict_row:
        try:
            cand_ids = [int(x) for x in json.loads(conflict_row.candidate_guest_ids_json or "[]")]
        except json.JSONDecodeError:
            cand_ids = []
        guests = []
        for gid in cand_ids:
            g = db.get(Guest, gid)
            if g:
                guests.append(_guest_card(db, g))
        if len(guests) < 2:
            # 回退同号扫描
            pass
        else:
            suggested = max(guests, key=lambda x: (x["ltv"], x["order_count"]))
            from application.wecom import list_phone_conflicts

            conf_list = list_phone_conflicts(db, hotel_id, status="pending")
            conf_pub = next((c for c in conf_list if c["id"] == conflict_row.id), None)
            return {
                "source": "phone_conflict",
                "conflict_id": conflict_row.id,
                "conflict": conf_pub,
                "match_type": conflict_row.match_type or "phone_exact_multi",
                "phone": conflict_row.phone_submitted,
                "phone_mask": _mask_phone(conflict_row.phone_submitted),
                "guests": guests,
                "suggested_primary_id": suggested["guest_id"],
                "message": _t("来自待处理手机号冲突（全号或后六位多人）"),
            }

    groups = list_duplicate_phone_groups(db, hotel_id, limit=5)
    if not groups:
        raise NotFoundError(_t("暂无同号冲突或待处理冲突"))
    g0 = groups[0]
    return {
        "source": "duplicate_phone",
        "conflict_id": None,
        "conflict": None,
        "match_type": "phone_exact_multi",
        "phone": g0["phone"],
        "phone_mask": g0["phone_mask"],
        "guests": g0["guests"],
        "suggested_primary_id": g0["suggested_primary_id"],
        "message": _t("来自数据库同号档案扫描"),
    }


def get_guest_asset_summary(db: Session, guest_id: int) -> dict:
    canonical_id = resolve_canonical_guest_id(db, guest_id)
    guest = db.get(Guest, canonical_id)
    if not guest:
        raise NotFoundError("客人不存在")
    card = _guest_card(db, guest, unified=True)
    coupons = card["coupons"]
    active_coupons = [c for c in coupons if c.get("status") == "active" and c.get("redeem_status") != "redeemed"]
    order_amt = sum(float(o.get("total_amount") or 0) for o in card["orders"])
    vip_rank = {"diamond": 4, "platinum": 3, "gold": 2, "silver": 1, "normal": 0}
    return {
        **card,
        "active_coupon_count": len(active_coupons),
        "recent_order_amount": order_amt,
        "insight": (
            f"档案「{guest.name}」"
            + (f"（其他名字：{'、'.join(card['alias_names'])}）" if card.get("alias_names") else "")
            + f"当前 LTV ¥{card['ltv']:,.0f}，"
            f"订单 {card['order_count']} 笔，有效券 {len(active_coupons)} 张，"
            f"会员等级 {card['vip_label']}。"
        ),
        "vip_rank": vip_rank.get((guest.vip_level or "normal").lower(), 0),
    }
