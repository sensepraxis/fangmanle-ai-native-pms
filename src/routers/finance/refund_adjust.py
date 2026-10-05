# SPDX-License-Identifier: Apache-2.0
"""finance.refund_adjust subdomain routes."""

from __future__ import annotations

from routers.finance._common import (
    APIRouter,
    AppContext,
    Depends,
    Query,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["finance"])


@router.get("/refund-adjust/board")
def refund_adjust_board(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from finance.refund_service import board as ra_board

    return ok(ra_board(db, hotel_id))


@router.put("/refund-adjust/threshold")
def refund_adjust_threshold(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_threshold

    return ok(
        update_threshold(
            db,
            ctx.hotel_id,
            int(payload.get("refund_threshold_yuan") or 2000),
            str(getattr(ctx, "user_id", "op")),
        )
    )


@router.get("/refund-adjust/lookup-order")
def refund_adjust_lookup_order(
    q: str = Query(..., min_length=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import lookup_order_for_refund

    return ok(lookup_order_for_refund(db, hotel_id, q))


@router.get("/refund-adjust/lookup-by-phone")
def refund_adjust_lookup_by_phone(
    phone: str = Query(..., min_length=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import lookup_refund_by_phone

    return ok(lookup_refund_by_phone(db, hotel_id, phone))


@router.get("/refund-adjust/order-detail")
def refund_adjust_order_detail(
    order_id: int = Query(..., ge=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import build_refund_order_detail

    return ok(build_refund_order_detail(db, hotel_id, order_id))


@router.get("/refund-adjust/adjust-entries")
def refund_adjust_entries(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import list_adjust_entries

    return ok({"entries": list_adjust_entries(db, hotel_id)})


@router.get("/refund-adjust/reverse-targets")
def refund_adjust_reverse_targets(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import list_reverse_targets

    return ok({"targets": list_reverse_targets(db, hotel_id)})


@router.post("/refund-adjust/refund")
def refund_adjust_submit_refund(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import submit_refund

    return ok(submit_refund(db, ctx.hotel_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/refund-adjust/adjust")
def refund_adjust_submit_adjust(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import submit_adjust

    return ok(submit_adjust(db, ctx.hotel_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/refund-adjust/reverse")
def refund_adjust_submit_reverse(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import submit_reverse

    return ok(submit_reverse(db, ctx.hotel_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/refund-adjust/tickets/{ticket_id}/dual-auth")
def refund_adjust_dual_auth(
    ticket_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import dual_auth

    return ok(
        dual_auth(
            db,
            ctx.hotel_id,
            ticket_id,
            str(payload.get("role") or ""),
            str(getattr(ctx, "user_id", "op")),
        )
    )
