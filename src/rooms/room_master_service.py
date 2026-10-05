# SPDX-License-Identifier: Apache-2.0
"""房间档案 / 房型台账 CRUD（从 Fat Controller 下沉）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api_common import row_to_dict
from domain import ConflictError, InvalidStateError, NotFoundError, ValidationError
from models import Order, Reservation, Room, RoomType
from rooms.room_board_service import (
    _dump_feature_tags,
    _normalize_physical_status,
    _parse_feature_tags,
    _room_master_dict,
)
from rooms.room_status import DO, EA, OCC, VC, normalize


def list_room_masters(
    db: Session,
    hotel_id: int,
    *,
    room_type_id: Optional[int] = None,
    q: Optional[str] = None,
) -> list[dict]:
    query = (
        db.query(Room, RoomType).outerjoin(RoomType, Room.room_type_id == RoomType.id).filter(Room.hotel_id == hotel_id)
    )
    if room_type_id:
        query = query.filter(Room.room_type_id == int(room_type_id))
    kw = (q or "").strip()
    if kw:
        like = f"%{kw}%"
        query = query.filter((Room.room_no.ilike(like)) | (Room.lock_id.ilike(like)))
    rows = query.order_by(Room.floor.asc(), Room.room_no.asc()).all()
    return [_room_master_dict(db, r, rt) for r, rt in rows]


def create_room_master(db: Session, hotel_id: int, payload: dict) -> dict:
    room_no = (payload.get("room_no") or "").strip()
    if not room_no:
        raise ValidationError("房号必填")
    exists = db.query(Room).filter_by(hotel_id=hotel_id, room_no=room_no).first()
    if exists:
        raise ConflictError("房号已存在")
    rt_id = payload.get("room_type_id")
    if rt_id:
        rt = db.get(RoomType, int(rt_id))
        if not rt or rt.hotel_id != hotel_id:
            raise ValidationError("房型无效")

    tags = payload.get("feature_tags") if "feature_tags" in payload else payload.get("features")
    tags = _parse_feature_tags(tags)
    smoking = bool(payload.get("smoking", False))
    if "可吸烟" in tags:
        smoking = True
        tags = [t for t in tags if t not in ("无烟", "可吸烟")]
    elif "无烟" in tags:
        smoking = False
        tags = [t for t in tags if t not in ("无烟", "可吸烟")]

    lock_id = (payload.get("lock_id") or "").strip() or f"LOCK-{room_no}"
    r = Room(
        hotel_id=hotel_id,
        room_no=room_no,
        room_type_id=int(rt_id) if rt_id else None,
        building=(payload.get("building") or "").strip() or None,
        floor=int(payload["floor"]) if payload.get("floor") is not None and str(payload.get("floor")) != "" else None,
        status=VC,
        smoking=smoking,
        features=_dump_feature_tags(tags),
        lock_id=lock_id,
        physical_status=_normalize_physical_status(payload.get("physical_status")),
    )
    db.add(r)
    db.flush()
    db.refresh(r)
    return _room_master_dict(db, r)


def update_room_master(db: Session, room_id: int, payload: dict) -> dict:
    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("房间不存在")
    if "room_no" in payload and payload["room_no"]:
        new_no = str(payload["room_no"]).strip()
        clash = db.query(Room).filter(Room.hotel_id == r.hotel_id, Room.room_no == new_no, Room.id != r.id).first()
        if clash:
            raise ConflictError("房号已存在")
        r.room_no = new_no
    if "room_type_id" in payload:
        rt_id = payload.get("room_type_id")
        if rt_id in (None, "", 0, "0"):
            r.room_type_id = None
        else:
            rt = db.get(RoomType, int(rt_id))
            if not rt or rt.hotel_id != r.hotel_id:
                raise ValidationError("房型无效")
            r.room_type_id = rt.id
    if "building" in payload:
        r.building = str(payload.get("building") or "").strip() or None
    if "floor" in payload:
        fv = payload.get("floor")
        r.floor = int(fv) if fv is not None and str(fv) != "" else None
    if "lock_id" in payload:
        r.lock_id = str(payload.get("lock_id") or "").strip() or None
    if "physical_status" in payload:
        r.physical_status = _normalize_physical_status(payload.get("physical_status"))
    if "feature_tags" in payload or "features" in payload or "smoking" in payload:
        tags = payload.get("feature_tags") if "feature_tags" in payload else payload.get("features")
        tags = _parse_feature_tags(tags if tags is not None else r.features)
        smoking = bool(payload["smoking"]) if "smoking" in payload else bool(r.smoking)
        if "可吸烟" in tags:
            smoking = True
            tags = [t for t in tags if t not in ("无烟", "可吸烟")]
        elif "无烟" in tags:
            smoking = False
            tags = [t for t in tags if t not in ("无烟", "可吸烟")]
        r.smoking = smoking
        r.features = _dump_feature_tags(tags)
    db.flush()
    db.refresh(r)
    return _room_master_dict(db, r)


def delete_room_master(db: Session, room_id: int) -> dict:
    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("房间不存在")
    st = normalize(r.status)
    if st in (OCC, EA, DO):
        raise InvalidStateError("房间当前占用中，无法删除档案")
    busy = (
        db.query(Reservation)
        .join(Order, Reservation.order_id == Order.id)
        .filter(
            Reservation.room_id == r.id,
            Order.status.in_(("pending", "confirmed", "checked_in")),
        )
        .first()
    )
    if busy:
        raise InvalidStateError("房间仍有有效订单占用，无法删除")
    db.delete(r)
    db.flush()
    return {"deleted": True, "id": room_id}


def list_room_types(db: Session, hotel_id: int) -> list[dict]:
    from bootstrap.ensure_room_types import _derive_amenities, _derive_area, dump_amenities, parse_amenities

    types = db.query(RoomType).filter_by(hotel_id=hotel_id).order_by(RoomType.id).all()
    counts = dict(
        db.query(Room.room_type_id, func.count(Room.id))
        .filter(Room.hotel_id == hotel_id)
        .group_by(Room.room_type_id)
        .all()
    )
    out = []
    for rt in types:
        # 兼容旧行：缺字段时回填（facade 见 session.dirty 后 commit）
        if rt.area is None:
            rt.area = _derive_area(rt)
        if not (rt.amenities or "").strip():
            rt.amenities = dump_amenities(_derive_amenities(rt))
        d = row_to_dict(rt)
        d["room_count"] = int(counts.get(rt.id) or 0)
        d["linked_rooms"] = d["room_count"]
        d["bed"] = rt.bed_type or "标准床型"
        d["tags"] = parse_amenities(rt.amenities)
        out.append(d)
    return out


def create_room_type(db: Session, hotel_id: int, payload: dict) -> dict:
    from bootstrap.ensure_room_types import dump_amenities, parse_amenities

    code = (payload.get("code") or "").strip()
    name = (payload.get("name") or "").strip()
    if not code or not name:
        raise ValidationError("code 与 name 必填")
    exists = db.query(RoomType).filter_by(hotel_id=hotel_id, code=code).first()
    if exists:
        raise ConflictError("房型代码已存在")
    tags = parse_amenities(payload.get("tags") or payload.get("amenities"))
    bf = bool(payload.get("breakfast_included")) or ("含早" in tags)
    has_window = payload.get("has_window")
    if has_window is None:
        has_window = True
    rt = RoomType(
        hotel_id=hotel_id,
        code=code,
        name=name,
        bed_type=(payload.get("bed") or payload.get("bed_type") or "标准床型"),
        capacity=int(payload.get("capacity") or 2),
        area=int(payload.get("area") or 28),
        amenities=dump_amenities(tags or ["标准配置"]),
        base_price=float(payload.get("base_price") or 0),
        breakfast_included=bf,
        is_active=bool(payload.get("is_active", True)),
        description=(payload.get("description") or "").strip() or None,
        image_url=(payload.get("image_url") or "").strip() or None,
        has_window=bool(has_window),
        orientation=(payload.get("orientation") or "").strip() or None,
    )
    db.add(rt)
    db.flush()
    db.refresh(rt)
    d = row_to_dict(rt)
    d["bed"] = rt.bed_type
    d["tags"] = parse_amenities(rt.amenities)
    d["room_count"] = 0
    d["linked_rooms"] = 0
    return d


def update_room_type(db: Session, type_id: int, payload: dict) -> dict:
    from bootstrap.ensure_room_types import dump_amenities, parse_amenities

    rt = db.get(RoomType, type_id)
    if not rt:
        raise NotFoundError("房型不存在")
    if "name" in payload and payload["name"]:
        rt.name = str(payload["name"]).strip()
    if "code" in payload and payload["code"]:
        new_code = str(payload["code"]).strip()
        clash = (
            db.query(RoomType)
            .filter(RoomType.hotel_id == rt.hotel_id, RoomType.code == new_code, RoomType.id != rt.id)
            .first()
        )
        if clash:
            raise ConflictError("房型代码已存在")
        rt.code = new_code
    if "bed" in payload or "bed_type" in payload:
        rt.bed_type = str(payload.get("bed") or payload.get("bed_type") or rt.bed_type or "").strip()
    if "area" in payload and payload["area"] is not None:
        rt.area = int(payload["area"])
    if "capacity" in payload and payload["capacity"] is not None:
        rt.capacity = int(payload["capacity"])
    if "base_price" in payload and payload["base_price"] is not None:
        rt.base_price = float(payload["base_price"])
    if "tags" in payload or "amenities" in payload:
        tags = parse_amenities(payload.get("tags") if "tags" in payload else payload.get("amenities"))
        rt.amenities = dump_amenities(tags)
        rt.breakfast_included = "含早" in tags
    if "breakfast_included" in payload:
        rt.breakfast_included = bool(payload["breakfast_included"])
    if "is_active" in payload:
        rt.is_active = bool(payload["is_active"])
    if "description" in payload:
        rt.description = str(payload.get("description") or "").strip() or None
    if "image_url" in payload:
        rt.image_url = str(payload.get("image_url") or "").strip() or None
    if "has_window" in payload:
        rt.has_window = bool(payload["has_window"])
    if "orientation" in payload:
        rt.orientation = str(payload.get("orientation") or "").strip() or None
    db.flush()
    db.refresh(rt)
    cnt = db.query(func.count(Room.id)).filter(Room.room_type_id == rt.id).scalar() or 0
    d = row_to_dict(rt)
    d["bed"] = rt.bed_type
    d["tags"] = parse_amenities(rt.amenities)
    d["room_count"] = int(cnt)
    d["linked_rooms"] = int(cnt)
    return d


def delete_room_type(db: Session, type_id: int) -> dict:
    rt = db.get(RoomType, type_id)
    if not rt:
        raise NotFoundError("房型不存在")
    cnt = db.query(func.count(Room.id)).filter(Room.room_type_id == rt.id).scalar() or 0
    if int(cnt) > 0:
        raise InvalidStateError(f"仍有 {cnt} 间关联房间，请先在「房间档案」中改绑或删除后再删房型")
    db.delete(rt)
    db.flush()
    return {"deleted": True, "id": type_id}


def room_detail_bundle(db: Session, room_id: int) -> dict:
    from models import HousekeepingTask, RoomStatusLog

    r = db.get(Room, room_id)
    if not r:
        raise NotFoundError("room not found")
    rt = db.get(RoomType, r.room_type_id) if r.room_type_id else None
    logs = [
        row_to_dict(l)
        for l in db.query(RoomStatusLog).filter_by(room_id=r.id).order_by(RoomStatusLog.id.desc()).limit(20)
    ]
    tasks = [
        dict(row_to_dict(t), room_no=r.room_no)
        for t, rn in db.query(HousekeepingTask, Room.room_no)
        .join(Room, HousekeepingTask.room_id == Room.id)
        .filter(HousekeepingTask.room_id == r.id)
        .all()
    ]
    d = row_to_dict(r)
    d["room_type_name"] = rt.name if rt else ""
    d["status_log"] = logs
    d["housekeeping"] = tasks
    return d
