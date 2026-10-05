# SPDX-License-Identifier: Apache-2.0
"""客人私域身份摘要：读 GuestIdentity，不 import wecom SDK。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import GuestIdentity


def guest_private_channel_summary(db: Session, guest_id: int) -> dict | None:
    """按当前 messaging vendor 判定建联；含 channel_reachable，并保留历史 JSON 键。"""
    from extensions.messaging.facade import identity_source, identity_sources_for_reachability, vendor_label
    from mkt.wallet_service import list_guest_coupons

    vendor = identity_source()
    sources = identity_sources_for_reachability()
    ident = (
        db.query(GuestIdentity)
        .filter(GuestIdentity.guest_id == guest_id, GuestIdentity.source.in_(list(sources)))
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    coupons = list_guest_coupons(db, guest_id)
    if not ident and not coupons:
        return None
    in_private = bool(ident)
    return {
        "bound": in_private,
        "channel_bound": in_private,
        "channel_reachable": in_private,
        "in_private": in_private,
        "in_wecom_private": in_private,  # compat
        "vendor": vendor,
        "vendor_label": vendor_label(vendor),
        "source": ident.source if ident else vendor,
        "external_userid": ident.external_id if ident else None,
        "follow_userid": ident.matched_by if ident else None,
        "linked_at": ident.linked_at.isoformat(sep=" ", timespec="seconds") if ident and ident.linked_at else None,
        "merge_method": ident.merge_method if ident else None,
        "confidence": float(ident.confidence) if ident and ident.confidence is not None else None,
        "coupons": coupons,
    }
