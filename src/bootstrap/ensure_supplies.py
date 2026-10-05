# SPDX-License-Identifier: Apache-2.0
"""旧库补齐报损登记相关列（PostgreSQL）。新表由 create_all 创建。"""

from sqlalchemy import inspect, text

DAMAGE_COLS = {
    "asset_category": "VARCHAR(80)",
    "severity": "VARCHAR(20)",
    "description": "TEXT",
    "photos": "TEXT",
    "ai_suggestion": "TEXT",
    "ai_risk": "TEXT",
    "ai_tags": "VARCHAR(200)",
}


def ensure_supplies_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        insp_conn = inspect(conn)
        if "damage_tickets" in tables:
            cols = {c["name"] for c in insp_conn.get_columns("damage_tickets")}
            for name, ddl in DAMAGE_COLS.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE damage_tickets ADD COLUMN {name} {ddl}"))
