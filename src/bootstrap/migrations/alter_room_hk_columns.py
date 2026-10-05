# SPDX-License-Identifier: Apache-2.0
"""房态/房务 schema 增量：HK 查房字段 + 房态备注 + 标准码迁移。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

HK_TASK_COLS = [
    ("inspect_by", "INTEGER"),
    ("inspect_at", "TIMESTAMP"),
    ("fail_reason", "VARCHAR(200)"),
    ("fail_count", "SMALLINT DEFAULT 0"),
]

ROOM_META_COLS = [
    ("status_note", "VARCHAR(200)"),
    ("status_until", "DATE"),
]


def _add_cols(engine: Engine, table: str, cols: list[tuple[str, str]]) -> list[str]:
    added = []
    insp = inspect(engine)
    if not insp.has_table(table):
        return added
    existing = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for name, typ in cols:
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
            added.append(name)
    return added


def ensure_room_hk_schema(engine: Engine) -> dict:
    added = {
        "housekeeping_tasks": _add_cols(engine, "housekeeping_tasks", HK_TASK_COLS),
        "rooms": _add_cols(engine, "rooms", ROOM_META_COLS),
    }
    return added


def migrate_room_and_hk(db: Session, hotel_id: int = 1) -> dict:
    from models import Order, Reservation, Room
    from rooms.room_ops import mark_expected_arrival
    from rooms.room_status import EA, VC, migrate_room_statuses, normalize

    n = migrate_room_statuses(db, hotel_id=hotel_id)
    ea_fixed = 0
    # 已预分房但房态仍空净 → 纠正为预抵（房态-05 存量对齐）
    rows = (
        db.query(Reservation, Order, Room)
        .join(Order, Reservation.order_id == Order.id)
        .join(Room, Reservation.room_id == Room.id)
        .filter(
            Order.hotel_id == hotel_id,
            Order.status.in_(("pending", "confirmed")),
            Reservation.room_id.isnot(None),
        )
        .all()
    )
    for _res, _od, rm in rows:
        if normalize(rm.status) == VC:
            mark_expected_arrival(db, rm, reason="存量预分对齐·预抵")
            ea_fixed += 1
        elif normalize(rm.status) != EA:
            pass
    return {"rooms_status_migrated": n, "ea_aligned": ea_fixed}
