# SPDX-License-Identifier: Apache-2.0
"""finance.night_audit subdomain routes — 薄 HTTP 层。"""

from __future__ import annotations

from routers.finance._common import (
    APIRouter,
    AppContext,
    Depends,
    Session,
    assert_hotel_access,
    date,
    datetime,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["finance"])


@router.post("/night-audit")
def night_audit(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.finance import run_night_audit

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    biz_date = datetime.strptime(payload.get("biz_date", date.today().isoformat()), "%Y-%m-%d").date()
    return ok(run_night_audit(db, hotel_id, biz_date, force=bool(payload.get("force"))))


@router.get("/night-audit/list")
def list_audits(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import list_night_audits

    return ok(list_night_audits(db, hotel_id))


@router.get("/night-audit/{hotel_id}/{biz_date}")
def audit_detail(
    biz_date: str,
    hotel_id: int,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import get_night_audit_detail

    hotel_id = assert_hotel_access(hotel_id)
    return ok(get_night_audit_detail(db, hotel_id, biz_date))
