# SPDX-License-Identifier: Apache-2.0
"""跨看板共用的只读 Query Object（开放客需等）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session

from models import Room, ServiceRequest

OPEN_SERVICE_STATUSES: tuple[str, ...] = ("open", "assigned", "in_progress")


@dataclass(frozen=True)
class OpenServiceRequestsQuery:
    """开放客需：hotel 维度 + 状态集合 + limit。"""

    hotel_id: int
    statuses: Sequence[str] = OPEN_SERVICE_STATUSES
    limit: int = 20
    order_desc: bool = False

    def all(self, db: Session) -> list[tuple[ServiceRequest, Optional[Room]]]:
        q = (
            db.query(ServiceRequest, Room)
            .outerjoin(Room, ServiceRequest.room_id == Room.id)
            .filter(
                ServiceRequest.hotel_id == self.hotel_id,
                ServiceRequest.status.in_(tuple(self.statuses)),
            )
        )
        if self.order_desc:
            q = q.order_by(ServiceRequest.priority.asc(), ServiceRequest.id.desc())
        else:
            q = q.order_by(ServiceRequest.priority.asc(), ServiceRequest.id.asc())
        return q.limit(self.limit).all()

    def as_dicts(self, db: Session) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sr, rm in self.all(db):
            out.append(
                {
                    "id": sr.id,
                    "room_id": sr.room_id,
                    "room_no": rm.room_no if rm else None,
                    "content": (sr.content or "")[:60],
                    "priority": sr.priority or 3,
                    "status": sr.status,
                    "assignee_id": sr.assignee_id,
                }
            )
        return out


__all__ = ["OPEN_SERVICE_STATUSES", "OpenServiceRequestsQuery"]
