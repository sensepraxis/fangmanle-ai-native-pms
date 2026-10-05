# SPDX-License-Identifier: Apache-2.0
"""订单模块重构：外部单号、团购券码字段。"""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_order_refactor_schema(engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("orders"):
        return
    cols = {c["name"] for c in insp.get_columns("orders")}
    alters: list[str] = []
    if "external_order_no" not in cols:
        alters.append("ALTER TABLE orders ADD COLUMN external_order_no VARCHAR(80)")
    if "voucher_code" not in cols:
        alters.append("ALTER TABLE orders ADD COLUMN voucher_code VARCHAR(80)")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))
