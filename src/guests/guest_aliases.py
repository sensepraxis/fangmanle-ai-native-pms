# SPDX-License-Identifier: Apache-2.0
"""客人别名（其他名字）：同号归并时保留次档姓名等。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models import Guest, GuestAlias

VIP_RANK = {"diamond": 4, "platinum": 3, "gold": 2, "silver": 1, "normal": 0}


def resolve_canonical_guest_id(db: Session, guest_id: int) -> int:
    """已归并档案 → 指向主档 ID。"""
    seen = set()
    cur = guest_id
    while cur and cur not in seen:
        seen.add(cur)
        g = db.get(Guest, cur)
        if not g or not g.merged_into_guest_id:
            return cur
        cur = int(g.merged_into_guest_id)
    return guest_id


def guest_unified_scope_ids(db: Session, guest_id: int) -> list[int]:
    """OneID 统一视图：主档 + 已归并次档（订单等原始 guest_id 不变）。"""
    canonical = resolve_canonical_guest_id(db, guest_id)
    ids = {canonical}
    for a in list_guest_aliases(db, canonical):
        mid = a.get("merged_from_guest_id")
        if mid:
            ids.add(int(mid))
    for g in db.query(Guest).filter_by(merged_into_guest_id=canonical).all():
        ids.add(g.id)
    return sorted(ids)


def is_merged_secondary(db: Session, guest_id: int) -> bool:
    g = db.get(Guest, guest_id)
    return bool(g and g.merged_into_guest_id)


def list_guest_alias_names(db: Session, guest_id: int) -> list[str]:
    rows = db.query(GuestAlias).filter_by(guest_id=guest_id).order_by(GuestAlias.id.asc()).all()
    return [r.alias_name for r in rows if r.alias_name]


def list_guest_aliases(db: Session, guest_id: int) -> list[dict]:
    rows = db.query(GuestAlias).filter_by(guest_id=guest_id).order_by(GuestAlias.id.asc()).all()
    return [
        {
            "id": r.id,
            "alias_name": r.alias_name,
            "source": r.source,
            "merged_from_guest_id": r.merged_from_guest_id,
            "note": r.note,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


def add_guest_alias(
    db: Session,
    guest_id: int,
    alias_name: str,
    *,
    source: str = "merge",
    merged_from_guest_id: int | None = None,
    note: str | None = None,
) -> bool:
    """新增别名；已存在或与本名相同则返回 False。"""
    name = (alias_name or "").strip()
    if not name:
        return False
    guest = db.get(Guest, guest_id)
    if guest and (guest.name or "").strip() == name:
        return False
    exists = db.query(GuestAlias).filter_by(guest_id=guest_id, alias_name=name).first()
    if exists:
        return False
    db.add(
        GuestAlias(
            guest_id=guest_id,
            alias_name=name,
            source=source,
            merged_from_guest_id=merged_from_guest_id,
            note=note,
            created_at=datetime.now(),
        )
    )
    db.flush()
    return True


def absorb_guest_aliases(db: Session, primary: Guest, secondary: Guest) -> list[str]:
    """归并次档：次档姓名 + 已有别名迁入主档「其他名字」。"""
    added: list[str] = []
    sec_name = (secondary.name or "").strip()
    pri_name = (primary.name or "").strip()
    if sec_name and sec_name != pri_name:
        if add_guest_alias(
            db,
            primary.id,
            sec_name,
            source="merge",
            merged_from_guest_id=secondary.id,
            note=f"归并档案 #{secondary.id} 姓名",
        ):
            added.append(sec_name)
    for row in list(db.query(GuestAlias).filter_by(guest_id=secondary.id).all()):
        if add_guest_alias(
            db,
            primary.id,
            row.alias_name,
            source=row.source or "merge",
            merged_from_guest_id=row.merged_from_guest_id or secondary.id,
            note=row.note,
        ):
            added.append(row.alias_name)
        db.delete(row)
    secondary.merged_into_guest_id = primary.id
    return added


def merge_vip_level(primary: Guest, secondary: Guest) -> None:
    p = VIP_RANK.get((primary.vip_level or "normal").lower(), 0)
    s = VIP_RANK.get((secondary.vip_level or "normal").lower(), 0)
    if s > p:
        primary.vip_level = secondary.vip_level
