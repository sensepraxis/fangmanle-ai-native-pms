# SPDX-License-Identifier: Apache-2.0
"""AI 问数：会话表 + 追问字段。"""

from __future__ import annotations

from sqlalchemy import inspect, text

from models import AiAskQuery, AiAskSession, Base

_ASK_QUERY_COLS = {
    "parent_query_id": "INTEGER",
    "resolved_question": "TEXT",
    "normalized_question": "TEXT",
    "metric_id": "VARCHAR(64)",
    "operator_id": "VARCHAR(32)",
    "playbook_tips": "TEXT",
    "pii_accessed": "BOOLEAN DEFAULT FALSE",
    "pii_ack_by": "VARCHAR(40)",
    "pii_ack_at": "TIMESTAMP",
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


def ensure_ai_ask_schema(engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    for model in (AiAskSession, AiAskQuery):
        if model.__tablename__ not in tables:
            need.append(model.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)
    _ensure_columns(engine, "ai_ask_queries", _ASK_QUERY_COLS)
