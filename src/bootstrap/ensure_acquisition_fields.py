# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""获客线索 / 绑定表字段增量迁移（幂等 ALTER）。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

LEAD_COLUMNS = {
    "lead_type": "VARCHAR(20)",
    "wechat": "VARCHAR(80)",
    "source_note_url": "VARCHAR(500)",
    "xhs_plan_id": "VARCHAR(80)",
    "xhs_creative_id": "VARCHAR(80)",
    "xhs_unit_id": "VARCHAR(80)",
    "payload_type": "VARCHAR(40)",
    "campaign_json": "TEXT",
}

BINDING_COLUMNS = {
    "xhs_page_ids": "VARCHAR(255)",
}

CAMPAIGN_COLUMNS = {
    "external_plan_id": "VARCHAR(80)",
}


def _add_columns(engine: Engine, table: str, columns: dict[str, str]) -> int:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return 0
    existing = {c["name"] for c in insp.get_columns(table)}
    added = 0
    with engine.begin() as conn:
        for name, col_type in columns.items():
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"))
            added += 1
    return added


def ensure_acquisition_fields(engine: Engine) -> dict:
    return {
        "lead_cols": _add_columns(engine, "acquisition_leads", LEAD_COLUMNS),
        "binding_cols": _add_columns(engine, "hotel_channel_bindings", BINDING_COLUMNS),
        "campaign_cols": _add_columns(engine, "campaigns", CAMPAIGN_COLUMNS),
    }
