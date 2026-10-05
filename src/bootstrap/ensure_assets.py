# SPDX-License-Identifier: Apache-2.0
"""旧库补齐设备设施相关列（PostgreSQL）。新表由 create_all 创建。"""

from sqlalchemy import inspect, text

ASSET_COLS = {
    "asset_no": "VARCHAR(40)",
    "room_no": "VARCHAR(20)",
    "sn": "VARCHAR(60)",
    "brand_model": "VARCHAR(80)",
    "repair_cost_total": "NUMERIC(12, 2)",
    "health_score": "INTEGER",
    "insight": "VARCHAR(200)",
    "warranty_until": "DATE",
    "runtime_hours": "INTEGER",
    "avg_power_w": "NUMERIC(10, 2)",
    "next_maintain_date": "DATE",
    "supplier": "VARCHAR(80)",
    "dept": "VARCHAR(40)",
}

MAINT_COLS = {
    "note": "VARCHAR(200)",
    "owner": "VARCHAR(40)",
    "completed_at": "TIMESTAMP",
}


def _backfill_asset_no(conn, engine):
    """为旧数据补齐设备编号：优先沿用 sn，否则按 id 生成。

    PostgreSQL 用 LPAD（CAST AS TEXT），SQLite 没 LPAD，用 printf('%05d', id)。
    """
    conn.execute(
        text(
            "UPDATE assets SET asset_no = sn WHERE (asset_no IS NULL OR asset_no = '') AND sn IS NOT NULL AND sn != ''"
        )
    )
    if engine.dialect.name == "postgresql":
        conn.execute(
            text(
                "UPDATE assets SET asset_no = 'EQ-' || LPAD(CAST(id AS TEXT), 5, '0') "
                "WHERE asset_no IS NULL OR asset_no = ''"
            )
        )
    else:
        # SQLite / 其他：printf('%05d', id) 输出 5 位前导零数字
        conn.execute(
            text("UPDATE assets SET asset_no = 'EQ-' || printf('%05d', id) WHERE asset_no IS NULL OR asset_no = ''")
        )


def ensure_asset_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    added_asset_no = False
    with engine.begin() as conn:
        insp_conn = inspect(conn)
        if "assets" in tables:
            cols = {c["name"] for c in insp_conn.get_columns("assets")}
            for name, ddl in ASSET_COLS.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE assets ADD COLUMN {name} {ddl}"))
                    if name == "asset_no":
                        added_asset_no = True
            if added_asset_no or "asset_no" in cols:
                _backfill_asset_no(conn, engine)
        if "asset_maintenance" in tables:
            cols = {c["name"] for c in insp_conn.get_columns("asset_maintenance")}
            for name, ddl in MAINT_COLS.items():
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE asset_maintenance ADD COLUMN {name} {ddl}"))
