# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""去掉 mkt_coupon_grants 上 (coupon_id, guest_id) 唯一约束，改由 per_user_qty / 业务限领控制。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


def ensure_drop_grant_guest_unique(engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("mkt_coupon_grants"):
        return
    # Postgres / 其他：尝试 drop constraint（不存在则忽略）
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE mkt_coupon_grants DROP CONSTRAINT IF EXISTS uk_mkt_coupon_guest"))
        except Exception:
            pass


def run(db: Session | None = None) -> None:
    from database import engine

    ensure_drop_grant_guest_unique(engine)
