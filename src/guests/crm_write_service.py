# SPDX-License-Identifier: Apache-2.0
"""客人域写操作：标签 / 分群删除 / CRM 任务完结（从 Fat Controller 下沉）。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import ConflictError, NotFoundError, ValidationError
from models import CrmTask, Guest, GuestTag, Segment, SegmentMember, TagDefinition


def delete_guest_segment(db: Session, hotel_id: int, segment_id: int) -> dict:
    from bootstrap.ensure_member_crm import mark_segment_deleted

    seg = db.get(Segment, segment_id)
    if not seg or seg.hotel_id != hotel_id:
        raise NotFoundError("分群不存在")
    name = seg.name or ""
    db.query(SegmentMember).filter_by(segment_id=seg.id).delete(synchronize_session=False)
    mark_segment_deleted(db, hotel_id, name)
    db.delete(seg)
    db.flush()
    return {"id": segment_id, "name": name, "deleted": True}


def complete_crm_task(db: Session, hotel_id: int, task_id: int) -> dict:
    t = db.get(CrmTask, task_id)
    if not t or t.hotel_id != hotel_id:
        raise NotFoundError("任务不存在")
    t.status = "done"
    t.done_at = datetime.utcnow()
    db.flush()
    return row_to_dict(t)


def create_tag_definition(
    db: Session,
    *,
    name: str,
    code: Optional[str] = None,
    category: Optional[str] = None,
    rule_expr: Optional[str] = None,
    is_active: bool = True,
) -> dict:
    from bootstrap.ensure_crm_extended import ensure_crm_extended

    ensure_crm_extended(db)
    code_v = (code or name).strip().replace(" ", "_")[:40]
    if not name or not name.strip():
        raise ValidationError("标签名称必填")
    if db.query(TagDefinition).filter_by(code=code_v).first():
        raise ConflictError("标签 code 已存在")
    row = TagDefinition(
        code=code_v,
        name=name.strip(),
        category=category or "画像",
        rule_expr=rule_expr or "",
        is_active=is_active,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row_to_dict(row)


def update_tag_definition(
    db: Session,
    tag_id: int,
    *,
    name: str,
    category: Optional[str] = None,
    rule_expr: Optional[str] = None,
    is_active: bool = True,
) -> dict:
    row = db.get(TagDefinition, tag_id)
    if not row:
        raise NotFoundError("标签不存在")
    row.name = name.strip() or row.name
    if category is not None:
        row.category = category
    if rule_expr is not None:
        row.rule_expr = rule_expr
    row.is_active = is_active
    db.flush()
    return row_to_dict(row)


def apply_tag_to_hotel_guests(db: Session, hotel_id: int, tag_id: int) -> dict:
    from bootstrap.ensure_member_crm import _guest_tag_codes, _hotel_guest_ids
    from guests.crm_defaults import match_rule_extended

    row = db.get(TagDefinition, tag_id)
    if not row:
        raise NotFoundError("标签不存在")
    gids = _hotel_guest_ids(db, hotel_id)
    guests = db.query(Guest).filter(Guest.id.in_(gids)).all() if gids else db.query(Guest).limit(120).all()
    tag_map = _guest_tag_codes(db, [g.id for g in guests])
    hit = 0
    for g in guests:
        if not match_rule_extended(g, tag_map.get(g.id, set()), row.rule_expr or ""):
            continue
        exists = db.query(GuestTag).filter_by(guest_id=g.id, tag_id=row.id).first()
        if not exists:
            db.add(GuestTag(guest_id=g.id, tag_id=row.id, confidence=0.92, source="rule"))
            hit += 1
    db.flush()
    return {"tag_id": tag_id, "applied": hit}
