# SPDX-License-Identifier: Apache-2.0
"""房满乐 PMS —— 后端入口 (FastAPI)。路由按域拆至 routers/。"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Re-export helpers for any legacy `from api import ok` callers
from api_common import hotel_scope, ok, row_to_dict  # noqa: F401

# 业务异常 → HTTP 异常 翻译器（让业务层不依赖 fastapi）
from domain import BusinessError  # noqa: F401
from infra.branding import product_title
from infra.i18n import parse_accept_language, set_locale, t
from routers.analytics import router as analytics_router
from routers.assets import router as assets_router
from routers.auth import router as auth_router
from routers.finance import router as finance_router
from routers.guests import router as guests_router
from routers.housekeeping import router as housekeeping_router
from routers.llm import router as llm_router
from routers.misc import router as misc_router
from routers.mkt import router as mkt_router
from routers.orders import router as orders_router
from routers.pricing import router as pricing_router
from routers.rbac import router as rbac_router
from routers.rooms import router as rooms_router
from routers.supplies import router as supplies_router
from routers.system import router as system_router
from routers.wecom import router as wecom_router

app = FastAPI(title=product_title())


# ---- 全局异常 handler：把业务层 BusinessError 翻译为 HTTPException ----
@app.exception_handler(BusinessError)
async def _business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    """业务层抛 BusinessError → 统一转为 JSONResponse（detail 经 i18n）。"""
    # 优先 Accept-Language / X-Locale，保证错误文案跟请求语言一致
    loc = request.headers.get("X-Locale") or parse_accept_language(request.headers.get("Accept-Language"))
    set_locale(loc)
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "detail": t(exc.message),
            "code": exc.code,
            **(exc.detail or {}),
        },
    )


@app.middleware("http")
async def _locale_middleware(request: Request, call_next):
    """从 query / header 写入请求级 locale。"""
    q = request.query_params.get("lang") or request.query_params.get("locale")
    loc = q or request.headers.get("X-Locale") or parse_accept_language(request.headers.get("Accept-Language"))
    set_locale(loc)
    response = await call_next(request)
    response.headers["Content-Language"] = loc if loc in ("en", "zh-CN") else "zh-CN"
    return response


# Event Bus 集成：让 WebHook Channel 自动订阅所有 lifecycle 事件
import logging

_log = logging.getLogger("uvicorn.error")
try:
    from events.integration import install_webhook_integration

    install_webhook_integration()
    _log.info("[EventBus] install_webhook_integration OK — 10 lifecycle events bridged to WebHook")
except Exception as e:
    _log.warning("[EventBus] install_webhook_integration failed: %s", e)

try:
    from infra.auth_local import jwt_uses_demo_secret

    if jwt_uses_demo_secret():
        _log.warning(
            "[auth] FML_JWT_SECRET is still the demo default please-change-this-jwt-secret; set a random secret in production"
        )
except Exception:
    pass

try:
    from infra.hotel import ensure_hotel

    ensure_hotel()
except Exception as e:
    _log.warning("[Hotel] ensure_hotel failed: %s", e)

# Rule Engine：加载所有域的 RuleSet（hk 派单、后续 pricing/wecom/finance）
try:
    from hk.hk_rules import HK_DISPATCH_RULESET  # noqa: F401 触发注册
    from rules import get_rule_set

    _log.info(
        "[RuleEngine] registered rulesets: hk_dispatch (%d rules)",
        len(HK_DISPATCH_RULESET.list_rules()),
    )
except Exception as e:
    _log.warning("[RuleEngine] register rulesets failed: %s", e)

# 白标 + 私域通道：从 AppSetting 灌入进程缓存（失败不阻断启动）
try:
    from bootstrap.ensure_coupon_wallet import ensure_coupon_wallet_schema
    from database import engine as _engine
    from database import session_scope
    from infra.branding import app_name, app_name_en, app_slug, ensure_branding_defaults, load_branding_overrides
    from infra.private_channel import configure_from_db, ensure_private_channel_defaults, resolve_vendor
    from infra.schema_migrate import apply_pending_migrations

    mig = apply_pending_migrations(_engine)
    if mig.get("applied"):
        _log.info("[SchemaMigrate] applied=%s current=%s", mig["applied"], mig.get("current"))
    ensure_coupon_wallet_schema(_engine)
    with session_scope() as _db:
        ensure_branding_defaults(_db)
        load_branding_overrides(_db)
        ensure_private_channel_defaults(_db)
        configure_from_db(_db)
    _log.info(
        "[Branding] app_name=%s | private_channel.vendor=%s",
        app_name_en() or app_slug() or app_name(),
        resolve_vendor(),
    )
except Exception as e:
    _log.warning("[Branding/PrivateChannel] bootstrap failed: %s", e)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _no_cache_frontend_assets(request, call_next):
    """避免浏览器强缓存旧 hashed 资源，导致装修器改完刷新仍像没更新。"""
    response = await call_next(request)
    path = request.url.path or ""
    if path == "/" or path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# API 版本化（v1）：所有路由统一挂在 /api/v1/ 前缀下
# ---------------------------------------------------------------------------
API_V1_PREFIX = "/api/v1"

app.include_router(analytics_router, prefix=API_V1_PREFIX)
app.include_router(assets_router, prefix=API_V1_PREFIX)
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(finance_router, prefix=API_V1_PREFIX)
app.include_router(guests_router, prefix=API_V1_PREFIX)
app.include_router(housekeeping_router, prefix=API_V1_PREFIX)
app.include_router(llm_router, prefix=API_V1_PREFIX)
app.include_router(misc_router, prefix=API_V1_PREFIX)
app.include_router(mkt_router, prefix=API_V1_PREFIX)
app.include_router(orders_router, prefix=API_V1_PREFIX)
app.include_router(pricing_router, prefix=API_V1_PREFIX)
app.include_router(rbac_router, prefix=API_V1_PREFIX)
app.include_router(rooms_router, prefix=API_V1_PREFIX)
app.include_router(supplies_router, prefix=API_V1_PREFIX)
app.include_router(system_router, prefix=API_V1_PREFIX)
app.include_router(wecom_router, prefix=API_V1_PREFIX)

_src_dir = os.path.dirname(os.path.abspath(__file__))
_dist = os.path.normpath(os.path.join(_src_dir, "..", "frontend", "dist"))
STATIC = _dist if os.path.isdir(_dist) else os.path.join(_src_dir, "static")


@app.get("/")
def index():
    """index.html 禁止缓存，避免重建后仍引用旧 hashed chunk。"""
    index_html = os.path.join(STATIC, "index.html")
    if not os.path.isfile(index_html):
        raise HTTPException(
            503,
            "Frontend is not built (missing frontend/dist or src/static). "
            "Run the Vite build or deploy/dev/start.*",
        )
    return FileResponse(
        index_html,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# 静态前端挂载在根路径（/@app 路由优先匹配 /api，其余回退到静态文件）
if os.path.isdir(STATIC):
    app.mount("/", StaticFiles(directory=STATIC), name="static")
