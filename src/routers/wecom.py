# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import logging
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

log = logging.getLogger(__name__)
router = APIRouter(tags=["wecom"])


class WecomSendPayload(BaseModel):
    guest_id: int
    content: str


@router.get("/wecom/config")
def get_wecom_config(db: Session = Depends(get_db)):
    from application.wecom import load_wecom_config_masked

    return ok(load_wecom_config_masked(db))


@router.put("/wecom/config")
def put_wecom_config(payload: dict, db: Session = Depends(get_db)):
    from application.wecom import save_wecom_config

    return ok(save_wecom_config(db, payload))


@router.post("/wecom/config/test")
def post_wecom_config_test(db: Session = Depends(get_db)):
    from application.wecom import test_wecom_connection

    return ok(test_wecom_connection(db))


@router.post("/wecom/sync-contacts")
def post_wecom_sync_contacts(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.wecom import sync_external_contacts

    return ok(sync_external_contacts(db, hotel_id))


@router.get("/wecom/jssdk-sign")
def wecom_jssdk_sign(url: str = Query(..., description="当前页 URL（不含 # 后片段）"), db: Session = Depends(get_db)):
    """企微 JS-SDK 签名（聊天工具栏，免登录）。"""
    from application.wecom import build_jssdk_signatures

    return ok(build_jssdk_signatures(db, url))


@router.get("/wecom/sidebar/guest")
def wecom_sidebar_guest(external_userid: str = Query(...), db: Session = Depends(get_db)):
    """聊天工具栏：按 external_userid 加载客人摘要（免登录）。"""
    from application.wecom import sidebar_guest_by_external_userid

    return ok(sidebar_guest_by_external_userid(db, external_userid))


class WecomSidebarCareDraftPayload(BaseModel):
    external_userid: str
    material: str = ""


@router.post("/wecom/sidebar/care-draft")
def wecom_sidebar_care_draft(payload: WecomSidebarCareDraftPayload, db: Session = Depends(get_db)):
    from wecom.wecom_service import draft_wecom_care_message, sidebar_guest_by_external_userid

    summary = sidebar_guest_by_external_userid(db, payload.external_userid)
    return ok(draft_wecom_care_message(db, summary["guest_id"], payload.material))


class WecomSidebarCareSentPayload(BaseModel):
    external_userid: str
    content: str
    sender_userid: Optional[str] = None


@router.post("/wecom/sidebar/care-sent")
def wecom_sidebar_care_sent(payload: WecomSidebarCareSentPayload, db: Session = Depends(get_db)):
    from application.wecom import log_sidebar_care_sent

    return ok(log_sidebar_care_sent(db, payload.external_userid, payload.content, payload.sender_userid))


@router.post("/wecom/send")
def post_wecom_send(
    payload: WecomSendPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.wecom import send_single_message

    return ok(send_single_message(db, hotel_id, payload.guest_id, payload.content))


@router.get("/wecom/tasks")
def get_wecom_tasks(
    hotel_id: int = Depends(hotel_scope),
    guest_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from application.wecom import list_msg_tasks

    return ok(list_msg_tasks(db, hotel_id, guest_id=guest_id))


class WecomSimulateScanPayload(BaseModel):
    external_userid: Optional[str] = None


@router.post("/wecom/simulate-scan")
def post_wecom_simulate_scan(
    payload: WecomSimulateScanPayload = WecomSimulateScanPayload(),
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """：模拟「客人刚扫码加好友」→ 发定制绑定消息。"""
    from application.wecom import simulate_friend_scan

    return ok(simulate_friend_scan(db, hotel_id, payload.external_userid))


@router.get("/wecom/msg-result")
def get_wecom_msg_result(
    msgid: Optional[str] = None,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """查询最近一次（或指定 msgid）企业群发是否真正送达客户。"""
    from application.wecom import query_groupmsg_result

    _ = hotel_id
    return ok(query_groupmsg_result(db, msgid))


@router.get("/wecom/bind-tickets")
def get_wecom_bind_tickets(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.wecom import list_bind_tickets

    return ok(list_bind_tickets(db, hotel_id))


# ==================== 营销获客 MVP API ====================


@router.get("/wecom/private/overview")
def wecom_private_overview(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """私域总览权威聚合（与 /api/mkt/dashboard 同源）。"""
    from application.mkt import private_overview

    return ok(private_overview(db, hotel_id))


@router.get("/wecom/bind/info")
def wecom_bind_info(t: str = Query(...), db: Session = Depends(get_db)):
    from application.wecom import get_bind_ticket_public

    return ok(get_bind_ticket_public(db, t))


@router.get("/wecom/portal")
def wecom_guest_portal(request: Request, t: str = Query(...), db: Session = Depends(get_db)):
    """客人会员中心：票据定位 + Cookie/OAuth 专属校验。"""
    from application.wecom import get_guest_portal
    from wecom.wecom_portal_auth import PORTAL_COOKIE

    return ok(get_guest_portal(db, t, session_raw=request.cookies.get(PORTAL_COOKIE), require_auth=True))


class WecomBindSubmit(BaseModel):
    t: str
    phone: str


@router.post("/wecom/bind/submit")
def wecom_bind_submit(request: Request, payload: WecomBindSubmit, db: Session = Depends(get_db)):
    """领券提交：归集 + 发券 + 签发专属会员中心 Cookie。"""
    from fastapi.responses import JSONResponse

    from messaging import submit_bind_phone
    from wecom.wecom_portal_auth import PORTAL_COOKIE, PORTAL_TTL_SEC
    from wecom.wecom_service import load_wecom_config

    data = submit_bind_phone(payload.t, payload.phone, db=db)
    body = {"ok": True, "data": data}
    resp = JSONResponse(body)
    sess = (data or {}).get("portal_session") or ""
    if sess and data.get("ok") is not False and data.get("status") != "conflict":
        cfg = load_wecom_config(db)
        secure = str(request.url.scheme).lower() == "https" or "https://" in (cfg.get("public_base_url") or "")
        resp.set_cookie(
            key=PORTAL_COOKIE,
            value=sess,
            max_age=PORTAL_TTL_SEC,
            httponly=True,
            samesite="lax",
            secure=secure,
            path="/",
        )
    return resp


@router.api_route("/api/wecom/callback", methods=["GET", "POST"])
async def wecom_callback(
    request: Request,
    msg_signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
    echostr: str = Query(None),
    db: Session = Depends(get_db),
):
    """企微客户联系事件回调：先入收件箱，异步发欢迎语 / 触发后续归集。"""
    from fastapi.responses import PlainTextResponse

    from infra.auth_local import DEFAULT_HOTEL_ID
    from messaging import enqueue_callback
    from wecom.wecom_service import load_wecom_config

    cfg = load_wecom_config(db)
    token = cfg.get("callback_token") or ""
    aes_key = cfg.get("callback_aes_key") or ""
    corp_id = cfg.get("corp_id") or ""

    # URL 验证
    if request.method == "GET":
        if not aes_key:
            return PlainTextResponse(echostr or "ok")
        try:
            from wecom.wecom_crypto import WecomMsgCrypt

            crypt = WecomMsgCrypt(token, aes_key, corp_id)
            plain = crypt.verify_url(msg_signature or "", timestamp or "", nonce or "", echostr or "")
            return PlainTextResponse(plain)
        except Exception as e:
            raise HTTPException(403, f"回调 URL 验证失败：{e}")

    body = (await request.body()).decode("utf-8", errors="replace")
    event = {}
    try:
        if aes_key:
            from wecom.wecom_crypto import WecomMsgCrypt, parse_event_xml

            crypt = WecomMsgCrypt(token, aes_key, corp_id)
            xml = crypt.decrypt_message(msg_signature or "", timestamp or "", nonce or "", body)
            event = parse_event_xml(xml)
        else:
            from application.wecom import parse_event_xml

            event = parse_event_xml(body) if body.strip().startswith("<") else {}
    except Exception as e:
        log.warning("wecom callback decrypt/parse failed: %s", e)
        return PlainTextResponse("success")

    try:
        enqueue_callback(event or {}, db=db, hotel_id=DEFAULT_HOTEL_ID)
    except Exception as e:
        log.warning("wecom callback enqueue failed: %s", e)

    return PlainTextResponse("success")


@router.get("/wecom/callback-inbox")
def wecom_callback_inbox(
    hotel_id: int = Depends(hotel_scope),
    limit: int = Query(30, ge=1, le=100),
    include_deleted: bool = Query(False, description="是否包含已逻辑删除的回调记录"),
    db: Session = Depends(get_db),
):
    from application.wecom import list_callback_inbox

    return ok(list_callback_inbox(db, hotel_id, limit=limit, include_deleted=include_deleted))


@router.get("/wecom/landing/{page_key}")
def wecom_landing_page(
    page_key: str,
    t: str = Query(""),
    hotel_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """通用落地页渲染：配置来自装修器，券面值运行时读券池。"""
    from fastapi.responses import HTMLResponse

    from infra.auth_local import DEFAULT_HOTEL_ID
    from mkt.mkt_service import get_published_landing, render_landing_html

    page = get_published_landing(db, page_key, hotel_id=hotel_id or DEFAULT_HOTEL_ID)
    return HTMLResponse(render_landing_html(db, page, token=t))


@router.get("/wecom/oauth/callback")
def wecom_oauth_callback(
    request: Request,
    code: str = Query(""),
    state: str = Query(""),
    db: Session = Depends(get_db),
):
    """企微网页授权回调：校验 external_userid 与票据一致后签发专属 Cookie。"""
    from fastapi.responses import RedirectResponse

    from application.wecom import (
        exchange_oauth_identity,
        get_bind_ticket_by_token,
        issue_portal_session,
    )
    from wecom.wecom_portal_auth import PORTAL_COOKIE, PORTAL_TTL_SEC
    from wecom.wecom_service import _http_json, _portal_url, load_wecom_config

    ticket_token = (state or "").strip()
    if not code or not ticket_token:
        raise HTTPException(400, "授权参数不完整")
    ticket = get_bind_ticket_by_token(db, ticket_token)
    if not ticket or not ticket.guest_id:
        raise HTTPException(404, "绑定票据无效，请从欢迎语重新打开")
    cfg = load_wecom_config(db)
    ident = exchange_oauth_identity(cfg, code, _http_json)
    eid = ident.get("external_userid") or ""
    if not eid:
        raise HTTPException(
            403,
            "未能识别企微客户身份。请使用添加管家的同一个微信打开，并确保应用已开通客户联系权限。",
        )
    if eid != (ticket.external_userid or "").strip():
        raise HTTPException(403, "身份不匹配：这不是您的专属会员中心（可能打开了他人转发的链接）")
    sess = issue_portal_session(
        external_userid=eid,
        guest_id=ticket.guest_id,
        ticket_token=ticket.token,
    )
    dest = _portal_url(cfg, ticket.token)
    secure = str(request.url.scheme).lower() == "https" or "https://" in (cfg.get("public_base_url") or "")
    resp = RedirectResponse(url=dest, status_code=302)
    resp.set_cookie(
        key=PORTAL_COOKIE,
        value=sess,
        max_age=PORTAL_TTL_SEC,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )
    return resp


@router.get("/wecom/portal")
def wecom_portal_page(t: str = Query(""), db: Session = Depends(get_db)):
    """兼容旧链接：302 到装修发布的会员中心页（不再返回写死 HTML）。"""
    from urllib.parse import quote

    from fastapi.responses import RedirectResponse

    from application.wecom import get_bind_ticket_by_token
    from infra.auth_local import DEFAULT_HOTEL_ID
    from wecom.wecom_service import _resolve_member_landing_page_key

    hotel_id = DEFAULT_HOTEL_ID
    token = (t or "").strip()
    if token:
        ticket = get_bind_ticket_by_token(db, token)
        if ticket and ticket.hotel_id:
            hotel_id = ticket.hotel_id
    page_key = _resolve_member_landing_page_key(db, hotel_id)
    qs = []
    if token:
        qs.append(f"t={quote(token)}")
    qs.append(f"hotel_id={int(hotel_id)}")
    return RedirectResponse(url=f"/wecom/landing/{page_key}?" + "&".join(qs), status_code=302)


@router.get("/wecom/bind")
def wecom_bind_page(t: str = Query(""), db: Session = Depends(get_db)):
    """兼容旧链接：跳转到门店配置的装修落地页（不再返回写死 HTML）。"""
    from fastapi.responses import RedirectResponse

    from infra.auth_local import DEFAULT_HOTEL_ID
    from wecom.wecom_service import _resolve_welcome_landing_page_key

    hotel_id = DEFAULT_HOTEL_ID
    if t:
        try:
            from application.wecom import get_bind_ticket_by_token

            ticket = get_bind_ticket_by_token(db, t)
            if ticket and ticket.hotel_id:
                hotel_id = ticket.hotel_id
        except Exception:
            pass
    page_key = _resolve_welcome_landing_page_key(db, hotel_id)
    qs = [f"hotel_id={hotel_id}"]
    if t:
        qs.insert(0, f"t={t}")
    return RedirectResponse(url=f"/wecom/landing/{page_key}?" + "&".join(qs), status_code=302)
