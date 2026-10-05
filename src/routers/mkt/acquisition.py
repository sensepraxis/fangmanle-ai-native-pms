# SPDX-License-Identifier: Apache-2.0
"""mkt.acquisition subdomain routes."""

from __future__ import annotations

from routers.mkt._common import (
    APIRouter,
    AppContext,
    Depends,
    HTTPException,
    Optional,
    Query,
    Request,
    Session,
    assert_hotel_access,
    get_current_user,
    get_db,
    hotel_scope,
    json,
    ok,
)

router = APIRouter(tags=["mkt"])


@router.get("/campaigns")
def list_campaigns(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.mkt import list_channel_campaigns

    return ok(list_channel_campaigns(db, hotel_id))


@router.post("/campaigns")
def create_campaign(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.mkt import create_channel_campaign

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    return ok(create_channel_campaign(db, hotel_id, payload))


# ---------------- 营销获客闭环（Mock 小红书亦可） ----------------


@router.get("/acquisition/board")
def acquisition_board(
    hotel_id: int = Depends(hotel_scope),
    channel: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.mkt import build_acquisition_board

    return ok(build_acquisition_board(db, hotel_id, channel=channel))


@router.get("/acquisition/leads")
def acquisition_leads(
    hotel_id: int = Depends(hotel_scope),
    stage: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from application.mkt import list_acquisition_leads

    return ok(list_acquisition_leads(db, hotel_id, stage=stage))


@router.post("/acquisition/leads/manual")
def acquisition_manual_lead(
    payload: dict,
    ctx: AppContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """未投流 / 自然私信：运营手工录入线索。"""
    from application.mkt import create_manual_acquisition_lead

    return ok(create_manual_acquisition_lead(db, payload=payload, ctx=ctx))


@router.get("/acquisition/roi-attribution")
def acquisition_roi_attribution(
    hotel_id: int = Depends(hotel_scope),
    channel: Optional[str] = Query("xiaohongshu"),
    db: Session = Depends(get_db),
):
    """按笔记/计划聚合线索与成交，供 E-7 ROI 页使用。"""
    from application.mkt import build_acquisition_roi

    return ok(build_acquisition_roi(db, hotel_id, channel=channel))


@router.get("/acquisition/douyin/trade-board")
def acquisition_douyin_trade_board(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """抖音团购交易路看板：券售卖/待核销/已核销（ + 真实订单汇总）。"""
    from application.mkt import build_acquisition_douyin_trade_board

    return ok(build_acquisition_douyin_trade_board(db, hotel_id))


@router.post("/acquisition/leads/mock-ingest")
def acquisition_mock_ingest(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.mkt import mock_ingest_acquisition

    return ok(mock_ingest_acquisition(db, payload=payload, ctx=ctx))


@router.post("/acquisition/leads/{lead_id}/claim")
def acquisition_claim_lead(
    lead_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.mkt import claim_acquisition_lead

    return ok(claim_acquisition_lead(db, lead_id=lead_id, payload=payload or {}, ctx=ctx))


@router.post("/acquisition/leads/{lead_id}/to-private")
def acquisition_to_private(
    lead_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from mkt.acquisition_service import acquisition_to_private as do_to_private

    return ok(do_to_private(db, lead_id=lead_id, payload=payload or {}, ctx=ctx))


@router.post("/acquisition/leads/{lead_id}/create-order")
@router.post("/acquisition/leads/{lead_id}/convert-booking")
def acquisition_convert_booking(
    lead_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """人工转预订：须确认房型、入离店日期与价格，禁止自动生成预订单。"""
    from application.mkt import convert_acquisition_booking

    return ok(convert_acquisition_booking(db, lead_id=lead_id, payload=payload or {}, ctx=ctx))


@router.post("/acquisition/leads/{lead_id}/mark-arrived")
def acquisition_mark_arrived(
    lead_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """标记线索对应客人已到店（成交前最后一步）。"""
    from application.mkt import mark_acquisition_arrived

    return ok(mark_acquisition_arrived(db, lead_id=lead_id, payload=payload or {}, ctx=ctx))


# ---------------- 小红书 Webhook（多租户，无需 JWT） ----------------
from application.mkt import (
    binding_public_urls,
    extract_signature,
    ingest_xhs_webhook,
    new_binding_token,
    resolve_binding,
    verify_webhook_signature,
)


async def _handle_xhs_webhook(
    request: Request,
    db: Session,
    binding_token: Optional[str] = None,
) -> dict:
    raw = await request.body()
    sig = extract_signature({k: v for k, v in request.headers.items()})
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(400, "请求体须为 JSON")
    if not isinstance(payload, dict):
        raise HTTPException(400, "请求体须为 JSON 对象")

    binding = resolve_binding(db, binding_token=binding_token, payload=payload)
    if binding_token and not binding:
        raise HTTPException(404, "绑定 token 无效或已停用")
    if binding and binding.webhook_secret:
        verify_webhook_signature(raw, binding.webhook_secret, sig)

    raw_json = raw.decode("utf-8", errors="replace")
    return ingest_xhs_webhook(db, payload=payload, binding=binding, raw_json=raw_json)


@router.post("/webhook/xhs/leads")
async def webhook_xhs_leads_unified(request: Request, db: Session = Depends(get_db)):
    """统一入口：靠 payload 内广告账户 ID 路由到酒店（适合单账户测试）。"""
    result = await _handle_xhs_webhook(request, db)
    return ok(result)


@router.post("/webhook/xhs/leads/{binding_token}")
async def webhook_xhs_leads_by_token(
    binding_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """推荐：每家酒店在聚光填带 binding_token 的 URL。"""
    result = await _handle_xhs_webhook(request, db, binding_token=binding_token)
    return ok(result)


@router.get("/acquisition/channel-bindings")
def acquisition_channel_bindings(
    request: Request,
    hotel_id: int = Depends(hotel_scope),
    channel: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.mkt import list_acquisition_channel_bindings

    return ok(list_acquisition_channel_bindings(db, hotel_id, channel=channel, request=request))


@router.post("/acquisition/channel-bindings")
def acquisition_create_channel_binding(
    payload: dict,
    request: Request,
    ctx: AppContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from application.mkt import create_acquisition_channel_binding

    return ok(create_acquisition_channel_binding(db, payload=payload or {}, ctx=ctx, request=request))


@router.patch("/acquisition/channel-bindings/{binding_id}")
def acquisition_update_channel_binding(
    binding_id: int,
    payload: dict,
    request: Request,
    ctx: AppContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from application.mkt import update_acquisition_channel_binding

    return ok(
        update_acquisition_channel_binding(db, binding_id=binding_id, payload=payload or {}, ctx=ctx, request=request)
    )


@router.get("/acquisition/webhook-events")
def acquisition_webhook_events(
    hotel_id: int = Depends(hotel_scope),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from application.mkt import list_acquisition_webhook_events

    return ok(list_acquisition_webhook_events(db, hotel_id, limit=limit))


@router.post("/acquisition/webhook/simulate")
async def acquisition_webhook_simulate(
    payload: dict,
    request: Request,
    ctx: AppContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """登录态联调：模拟聚光 POST 到本酒店 binding（无需外网）。"""
    from application.mkt import simulate_acquisition_webhook

    return ok(simulate_acquisition_webhook(db, payload=payload or {}, ctx=ctx, request=request))


# ---------------- 鉴权（本地账号） ----------------
