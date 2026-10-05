# SPDX-License-Identifier: Apache-2.0
"""夜审流水线 · Template Method。

固定步骤：日租入账 → 房态翻转 → 证件清理 → 汇总写库 → emit。
子类/钩子可覆盖单步，而不改编排顺序。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api_common import row_to_dict
from events import emit
from models import NightAuditLog, Order, Payment


@dataclass
class NightAuditContext:
    db: Session
    hotel_id: int
    biz_date: date
    force: bool = False
    room_post: Any = None
    room_flip: Any = None
    id_purged: int = 0
    log_row: Optional[NightAuditLog] = None
    skipped_summary: bool = False
    result: dict[str, Any] = field(default_factory=dict)


class NightAuditPipeline:
    """模板方法：``run()`` 固定顺序调用各步。"""

    def run(self, ctx: NightAuditContext) -> dict[str, Any]:
        try:
            self.step_post_room_charges(ctx)
            self.step_flip_rooms(ctx)
            self.step_purge_id_docs(ctx)
            self.step_summarize_or_skip(ctx)
            if not ctx.skipped_summary:
                self.step_persist_log(ctx)
            self.step_commit(ctx)
            self.step_emit(ctx)
            return ctx.result
        except Exception:
            ctx.db.rollback()
            raise

    def step_post_room_charges(self, ctx: NightAuditContext) -> None:
        from orders.pms_ops import post_night_audit_room_charges

        ctx.room_post = post_night_audit_room_charges(ctx.db, ctx.hotel_id, ctx.biz_date)

    def step_flip_rooms(self, ctx: NightAuditContext) -> None:
        from rooms.room_ops import night_audit_room_flip

        ctx.room_flip = night_audit_room_flip(ctx.db, ctx.hotel_id, ctx.biz_date)

    def step_purge_id_docs(self, ctx: NightAuditContext) -> None:
        from infra.compliance import purge_expired_id_docs

        ctx.id_purged = purge_expired_id_docs(ctx.db)

    def step_summarize_or_skip(self, ctx: NightAuditContext) -> None:
        existing = ctx.db.query(NightAuditLog).filter_by(hotel_id=ctx.hotel_id, biz_date=ctx.biz_date).first()
        if existing and existing.status == "passed" and not ctx.force:
            ctx.skipped_summary = True
            ctx.log_row = existing
            d = row_to_dict(existing)
            d["room_charges"] = ctx.room_post
            d["room_flip"] = ctx.room_flip
            d["id_docs_purged"] = ctx.id_purged
            ctx.result = d
            return
        ctx.log_row = existing
        ctx.skipped_summary = False

    def step_persist_log(self, ctx: NightAuditContext) -> None:
        biz_date = ctx.biz_date
        day_start = datetime(biz_date.year, biz_date.month, biz_date.day)
        day_end = day_start + timedelta(days=1)
        rev = (
            ctx.db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter_by(hotel_id=ctx.hotel_id)
            .filter(Payment.paid_at >= day_start, Payment.paid_at < day_end)
            .scalar()
        )
        nights = (
            ctx.db.query(func.coalesce(func.sum(Order.rooms), 0))
            .filter_by(hotel_id=ctx.hotel_id, status="checked_out", check_out=biz_date)
            .scalar()
        )
        exceptions = ctx.db.query(Order).filter_by(hotel_id=ctx.hotel_id, status="no_show").count()
        existing = ctx.log_row
        if existing:
            existing.status = "passed"
            existing.revenue = float(rev or 0)
            existing.room_nights = int(nights or 0)
            existing.exceptions = exceptions
            existing.ran_at = datetime.now()
        else:
            existing = NightAuditLog(
                hotel_id=ctx.hotel_id,
                biz_date=biz_date,
                status="passed",
                revenue=float(rev or 0),
                room_nights=int(nights or 0),
                exceptions=exceptions,
                ran_at=datetime.now(),
            )
            ctx.db.add(existing)
        ctx.log_row = existing
        d = row_to_dict(existing)
        d["room_charges"] = ctx.room_post
        d["room_flip"] = ctx.room_flip
        d["id_docs_purged"] = ctx.id_purged
        ctx.result = d

    def step_commit(self, ctx: NightAuditContext) -> None:
        ctx.db.commit()

    def step_emit(self, ctx: NightAuditContext) -> None:
        payload: dict[str, Any] = {
            "hotel_id": ctx.hotel_id,
            "biz_date": ctx.biz_date.isoformat(),
            "force": bool(ctx.force),
        }
        if ctx.skipped_summary:
            payload["skipped_summary"] = True
        else:
            payload["revenue"] = ctx.result.get("revenue")
            payload["room_nights"] = ctx.result.get("room_nights")
            payload["exceptions"] = ctx.result.get("exceptions")
        emit("night_audit.completed", payload)


def run_night_audit_pipeline(
    db: Session,
    hotel_id: int,
    biz_date: date,
    *,
    force: bool = False,
    pipeline: Optional[NightAuditPipeline] = None,
) -> dict[str, Any]:
    pipe = pipeline or NightAuditPipeline()
    ctx = NightAuditContext(db=db, hotel_id=hotel_id, biz_date=biz_date, force=force)
    return pipe.run(ctx)


__all__ = [
    "NightAuditContext",
    "NightAuditPipeline",
    "run_night_audit_pipeline",
]
