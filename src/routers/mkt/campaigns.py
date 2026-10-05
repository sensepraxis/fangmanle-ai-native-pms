# SPDX-License-Identifier: Apache-2.0
"""mkt.campaigns subdomain routes."""

from __future__ import annotations

from routers.mkt._common import APIRouter, Depends, HTMLResponse, Optional, Query, Session, get_db, hotel_scope, ok

router = APIRouter(tags=["mkt"])


@router.get("/mkt/campaigns/templates")
def mkt_campaign_templates():
    from application.mkt import list_campaign_templates

    return ok(list_campaign_templates())


@router.get("/mkt/campaigns")
def mkt_campaigns_list(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.mkt import list_campaigns

    return ok(list_campaigns(db, hotel_id, status=status))


@router.post("/mkt/campaigns")
def mkt_campaigns_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import create_campaign

    return ok(create_campaign(db, hotel_id, payload or {}))


@router.patch("/mkt/campaigns/{campaign_id}/status")
def mkt_campaigns_status(
    campaign_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import patch_campaign_status

    payload = payload or {}
    return ok(
        patch_campaign_status(
            db,
            hotel_id,
            campaign_id,
            str(payload.get("status") or ""),
            approved_by=str(payload.get("approved_by") or ""),
        )
    )


@router.post("/mkt/campaigns/{campaign_id}/approve")
def mkt_campaigns_approve(
    campaign_id: int,
    payload: dict = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import approve_campaign

    payload = payload or {}
    return ok(approve_campaign(db, hotel_id, campaign_id, approved_by=str(payload.get("approved_by") or "manager")))


@router.post("/mkt/campaigns/{campaign_id}/reject")
def mkt_campaigns_reject(
    campaign_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import reject_campaign

    return ok(reject_campaign(db, hotel_id, campaign_id))


@router.get("/mkt/landing-templates")
def mkt_landing_templates(db: Session = Depends(get_db)):
    from application.mkt import list_landing_templates

    return ok(list_landing_templates(db))


@router.get("/mkt/landing-pages")
def mkt_landing_pages(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_landing_pages

    return ok(list_landing_pages(db, hotel_id))


@router.post("/mkt/landing-pages")
def mkt_landing_create(payload: dict, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import create_landing_page

    return ok(create_landing_page(db, hotel_id, payload or {}))


@router.put("/mkt/landing-pages/{page_id}")
def mkt_landing_update(
    page_id: int,
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.mkt import update_landing_page

    return ok(update_landing_page(db, hotel_id, page_id, payload or {}))


@router.post("/mkt/landing-pages/{page_id}/publish")
def mkt_landing_publish(page_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import publish_landing_page
    from application.wecom import load_wecom_config

    cfg = load_wecom_config(db)
    return ok(publish_landing_page(db, hotel_id, page_id, public_base=str(cfg.get("public_base_url") or "")))


@router.post("/mkt/landing-pages/{page_id}/unpublish")
def mkt_landing_unpublish(page_id: int, hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import unpublish_landing_page

    return ok(unpublish_landing_page(db, hotel_id, page_id))


@router.get("/mkt/landing-pages/{page_id}/preview")
def mkt_landing_preview_get(
    page_id: int,
    hotel_id: int = Depends(hotel_scope),
    demo: int = Query(1),
    db: Session = Depends(get_db),
):
    """已保存版本真预览（含 draft）；会员页默认数据。"""
    from fastapi.responses import HTMLResponse

    from application.mkt import preview_landing_html

    html = preview_landing_html(db, hotel_id, page_id=page_id, demo=bool(demo))
    return HTMLResponse(html)


@router.post("/mkt/landing-pages/preview")
def mkt_landing_preview_post(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """画布即时预览：可用未保存 blocks；可带 page_id 叠画布覆盖。"""
    from fastapi.responses import HTMLResponse

    from application.mkt import preview_landing_html

    payload = payload or {}
    page_id = payload.get("page_id")
    demo = payload.get("demo", True)
    html = preview_landing_html(
        db,
        hotel_id,
        page_id=int(page_id) if page_id else None,
        payload=payload,
        demo=bool(demo),
    )
    return HTMLResponse(html)


@router.post("/mkt/landing-pages/claim")
def mkt_landing_claim(payload: dict, db: Session = Depends(get_db)):
    """无企微 token 的公开领券（分享落地页）。"""
    from application.mkt import public_claim_without_token
    from infra.auth_local import DEFAULT_HOTEL_ID

    payload = payload or {}
    hotel_id = int(payload.get("hotel_id") or DEFAULT_HOTEL_ID)
    return ok(
        public_claim_without_token(
            db,
            hotel_id,
            str(payload.get("page_key") or "bind"),
            str(payload.get("phone") or ""),
        )
    )
