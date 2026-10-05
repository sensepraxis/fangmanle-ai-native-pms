# SPDX-License-Identifier: Apache-2.0
"""finance.deposits subdomain routes."""

from __future__ import annotations

from routers.finance._common import (
    APIRouter,
    AppContext,
    Depends,
    Optional,
    Query,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["finance"])


@router.get("/deposits/board")
def deposits_board(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = None,
    form: Optional[str] = None,
    q: Optional[str] = None,
    bucket: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from application.finance import deposit_board

    return ok(deposit_board(db, hotel_id, status=status, form=form, q=q, bucket=bucket))


@router.get("/deposits/orders")
def deposits_collectable_orders(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import list_collectable_orders

    return ok({"orders": list_collectable_orders(db, hotel_id)})


@router.get("/deposits/lookup-by-phone")
def deposits_lookup_by_phone(
    phone: str = Query(..., min_length=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """收押主路径：手机号 → 客户 OneID → 有效订单。"""
    from application.finance import lookup_by_phone

    return ok(lookup_by_phone(db, hotel_id, phone))


@router.get("/deposits/lookup-by-room")
def deposits_lookup_by_room(
    room_no: str = Query(..., min_length=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """边角入口：房号 → 在住单。"""
    from application.finance import lookup_by_room

    return ok(lookup_by_room(db, hotel_id, room_no))


@router.get("/deposits/lookup-by-guest")
def deposits_lookup_by_guest(
    guest_id: int = Query(..., ge=1),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """候选人点选：guest_id → 360 + 有效订单。"""
    from application.finance import lookup_by_guest

    return ok(lookup_by_guest(db, hotel_id, guest_id))


@router.post("/deposits/preview-amount")
def deposits_preview_amount(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import credit_preview

    return ok(
        credit_preview(
            db,
            hotel_id=hotel_id,
            customer_id=payload.get("customer_id"),
            guest_id=payload.get("guest_id"),
            nights=int(payload.get("nights") or 1),
        )
    )


@router.get("/deposits/{deposit_id}")
def deposits_detail(
    deposit_id: str,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import get_detail

    return ok(get_detail(db, hotel_id, deposit_id))


@router.post("/deposits")
def deposits_collect(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import collect_deposit

    return ok(collect_deposit(db, ctx.hotel_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/deposits/{deposit_id}/capture")
def deposits_capture(
    deposit_id: str,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import capture_deposit

    return ok(capture_deposit(db, ctx.hotel_id, deposit_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/deposits/{deposit_id}/release")
def deposits_release(
    deposit_id: str,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import release_deposit

    return ok(release_deposit(db, ctx.hotel_id, deposit_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/deposits/{deposit_id}/reauthorize")
def deposits_reauthorize(
    deposit_id: str,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import reauthorize_deposit

    return ok(reauthorize_deposit(db, ctx.hotel_id, deposit_id, payload, str(getattr(ctx, "user_id", "op"))))


@router.post("/deposits/{deposit_id}/dispute")
def deposits_dispute(
    deposit_id: str,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import dispute_deposit

    return ok(dispute_deposit(db, ctx.hotel_id, deposit_id, payload, str(getattr(ctx, "user_id", "op"))))


# ---------- 退改与反结账 ----------
