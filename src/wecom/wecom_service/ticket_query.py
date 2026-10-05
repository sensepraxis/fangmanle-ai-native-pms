# SPDX-License-Identifier: Apache-2.0
"""企微只读查询辅助（票据查找等），供 application / router 调用。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models import WecomBindTicket


def get_bind_ticket_by_token(db: Session, token: str) -> Optional[WecomBindTicket]:
    """按 token 取绑定票据；无则返回 None。"""
    t = (token or "").strip()
    if not t:
        return None
    return db.query(WecomBindTicket).filter_by(token=t).first()


__all__ = ["get_bind_ticket_by_token"]
