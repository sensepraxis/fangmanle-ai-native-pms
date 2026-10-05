# SPDX-License-Identifier: Apache-2.0
"""mkt.coupons subdomain routes."""

from __future__ import annotations

from mkt.wallet_norm import NATIVE_WALLET_SOURCE, label_for_wallet_source
from routers.mkt._common import (
    APIRouter,
    AppContext,
    BaseModel,
    Depends,
    HTTPException,
    Optional,
    Query,
    Session,
    get_current_user,
    get_db,
    hotel_scope,
    ok,
)

router = APIRouter(tags=["mkt"])


@router.get("/mkt/coupons/templates")
def mkt_coupon_templates():
    from application.mkt import list_coupon_templates

    return ok(list_coupon_templates())


@router.get("/mkt/coupons")
def mkt_coupons_list(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.mkt import list_coupons

    return ok(list_coupons(db, hotel_id, status=status))


@router.post("/mkt/coupons")
def mkt_coupons_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import create_coupon

    return ok(create_coupon(db, hotel_id, payload or {}))


@router.patch("/mkt/coupons/{coupon_id}/status")
def mkt_coupons_status(
    coupon_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import update_coupon_status

    return ok(update_coupon_status(db, hotel_id, coupon_id, str((payload or {}).get("status") or "")))


@router.post("/mkt/coupons/{coupon_id}/grant")
def mkt_coupons_grant(
    coupon_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import grant_coupon

    payload = payload or {}
    return ok(
        grant_coupon(
            db,
            hotel_id,
            coupon_id,
            guest_ids=[int(x) for x in (payload.get("guest_ids") or [])],
            channel=str(payload.get("channel") or "manual"),
            mode=str(payload.get("mode") or "guest"),
            segment=payload.get("segment"),
            require_h5=bool(payload.get("require_h5", True)),
            allow_over_limit=bool(payload.get("allow_over_limit")),
            over_limit_reason=payload.get("over_limit_reason") or payload.get("reason"),
        )
    )


@router.get("/mkt/coupons/{coupon_id}/ownership")
def mkt_coupon_ownership(
    coupon_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    guest_ids: Optional[str] = None,
):
    """查询客人对该批次的持有/限领状态。guest_ids=1,2,3 可选。"""
    from application.mkt import list_coupon_guest_ownership

    ids = None
    if guest_ids:
        ids = []
        for part in str(guest_ids).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                continue
    return ok(list_coupon_guest_ownership(db, hotel_id, coupon_id, ids))


@router.get("/mkt/grant-segments")
def mkt_grant_segments(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_grant_segments

    return ok(list_grant_segments(db, hotel_id))


@router.post("/mkt/grant-preview")
def mkt_grant_preview(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import preview_grant_audience

    payload = payload or {}
    return ok(
        preview_grant_audience(
            db,
            hotel_id,
            mode=str(payload.get("mode") or "guest"),
            segment=payload.get("segment"),
            guest_ids=payload.get("guest_ids") or [],
        )
    )


@router.get("/mkt/coupons/{coupon_id}/claim-entries")
def mkt_coupon_claim_entries(coupon_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_claim_landing_options

    return ok(list_claim_landing_options(db, hotel_id, coupon_id=coupon_id))


@router.post("/mkt/coupons/{coupon_id}/bind-claim-landing")
def mkt_coupon_bind_claim(
    coupon_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import bind_coupon_to_claim_landing

    payload = payload or {}
    page_id = int(payload.get("page_id") or 0)
    if not page_id:
        raise HTTPException(400, "请指定落地页 page_id")
    return ok(bind_coupon_to_claim_landing(db, hotel_id, page_id, coupon_id))


@router.get("/mkt/coupons/{coupon_id}/grants")
def mkt_coupon_grants(coupon_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_grants

    return ok(list_grants(db, hotel_id, coupon_id=coupon_id))


@router.get("/mkt/grants")
def mkt_all_grants(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_grants

    return ok(list_grants(db, hotel_id))


@router.post("/mkt/coupons/verify")
def mkt_coupons_verify(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import verify_coupon

    payload = payload or {}
    return ok(
        verify_coupon(
            db,
            hotel_id,
            str(payload.get("code") or ""),
            order_id=payload.get("order_id"),
        )
    )


# ---------- 优惠券系统权威稿 §10 API（/api/mkt/coupon/*）----------


@router.post("/mkt/coupon/batch")
def mkt_coupon_batch_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import create_coupon

    return ok(create_coupon(db, hotel_id, payload or {}))


@router.put("/mkt/coupon/batch/{batch_id}")
def mkt_coupon_batch_update(
    batch_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import update_coupon_batch

    return ok(update_coupon_batch(db, hotel_id, batch_id, payload or {}))


@router.get("/mkt/coupon/batch")
def mkt_coupon_batch_list(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.mkt import list_coupons

    return ok(list_coupons(db, hotel_id, status=status))


@router.post("/mkt/coupon/instance/grant")
def mkt_coupon_instance_grant(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import grant_coupon

    payload = payload or {}
    batch_id = int(payload.get("batch_id") or payload.get("coupon_id") or 0)
    if not batch_id:
        raise HTTPException(400, "请指定 batch_id")
    guest_ids = payload.get("guest_ids") or []
    if payload.get("customer_id") and not guest_ids:
        guest_ids = [int(payload["customer_id"])]
    return ok(
        grant_coupon(
            db,
            hotel_id,
            batch_id,
            guest_ids=[int(x) for x in guest_ids],
            channel=str(payload.get("grant_channel") or payload.get("channel") or "manual"),
            mode=str(payload.get("mode") or "guest"),
            segment=payload.get("segment"),
            require_h5=bool(payload.get("require_h5", True)),
            grant_event=str(payload.get("grant_event") or "manual"),
            auto_claim=bool(payload.get("auto_claim", True)),
        )
    )


@router.get("/mkt/coupon/wallet")
def mkt_coupon_wallet(
    oneid: int = Query(..., description="customer_id / guest_id"),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import wallet_by_customer

    return ok(wallet_by_customer(db, hotel_id, oneid))


@router.post("/mkt/coupon/claim")
def mkt_coupon_claim(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import claim_instance

    payload = payload or {}
    return ok(
        claim_instance(
            db,
            hotel_id,
            code=payload.get("code") or payload.get("coupon_code"),
            instance_id=payload.get("instance_id") or payload.get("id"),
            customer_id=payload.get("customer_id") or payload.get("oneid"),
        )
    )


@router.post("/mkt/coupon/redeem")
def mkt_coupon_redeem(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import redeem_instance

    payload = payload or {}
    return ok(
        redeem_instance(
            db,
            hotel_id,
            code=payload.get("code") or payload.get("coupon_code"),
            instance_id=payload.get("instance_id"),
            order_id=payload.get("order_id"),
            order_amount=payload.get("order_amount"),
            cashier=payload.get("cashier") or payload.get("redeemed_by"),
        )
    )


@router.get("/mkt/coupon/verify")
def mkt_coupon_verify_get(
    code: str = Query(...),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import verify_instance_preview

    return ok(verify_instance_preview(db, hotel_id, code))


@router.post("/mkt/coupon/trigger")
def mkt_coupon_trigger_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import upsert_auto_rule

    return ok(upsert_auto_rule(db, hotel_id, payload or {}))


@router.get("/mkt/coupon/trigger")
def mkt_coupon_trigger_list(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_auto_rules

    return ok(list_auto_rules(db, hotel_id))


@router.post("/mkt/coupon/trigger/fire")
def mkt_coupon_trigger_fire(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """/联调：显式触发事件发放。"""
    from application.mkt import fire_event

    payload = payload or {}
    cid = int(payload.get("customer_id") or payload.get("oneid") or 0)
    if not cid:
        raise HTTPException(400, "请指定 customer_id")
    return ok(
        fire_event(
            db,
            hotel_id,
            str(payload.get("event_type") or ""),
            cid,
            event_params=payload.get("event_params"),
        )
    )


# ---------- 自动发券规则（产品主入口）----------


@router.get("/mkt/coupon/redeem/log")
def mkt_coupon_redeem_log(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_redeem_log

    rows = list_redeem_log(db, hotel_id)
    # 统一字段，避免旧进程/旧格式导致前端整列空白
    out = []
    for r in rows or []:
        used_at = r.get("used_at") or r.get("redeemed_at")
        out.append(
            {
                **r,
                "used_at": used_at,
                "redeemed_at": used_at,
                "source": r.get("source") or r.get("wallet_source") or NATIVE_WALLET_SOURCE,
                "wallet_source": r.get("wallet_source") or r.get("source") or NATIVE_WALLET_SOURCE,
                "source_label": r.get("source_label")
                or label_for_wallet_source(r.get("wallet_source") or r.get("source") or NATIVE_WALLET_SOURCE),
                "used_order_id": r.get("used_order_id") if r.get("used_order_id") is not None else r.get("order_id"),
                "used_amount": r.get("used_amount") if r.get("used_amount") is not None else r.get("amount_saved"),
                "coupon_code": r.get("coupon_code") or r.get("code"),
                "guest_name": r.get("guest_name") or r.get("customer_name"),
                "batch_no": r.get("batch_no"),
                "coupon_name": r.get("coupon_name") or r.get("name"),
            }
        )
    return ok(out)


@router.post("/mkt/coupon/expire-scan")
def mkt_coupon_expire_scan(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import expire_due_instances

    n = expire_due_instances(db, hotel_id)
    return ok({"expired": n})


@router.get("/coupons/lookup")
def coupon_lookup(code: str = Query(...), db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """前台按券码查询私域优惠券。"""
    from application.mkt import lookup_coupon_by_code

    return ok(lookup_coupon_by_code(db, code))


class CouponRedeemPayload(BaseModel):
    coupon_id: Optional[int] = None
    code: Optional[str] = None
    order_id: Optional[int] = None
    remark: str = ""


@router.post("/coupons/redeem")
def coupon_redeem(
    payload: CouponRedeemPayload,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """前台核销私域优惠券（按券 ID 或券码）。"""
    if not payload.coupon_id and not (payload.code or "").strip():
        raise HTTPException(422, "请提供 coupon_id 或 code")
    from application.mkt import redeem_guest_coupon

    return ok(
        redeem_guest_coupon(
            db,
            coupon_id=payload.coupon_id,
            code=payload.code,
            order_id=payload.order_id,
            operator=getattr(ctx, "full_name", None) or ctx.username or "前台",
            remark=payload.remark or "",
        )
    )
