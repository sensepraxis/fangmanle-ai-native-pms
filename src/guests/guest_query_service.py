# SPDX-License-Identifier: Apache-2.0
"""客人域只读查询：从 Fat Router 下沉。"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api_common import row_to_dict
from infra.i18n import t
from models import CrmTask, Guest, GuestIdentity, GuestTag, TagDefinition


def list_oneid_identities(db: Session) -> list[dict[str, Any]]:
    """身份链路：guest_identities + 客人主档字段。"""
    rows = (
        db.query(GuestIdentity, Guest)
        .join(Guest, GuestIdentity.guest_id == Guest.id)
        .order_by(GuestIdentity.id.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for ident, g in rows:
        d = row_to_dict(ident)
        d["guest_name"] = g.name
        d["guest_phone"] = g.phone
        d["one_id"] = g.one_id
        d["vip_level"] = g.vip_level
        d["ltv"] = float(g.ltv or 0)
        out.append(d)
    return out


def list_tags_with_coverage(db: Session) -> list[dict[str, Any]]:
    rows = db.query(TagDefinition).order_by(TagDefinition.id.asc()).all()
    counts = dict(db.query(GuestTag.tag_id, func.count(GuestTag.id)).group_by(GuestTag.tag_id).all())
    out: list[dict[str, Any]] = []
    for row in rows:
        d = row_to_dict(row)
        if d.get("name"):
            d["name"] = t(d["name"])
        d["cover_count"] = int(counts.get(row.id, 0) or 0)
        out.append(d)
    return out


def list_crm_tasks(
    db: Session,
    hotel_id: int,
    *,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    from bootstrap.ensure_crm_extended import ensure_crm_extended

    ensure_crm_extended(db, hotel_id)
    q = db.query(CrmTask).filter(CrmTask.hotel_id == hotel_id)
    if status:
        q = q.filter(CrmTask.status == status)
    rows = q.order_by(CrmTask.id.desc()).limit(100).all()
    return [row_to_dict(t) for t in rows]


__all__ = [
    "list_oneid_identities",
    "list_tags_with_coverage",
    "list_crm_tasks",
]
