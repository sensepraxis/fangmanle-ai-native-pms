# SPDX-License-Identifier: Apache-2.0
"""mkt.core subdomain routes."""

from __future__ import annotations

from routers.mkt._common import APIRouter, Depends, Session, get_db, hotel_scope, ok

router = APIRouter(tags=["mkt"])


@router.get("/mkt/dashboard")
def mkt_dashboard_api(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import private_overview

    return ok(private_overview(db, hotel_id))
