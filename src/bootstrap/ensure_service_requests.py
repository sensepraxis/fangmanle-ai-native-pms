# SPDX-License-Identifier: Apache-2.0
"""旧库补齐客需工单责任人列。"""

from sqlalchemy import inspect, text


def ensure_service_request_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "service_requests" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("service_requests")}
    if "assignee_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE service_requests ADD COLUMN assignee_id INTEGER"))
