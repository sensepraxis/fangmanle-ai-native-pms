# SPDX-License-Identifier: Apache-2.0
"""
将酒店房间收敛为 1–2 楼（每层 12 间），与房态看板 / 房务任务一致。

历史种子为 3–12 楼共 120 间。房态看板若误用房号首字符，0301 会显示成「0 楼」、
1001 会显示成「1 楼」，而房务任务按 Room.floor 能看到 3F–12F，两边不一致。
本迁移：保留最低两层物理房，重编号为 01xx/02xx，删除其余楼层房间及相关清扫单。
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models import (
    AssetAlert,
    HousekeepingTask,
    Linen,
    PmsCheckin,
    PmsGroupRoomLine,
    PmsRoomAssignment,
    Reservation,
    Room,
    RoomInspection,
    RoomIotMetric,
    RoomNightInventory,
    RoomStatusLog,
    ServiceRequest,
    StaffShift,
    SupplyAlert,
)


def _infer_floor(room: Room) -> int | None:
    if room.floor is not None and int(room.floor) > 0:
        return int(room.floor)
    digits = "".join(ch for ch in (room.room_no or "") if ch.isdigit())
    if len(digits) >= 4:
        fl = int(digits[:2])
        return fl if fl > 0 else None
    if len(digits) >= 3:
        fl = int(digits[0])
        return fl if fl > 0 else None
    return None


def _rewrite_shift_note(note: str, max_floors: int = 2) -> str:
    s = note or ""
    if not s:
        return s
    s2 = re.sub(r"\d+\s*[-~～至到]\s*\d+\s*[楼層Ff]", "1-2 楼", s)
    if max_floors <= 1:
        s2 = re.sub(r"\d+\s*[-~～至到]\s*\d+\s*[楼層Ff]", "1 楼", s)

    def _one(m: re.Match) -> str:
        n = int(m.group(1))
        if n > max_floors:
            return f"{max_floors} 楼"
        return m.group(0)

    s2 = re.sub(r"(?<!\d)(\d{1,2})\s*[楼層Ff]", _one, s2)
    if "VIP" in s2 and "楼" in s2:
        s2 = s2.replace("VIP 楼层", f"{max_floors} 楼优先")
    return s2


def ensure_compact_demo_floors(db: Session, hotel_id: int = 1, max_floors: int = 2) -> dict:
    rooms = db.query(Room).filter_by(hotel_id=hotel_id).order_by(Room.floor.asc(), Room.room_no.asc()).all()
    if not rooms:
        return {"skipped": True, "reason": "no rooms"}

    inferred = [(r, _infer_floor(r)) for r in rooms]
    floors = sorted({fl for _, fl in inferred if fl is not None})
    if not floors:
        return {"skipped": True, "reason": "no floor numbers"}

    already_compact = (
        len(floors) <= max_floors
        and max(floors) <= max_floors
        and floors == list(range(1, len(floors) + 1))
        and len(rooms) <= max_floors * 12
    )
    if already_compact:
        return {"skipped": True, "floors": floors, "rooms": len(rooms)}

    keep_src = floors[:max_floors]
    floor_map = {src: i + 1 for i, src in enumerate(keep_src)}  # e.g. 3→1, 4→2
    keep_ids = {r.id for r, fl in inferred if fl in keep_src}
    drop_ids = [r.id for r, fl in inferred if r.id not in keep_ids]

    hk_del = sr_del = inv_del = log_del = insp_del = linen_del = 0
    if drop_ids:
        hk_del = (
            db.query(HousekeepingTask).filter(HousekeepingTask.room_id.in_(drop_ids)).delete(synchronize_session=False)
        ) or 0
        sr_del = (
            db.query(ServiceRequest).filter(ServiceRequest.room_id.in_(drop_ids)).delete(synchronize_session=False)
        ) or 0
        inv_del = (
            db.query(RoomNightInventory)
            .filter(RoomNightInventory.room_id.in_(drop_ids))
            .delete(synchronize_session=False)
        ) or 0
        log_del = (
            db.query(RoomStatusLog).filter(RoomStatusLog.room_id.in_(drop_ids)).delete(synchronize_session=False)
        ) or 0
        insp_del = (
            db.query(RoomInspection).filter(RoomInspection.room_id.in_(drop_ids)).delete(synchronize_session=False)
        ) or 0
        linen_del = (db.query(Linen).filter(Linen.room_id.in_(drop_ids)).delete(synchronize_session=False)) or 0
        db.query(Reservation).filter(Reservation.room_id.in_(drop_ids)).update(
            {Reservation.room_id: None}, synchronize_session=False
        )
        db.query(PmsCheckin).filter(PmsCheckin.room_id.in_(drop_ids)).update(
            {PmsCheckin.room_id: None}, synchronize_session=False
        )
        db.query(PmsGroupRoomLine).filter(PmsGroupRoomLine.room_id.in_(drop_ids)).update(
            {PmsGroupRoomLine.room_id: None}, synchronize_session=False
        )
        db.query(PmsRoomAssignment).filter(PmsRoomAssignment.from_room_id.in_(drop_ids)).update(
            {PmsRoomAssignment.from_room_id: None}, synchronize_session=False
        )
        db.query(PmsRoomAssignment).filter(PmsRoomAssignment.to_room_id.in_(drop_ids)).update(
            {PmsRoomAssignment.to_room_id: None}, synchronize_session=False
        )
        for r, _fl in inferred:
            if r.id in keep_ids:
                continue
            db.delete(r)

    # 先改临时房号，避免 unique(hotel_id, room_no) 冲突
    original_no = {r.id: r.room_no for r, _fl in inferred}
    original_fl = {r.id: fl for r, fl in inferred}
    keep_rooms = [r for r, fl in inferred if r.id in keep_ids]
    for r in keep_rooms:
        r.room_no = f"__tmp_{r.id}"
    db.flush()

    renamed = 0
    used_nos: set[str] = set()
    for r in keep_rooms:
        src_fl = original_fl.get(r.id)
        new_floor = floor_map.get(src_fl) or 1
        digits = "".join(ch for ch in (original_no.get(r.id) or "") if ch.isdigit())
        seq = digits[-2:] if len(digits) >= 2 else f"{(r.id % 12) + 1:02d}"
        new_no = f"{new_floor:02d}{seq}"
        if new_no in used_nos:
            for n in range(1, 99):
                cand = f"{new_floor:02d}{n:02d}"
                if cand not in used_nos:
                    new_no = cand
                    break
        used_nos.add(new_no)
        r.floor = new_floor
        r.room_no = new_no
        renamed += 1

    note_fix = 0
    for s in db.query(StaffShift).filter_by(hotel_id=hotel_id).all():
        note = s.handover_note or ""
        rewritten = _rewrite_shift_note(note, max_floors=max_floors)
        if rewritten != note:
            s.handover_note = rewritten
            note_fix += 1

    # IoT / 资产告警楼层文案随房间收敛
    iot_fix = 0
    src_to_label = {src: f"{dst}F" for src, dst in floor_map.items()}
    for m in list(db.query(RoomIotMetric).filter_by(hotel_id=hotel_id).all()):
        lab = (m.floor or "").strip()
        mm = re.match(r"(\d+)", lab)
        num = int(mm.group(1)) if mm else None
        if num in src_to_label:
            if lab != src_to_label[num]:
                m.floor = src_to_label[num]
                iot_fix += 1
        elif num is not None:
            db.delete(m)
            iot_fix += 1

    alert_fix = 0
    for a in list(db.query(AssetAlert).filter_by(hotel_id=hotel_id).all()) + list(
        db.query(SupplyAlert).filter_by(hotel_id=hotel_id).all()
    ):
        lab = (a.floor or "").strip()
        mm = re.match(r"(\d+)", lab)
        if not mm:
            continue
        num = int(mm.group(1))
        if num in src_to_label and lab != src_to_label[num]:
            a.floor = src_to_label[num]
            alert_fix += 1
        elif num > max_floors:
            a.floor = f"{max_floors}F"
            alert_fix += 1

    db.flush()
    left = db.query(Room).filter_by(hotel_id=hotel_id).count()
    return {
        "skipped": False,
        "kept_src_floors": keep_src,
        "floor_map": floor_map,
        "dropped_rooms": len(drop_ids),
        "hk_deleted": int(hk_del or 0),
        "sr_deleted": int(sr_del or 0),
        "inv_deleted": int(inv_del or 0),
        "log_deleted": int(log_del or 0),
        "insp_deleted": int(insp_del or 0),
        "linen_deleted": int(linen_del or 0),
        "renamed": renamed,
        "note_fix": note_fix,
        "iot_fix": iot_fix,
        "alert_fix": alert_fix,
        "rooms_left": left,
    }
