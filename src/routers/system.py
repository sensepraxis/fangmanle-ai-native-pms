# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)
from models import Hotel

router = APIRouter(tags=["system"])


@router.get("/hotel")
@router.get("/hotels")
def get_hotel(db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """本店配置（单体部署仅一家）。"""
    h = db.get(Hotel, ctx.hotel_id) or db.query(Hotel).order_by(Hotel.id).first()
    if not h:
        raise HTTPException(404, "酒店配置不存在")
    return ok([row_to_dict(h)])


@router.get("/channels")
def list_channels(db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    """运营/收益侧渠道列表：仅启用渠道；去重运营别名，佣金率与 OTA 佣金档案对齐。"""
    from application.finance import list_channels_for_api

    return ok(list_channels_for_api(db))


# ---------------- 系统配置 · OTA 佣金（渠道档案） ----------------
@router.get("/system/ota-commission")
def sys_ota_commission_get(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import (
        can_edit_commission,
        list_commission_overrides,
        list_ota_commission_channels,
    )
    from infra.i18n import t as _t

    channels = list_ota_commission_channels(db)
    return ok(
        {
            "channels": channels,
            "overrides": list_commission_overrides(db, hotel_id),
            "can_edit": can_edit_commission(ctx.role),
            "role": ctx.role,
            "settle_cycles": ["T+1", "T+7", "月结", "实时"],
            "compliance_note": _t("佣金率为签约/自选结果；系统不计算、不自动调价；保存不触发改价。"),
        }
    )


@router.put("/system/ota-commission")
def sys_ota_commission_put(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import save_ota_commission_channels

    body = dict(payload or {})
    body["hotel_id"] = hotel_id
    return ok(save_ota_commission_channels(db, body, role=ctx.role, username=getattr(ctx, "username", None)))


@router.post("/system/ota-commission/channels")
def sys_ota_commission_channel_upsert(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """新增或编辑单个 OTA 渠道（名称 / 编码 / 佣金 / 结算周期）。"""
    from application.finance import upsert_ota_commission_channel

    return ok(
        upsert_ota_commission_channel(
            db,
            payload or {},
            role=ctx.role,
            username=getattr(ctx, "username", None),
            hotel_id=hotel_id,
        )
    )


@router.patch("/system/ota-commission/channels/{channel_code}/enabled")
def sys_ota_commission_channel_enabled(
    channel_code: str,
    payload: dict = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """启用 / 禁用渠道（软开关）。"""
    from application.finance import set_ota_channel_enabled

    body = payload or {}
    enabled = body.get("is_enabled")
    if enabled is None:
        enabled = body.get("enabled", True)
    return ok(
        set_ota_channel_enabled(
            db,
            channel_code,
            bool(enabled),
            role=ctx.role,
            username=getattr(ctx, "username", None),
            hotel_id=hotel_id,
        )
    )


@router.post("/system/ota-commission/reset")
def sys_ota_commission_reset(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import reset_ota_commission_defaults
    from application.pricing import sync_commission_from_channels

    out = reset_ota_commission_defaults(db, role=ctx.role, username=getattr(ctx, "username", None))
    try:
        sync_commission_from_channels(db, hotel_id)
    except Exception:
        pass
    return ok(out)


@router.get("/system/ota-commission/overrides")
def sys_ota_commission_overrides_get(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import list_commission_overrides

    return ok(list_commission_overrides(db, hotel_id))


@router.post("/system/ota-commission/overrides")
def sys_ota_commission_overrides_post(
    payload: dict,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import upsert_commission_override

    return ok(
        upsert_commission_override(db, hotel_id, payload or {}, role=ctx.role, username=getattr(ctx, "username", None))
    )


@router.delete("/system/ota-commission/overrides/{override_id}")
def sys_ota_commission_overrides_del(
    override_id: int,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import delete_commission_override

    return ok(delete_commission_override(db, hotel_id, override_id, role=ctx.role))


@router.post("/system/ota-commission/preview")
def sys_ota_commission_preview(
    payload: dict = None, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    """换算：挂牌→净到手，或净到手→渠道挂价（§5.10）。不改库。"""
    from finance.ota_commission_service import channel_price_from_net, net_from_channel_price

    payload = payload or {}
    rate = float(payload.get("commission_rate") or 0)
    if rate > 1:
        rate = rate / 100.0
    mode = payload.get("mode") or "list_to_net"
    if mode == "net_to_list":
        net = float(payload.get("net_price") or payload.get("rate_plan_price") or 0)
        listing = channel_price_from_net(net, rate)
        return ok(
            {
                "mode": mode,
                "net_price": net,
                "commission_rate": rate,
                "channel_price": listing,
                "platform_cut": round(listing - net, 2),
                "formula": "channel_price = rate_plan.price / (1 − commission_rate)",
            }
        )
    listing = float(payload.get("list_price") or payload.get("channel_price") or 0)
    net = net_from_channel_price(listing, rate)
    return ok(
        {
            "mode": "list_to_net",
            "list_price": listing,
            "commission_rate": rate,
            "net_price": net,
            "platform_cut": round(listing - net, 2),
            "formula": "net = list_price × (1 − commission_rate)",
        }
    )


# ---------------- 经营总览 ----------------
@router.get("/dashboard")
def dashboard(
    hotel_id: int = Depends(hotel_scope),
    period: str = Query("今日", description="今日/本周/本月"),
    db: Session = Depends(get_db),
):
    """经营总览 · 实时看板快照（统一指标层切片）。"""
    from application.analytics import build_realtime_snapshot

    try:
        return ok(build_realtime_snapshot(db, hotel_id, period=period or "今日"))
    except Exception as e:
        raise HTTPException(503, f"看板快照失败：{e}") from e


# ---------------- 房态看板 ----------------
@router.get("/system/finance-params/float-carry")
def finance_params_float_carry(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.finance import get_float_carry_workspace

    return ok(get_float_carry_workspace(db, hotel_id))


class FloatCarryChangePayload(BaseModel):
    amount: float
    reason: str
    denom_ratios: list[dict] | None = None
    review_password: str = ""


class FloatCarryReviewPayload(BaseModel):
    review_password: str = ""


@router.post("/system/finance-params/float-carry/request")
def finance_params_float_carry_request(
    payload: FloatCarryChangePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import submit_float_carry_change

    return ok(
        submit_float_carry_change(
            db,
            hotel_id,
            float(payload.amount),
            payload.reason,
            ctx,
            payload.denom_ratios,
            payload.review_password,
        )
    )


@router.post("/system/finance-params/float-carry/{request_id}/approve-finance")
def finance_params_float_carry_approve_finance(
    request_id: int,
    payload: FloatCarryReviewPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import approve_float_carry_finance

    return ok(approve_float_carry_finance(db, hotel_id, request_id, ctx, payload.review_password))


@router.post("/system/finance-params/float-carry/{request_id}/approve-manager")
def finance_params_float_carry_approve_manager(
    request_id: int,
    payload: FloatCarryReviewPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import approve_float_carry_manager

    return ok(approve_float_carry_manager(db, hotel_id, request_id, ctx, payload.review_password))


class FloatCarryRejectPayload(BaseModel):
    reason: str = ""
    review_password: str = ""


@router.post("/system/finance-params/float-carry/{request_id}/reject")
def finance_params_float_carry_reject(
    request_id: int,
    payload: FloatCarryRejectPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import reject_float_carry_change

    return ok(reject_float_carry_change(db, hotel_id, request_id, ctx, payload.reason, payload.review_password))


# ---------- 财务参数扩展：税率账期 / 收单费率 / 信用账龄 ----------


@router.get("/system/finance-params/tax")
def finance_params_tax(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import get_tax_workspace

    return ok(get_tax_workspace(db, hotel_id))


class TaxUpdatePayload(BaseModel):
    taxpayer_type: str = "一般纳税人"
    main_rate_pct: float
    price_mode: str = "价外"
    effective_mode: str = "次月 1 日（推荐）"
    specified_date: str | None = None
    reason: str


@router.post("/system/finance-params/tax")
def finance_params_tax_update(
    payload: TaxUpdatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_tax_config

    return ok(
        update_tax_config(
            db,
            hotel_id,
            taxpayer_type=payload.taxpayer_type,
            main_rate_pct=payload.main_rate_pct,
            price_mode=payload.price_mode,
            effective_mode=payload.effective_mode,
            reason=payload.reason,
            specified_date=payload.specified_date,
            operator_id=ctx.user_id,
        )
    )


class TermUpdatePayload(BaseModel):
    term_label: str
    effective_mode: str = "立即生效"
    reason: str


@router.post("/system/finance-params/tax/terms/{term_id}")
def finance_params_term_update(
    term_id: int,
    payload: TermUpdatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_payment_term

    return ok(
        update_payment_term(
            db,
            hotel_id,
            term_id,
            term_label=payload.term_label,
            effective_mode=payload.effective_mode,
            reason=payload.reason,
            operator_id=ctx.user_id,
        )
    )


@router.get("/system/finance-params/acquiring")
def finance_params_acquiring(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import get_acquiring_workspace

    return ok(get_acquiring_workspace(db, hotel_id))


class AcquiringRatePayload(BaseModel):
    rate_pct: float
    effective_mode: str = "次月 1 日（推荐）"
    reason: str


@router.post("/system/finance-params/acquiring/{channel_id}/rate")
def finance_params_acquiring_rate(
    channel_id: int,
    payload: AcquiringRatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_acquiring_rate

    return ok(
        update_acquiring_rate(
            db,
            hotel_id,
            channel_id,
            rate_pct=payload.rate_pct,
            effective_mode=payload.effective_mode,
            reason=payload.reason,
            operator_id=ctx.user_id,
        )
    )


class AcquiringTogglePayload(BaseModel):
    enabled: bool


@router.post("/system/finance-params/acquiring/{channel_id}/toggle")
def finance_params_acquiring_toggle(
    channel_id: int,
    payload: AcquiringTogglePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import toggle_acquiring_channel

    return ok(toggle_acquiring_channel(db, hotel_id, channel_id, enabled=payload.enabled, operator_id=ctx.user_id))


@router.get("/system/finance-params/credit")
def finance_params_credit(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.finance import get_credit_workspace

    return ok(get_credit_workspace(db, hotel_id))


class CreditCreatePayload(BaseModel):
    name: str
    customer_type: str = "企业挂账"
    grade: str = "B"
    credit_limit: float
    term_label: str = "30 天"
    reason: str


@router.post("/system/finance-params/credit")
def finance_params_credit_create(
    payload: CreditCreatePayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import create_credit_customer

    return ok(
        create_credit_customer(
            db,
            hotel_id,
            name=payload.name,
            customer_type=payload.customer_type,
            grade=payload.grade,
            credit_limit=payload.credit_limit,
            term_label=payload.term_label,
            reason=payload.reason,
            operator_id=ctx.user_id,
        )
    )


class CreditLimitPayload(BaseModel):
    new_limit: float
    reason: str


@router.post("/system/finance-params/credit/{customer_id}/limit")
def finance_params_credit_limit(
    customer_id: int,
    payload: CreditLimitPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_credit_limit

    return ok(
        update_credit_limit(
            db,
            hotel_id,
            customer_id,
            new_limit=payload.new_limit,
            reason=payload.reason,
            operator_id=ctx.user_id,
        )
    )


class BadDebtPayload(BaseModel):
    rate_pct: float
    reason: str


@router.post("/system/finance-params/credit/bad-debt/{rate_id}")
def finance_params_bad_debt(
    rate_id: int,
    payload: BadDebtPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.finance import update_bad_debt_rate

    return ok(
        update_bad_debt_rate(
            db,
            hotel_id,
            rate_id,
            rate_pct=payload.rate_pct,
            reason=payload.reason,
            operator_id=ctx.user_id,
        )
    )


@router.get("/overview/revenue-forecast")
def overview_revenue_forecast(
    hotel_id: int = Depends(hotel_scope),
    growth_factor: float = Query(1.0, ge=0.5, le=2.0),
    db: Session = Depends(get_db),
):
    """经营总览 · 营收预测：共享 Forecast Service（与价格助手同源消费）。"""
    from application.analytics import build_revenue_forecast

    return ok(build_revenue_forecast(db, hotel_id, growth_factor=growth_factor))


@router.post("/overview/revenue-forecast/ai-advice")
def overview_revenue_forecast_ai_advice(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """智能问数：经营快照 + 规则 anomalies + LLM 受限 JSON（§产品定义）。"""
    from application.analytics import generate_ask_data

    growth_factor = float(payload.get("growth_factor") or 1.0)
    try:
        return ok(generate_ask_data(db, hotel_id, growth_factor=max(0.5, min(2.0, growth_factor))))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"智能问数失败：{e}") from e


@router.post("/overview/revenue-forecast/ai-advice/stream")
def overview_revenue_forecast_ai_advice_stream(
    payload: dict = {},
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """流式智能问数（SSE：meta / token / done）。"""
    from application.analytics import stream_ask_data

    growth_factor = float(payload.get("growth_factor") or 1.0)
    gf = max(0.5, min(2.0, growth_factor))

    def event_gen():
        try:
            for evt in stream_ask_data(db, hotel_id, growth_factor=gf):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# 系统配置 · 白标品牌 + 私域通道 vendor（开源可配置）
# ---------------------------------------------------------------------------
@router.get("/system/branding")
def sys_branding_get(db: Session = Depends(get_db)):
    """公开品牌信息（登录页也可用；无密钥）。"""
    from infra.branding import branding_public_dict, load_branding_overrides

    try:
        load_branding_overrides(db)
    except Exception:
        pass
    return ok(branding_public_dict())


@router.get("/system/private-channel")
def sys_private_channel_get(db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from extensions.messaging.facade import channel_status
    from infra.private_channel import (
        load_private_channel_config,
        mask_private_channel_config,
        resolve_vendor,
    )

    cfg = mask_private_channel_config(load_private_channel_config(db))
    status = channel_status(db)
    return ok({**cfg, "effective_vendor": resolve_vendor(), "status": status})


@router.put("/system/private-channel")
def sys_private_channel_put(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from extensions.messaging.facade import channel_status
    from infra.private_channel import (
        mask_private_channel_config,
        resolve_vendor,
        save_private_channel_config,
    )

    try:
        cfg = save_private_channel_config(db, payload or {})
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return ok(
        {
            **mask_private_channel_config(cfg),
            "effective_vendor": resolve_vendor(),
            "status": channel_status(db),
        }
    )


# ---------------------------------------------------------------------------
# 系统配置 · 地图（天地图 / 高德 / 百度 / Google）
# ---------------------------------------------------------------------------
@router.get("/system/map-config")
def sys_map_config_get(db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from infra.map_config import apply_runtime_from_db, map_providers_ui, mask_map_config, runtime_provider
    from infra.map_provider import map_status

    cfg = apply_runtime_from_db(db)
    status = map_status(db)
    masked = mask_map_config(cfg)
    masked["provider"] = runtime_provider() or masked.get("provider")
    return ok({**masked, "providers": map_providers_ui(), "status": status})


@router.put("/system/map-config")
def sys_map_config_put(
    payload: dict,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from infra.map_config import mask_map_config, save_map_config
    from infra.map_provider import map_status

    saved = save_map_config(db, payload or {})
    from infra.map_config import map_providers_ui, runtime_provider

    masked = mask_map_config(saved)
    masked["provider"] = runtime_provider() or masked.get("provider")
    return ok({**masked, "providers": map_providers_ui(), "status": map_status(db)})


@router.post("/system/map-config/test")
def sys_map_config_test(
    payload: dict = None,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """用当前配置试解析一条地址。"""
    from infra.map_config import apply_runtime_from_db
    from infra.map_provider import geocode_address, map_status

    apply_runtime_from_db(db)
    payload = payload or {}
    address = str(payload.get("address") or "上海市黄浦区人民广场").strip()
    city = str(payload.get("city") or "").strip() or None
    try:
        loc = geocode_address(address, city=city, db=db)
        return ok({"ok": True, "location": loc, "status": map_status(db)})
    except Exception as e:
        return ok({"ok": False, "error": str(e), "status": map_status(db)})


@router.get("/system/map-tile/{layer}/{z}/{y}/{x}")
def sys_map_tile(
    layer: str,
    z: int,
    y: int,
    x: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """同源瓦片代理：委托当前 IMap.fetch_tile（天地图/高德/Google…各自实现）。

    img 请求通常不带 Authorization，故此接口免登录。
    Referer 从客户端 Host 动态拼接（支持 IP / 域名 / 反代）。
    """
    from extensions.map.facade import proxy_map_tile
    from infra.map_config import apply_runtime_from_db

    apply_runtime_from_db(db)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "127.0.0.1:8000"
    scheme = request.headers.get("x-forwarded-proto") or "http"
    referer = f"{scheme}://{host}/"
    try:
        body, ctype = proxy_map_tile(layer, z, y, x, referer=referer, db=None)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"瓦片拉取失败：{e}") from e

    return Response(
        content=body,
        media_type=ctype,
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ---------------------------------------------------------------------------
# 数据洞察（BI / Insights）— 事后归因，不重复实时看板 / 营收预测
# ---------------------------------------------------------------------------
@router.get("/demo/{entity}")
def demo_entity(entity: str):
    return ok(_demo_get(entity))


# ---------------- 静态前端 ----------------
