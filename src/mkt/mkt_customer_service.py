# SPDX-License-Identifier: Apache-2.0
"""营销客户列表 / 详情 / 备注。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from domain import InvalidStateError, NotFoundError
from models import Guest, GuestIdentity, MktCouponGrant, MktCustomerNote, Order


def list_mkt_customers(
    db: Session,
    hotel_id: int,
    tag: Optional[str] = None,
    *,
    h5_only: bool = False,
) -> list[dict]:
    from bootstrap.ensure_member_crm import _hotel_guest_ids
    from mkt.grant_service import guest_private_bound

    gids = _hotel_guest_ids(db, hotel_id)[:200]
    if not gids:
        return []
    guests = db.query(Guest).filter(Guest.id.in_(gids)).order_by(Guest.id.desc()).all()
    out = []
    for g in guests:
        from extensions.messaging.facade import identity_source

        src = identity_source()
        identities = db.query(GuestIdentity).filter_by(guest_id=g.id).all()
        bound = next((i for i in identities if (i.source or "").lower() == src), None)
        if bound is None and src != "wecom":
            bound = next((i for i in identities if (i.source or "").lower() == "wecom"), None)
        h5_ready = guest_private_bound(db, hotel_id, g.id)
        if h5_only and not h5_ready:
            continue
        grants = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, guest_id=g.id).count()
        notes = (
            db.query(MktCustomerNote)
            .filter_by(hotel_id=hotel_id, guest_id=g.id)
            .order_by(MktCustomerNote.id.desc())
            .limit(3)
            .all()
        )
        last_tag = notes[0].tag if notes else None
        if tag and last_tag != tag:
            continue
        out.append(
            {
                "guest_id": g.id,
                "name": g.name,
                "phone": g.phone_mask or g.phone,
                "one_id": g.one_id or f"G-{g.id}",
                "vip_level": g.vip_level,
                "ltv": float(g.ltv or 0),
                "channel_bound": bool(bound),
                "channel_reachable": bool(bound),
                "in_private": bool(bound),
                "wecom_bound": bool(bound),  # compat
                "in_wecom_private": bool(bound),  # compat
                "channel_source": bound.source if bound else None,
                "h5_ready": h5_ready,
                "external_userid": bound.external_id if bound else None,
                "coupon_count": grants,
                "last_tag": last_tag,
                "last_note": notes[0].note if notes else None,
            }
        )
    return out


def get_mkt_customer(db: Session, hotel_id: int, guest_id: int) -> dict:
    from bootstrap.ensure_member_crm import _hotel_guest_ids

    if guest_id not in set(_hotel_guest_ids(db, hotel_id)):
        raise NotFoundError('"客户不存在"')
    g = db.get(Guest, guest_id)
    if not g:
        raise NotFoundError('"客户不存在"')
    notes = (
        db.query(MktCustomerNote)
        .filter_by(hotel_id=hotel_id, guest_id=guest_id)
        .order_by(MktCustomerNote.id.desc())
        .all()
    )
    from mkt.grant_service import list_grants

    grants = [x for x in list_grants(db, hotel_id) if x["guest_id"] == guest_id]
    orders = db.query(Order).filter_by(hotel_id=hotel_id, guest_id=guest_id).order_by(Order.id.desc()).limit(20).all()
    return {
        "guest_id": g.id,
        "name": g.name,
        "phone": g.phone_mask or g.phone,
        "one_id": g.one_id,
        "notes": [
            {
                "id": n.id,
                "note": n.note,
                "tag": n.tag,
                "created_by": n.created_by,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
        "grants": grants,
        "orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "check_in": str(o.check_in) if o.check_in else None,
                "check_out": str(o.check_out) if o.check_out else None,
                "total_amount": float(o.total_amount or 0),
            }
            for o in orders
        ],
    }


def add_customer_note(db: Session, hotel_id: int, guest_id: int, payload: dict) -> dict:
    from bootstrap.ensure_member_crm import _hotel_guest_ids

    if guest_id not in set(_hotel_guest_ids(db, hotel_id)):
        raise NotFoundError('"客户不存在"')
    note = str(payload.get("note") or "").strip()
    if not note:
        raise InvalidStateError('"备注不能为空"')
    row = MktCustomerNote(
        hotel_id=hotel_id,
        guest_id=guest_id,
        note=note,
        tag=payload.get("tag"),
        created_by=str(payload.get("created_by") or "manager"),
    )
    db.add(row)
    db.commit()
    return get_mkt_customer(db, hotel_id, guest_id)
