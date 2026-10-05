# SPDX-License-Identifier: Apache-2.0
"""班次交接：建表 + 接班扩展列。"""

from __future__ import annotations

from sqlalchemy import inspect, text

from models import (
    Base,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    ShiftReceiveDiff,
)

_HANDOVER_COLS = {
    "received_revenue_ok": "BOOLEAN DEFAULT FALSE",
    "deposit_ack": "BOOLEAN DEFAULT FALSE",
    "float_received_confirmed": "BOOLEAN DEFAULT FALSE",
    "assets_received_confirmed": "BOOLEAN DEFAULT FALSE",
    "matters_confirmed": "BOOLEAN DEFAULT FALSE",
    "received_float_actual": "NUMERIC(14, 2)",
    "received_float_match_outgoing": "BOOLEAN DEFAULT TRUE",
    "guest_situation_acks": "TEXT",
    "task_claims": "TEXT",
    "carryover_acks": "TEXT",
    "narrative": "TEXT",
    "ai_draft_json": "TEXT",
    "ai_approved_json": "TEXT",
    "guest_situations_snapshot": "TEXT",
    "ai_session_id": "VARCHAR(64)",
    "ai_draft_confirmed_at": "TIMESTAMP",
    "ai_draft_confirmed_by": "INTEGER",
}

_TASK_COLS = {
    "task_type": "VARCHAR(20) DEFAULT 'normal'",
    "created_by": "VARCHAR(40) DEFAULT 'manual'",
    "approved_by": "INTEGER",
    "ai_session_id": "VARCHAR(64)",
    "source": "VARCHAR(40)",
}

_DIFF_COLS = {
    "suggestion": "VARCHAR(20)",
}

_FLOAT_COLS = {
    "received_qty": "INTEGER",
}

_ASSET_COLS = {
    "received_qty": "INTEGER",
    "received_ack": "BOOLEAN DEFAULT FALSE",
}


def _ensure_columns(engine, table: str, cols: dict[str, str]) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for name, ddl in cols.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def ensure_shift_handover_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    for model in (
        ShiftHandover,
        ShiftFloatCount,
        ShiftAssetCount,
        ShiftHandoverTask,
        ShiftReceiveDiff,
        ShiftAuditLog,
    ):
        if model.__tablename__ not in tables:
            need.append(model.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)
    _ensure_columns(engine, "shift_handovers", _HANDOVER_COLS)
    _ensure_columns(engine, "shift_float_counts", _FLOAT_COLS)
    _ensure_columns(engine, "shift_asset_counts", _ASSET_COLS)
    _ensure_columns(engine, "shift_handover_tasks", _TASK_COLS)
    _ensure_columns(engine, "shift_receive_diffs", _DIFF_COLS)
