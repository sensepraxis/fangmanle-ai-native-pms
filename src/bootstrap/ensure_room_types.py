# SPDX-License-Identifier: Apache-2.0
"""room_types 补齐 area / amenities，并回填历史行。

amenities 解析 / 房型默认值 helper 已抽到 `rooms.amenities`；本文件保留启动期
schema 保活 + 历史行回填。
"""

import json

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models import RoomType
from rooms.amenities import _derive_amenities, _derive_area, dump_amenities, parse_amenities


def ensure_room_types_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "room_types" in tables:
        cols = {c["name"] for c in insp.get_columns("room_types")}
        with engine.begin() as conn:
            if "area" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN area INTEGER"))
            if "amenities" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN amenities TEXT"))
            if "description" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN description TEXT"))
            if "image_url" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN image_url VARCHAR(500)"))
            if "has_window" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN has_window BOOLEAN DEFAULT TRUE"))
            if "orientation" not in cols:
                conn.execute(text("ALTER TABLE room_types ADD COLUMN orientation VARCHAR(40)"))
    if "rooms" in tables:
        rcols = {c["name"] for c in insp.get_columns("rooms")}
        with engine.begin() as conn:
            if "smoking" not in rcols:
                conn.execute(text("ALTER TABLE rooms ADD COLUMN smoking BOOLEAN DEFAULT FALSE"))
            if "features" not in rcols:
                conn.execute(text("ALTER TABLE rooms ADD COLUMN features VARCHAR(200)"))
            if "lock_id" not in rcols:
                conn.execute(text("ALTER TABLE rooms ADD COLUMN lock_id VARCHAR(60)"))
            if "physical_status" not in rcols:
                conn.execute(text("ALTER TABLE rooms ADD COLUMN physical_status VARCHAR(20) DEFAULT 'normal'"))


def backfill_room_types(db: Session) -> int:
    """为空的 area/amenities 写入推导值；房间补 lock_id / physical_status。"""
    n = 0
    for rt in db.query(RoomType).all():
        changed = False
        if rt.area is None:
            rt.area = _derive_area(rt)
            changed = True
        if not (rt.amenities or "").strip():
            rt.amenities = dump_amenities(_derive_amenities(rt))
            changed = True
        if changed:
            n += 1
    from models import Room

    for r in db.query(Room).all():
        changed = False
        if not (getattr(r, "lock_id", None) or "").strip():
            r.lock_id = f"LOCK-{r.room_no}"
            changed = True
        if not (getattr(r, "physical_status", None) or "").strip():
            r.physical_status = "normal"
            changed = True
        if changed:
            n += 1
    if n:
        db.commit()
    return n
