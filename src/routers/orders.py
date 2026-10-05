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
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from application.orders import (
    compose_orders_attribution,
    compose_orders_channel_insight,
)
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)
from models import Order, OrderItem, PmsCheckin, PmsIdDocAudit, User

router = APIRouter(tags=["orders"])


@router.get("/orders/sources")
def order_sources_meta():
    """订单中心来源 Tab 元数据。"""
    from orders.channel_config import SOURCE_META

    return ok(SOURCE_META)


@router.get("/orders/board")
def orders_board(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    """订单中心看板：按来源计数 + 增强入口提示。"""
    from application.orders import build_orders_board

    return ok(build_orders_board(db, hotel_id))


@router.get("/orders/attribution")
def orders_attribution(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """订单渠道归因分析：KPI / 旅程流转 / 高价值单溯源，尽量读库。"""
    from application.orders import compose_orders_attribution

    return ok(compose_orders_attribution(db, hotel_id, days))


@router.post("/orders/attribution/ai")
def orders_attribution_ai(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """手动触发：LLM 解读归因事实（规则兜底）。"""
    from application.analytics import narrate_attribution_insight

    data = compose_orders_attribution(db, hotel_id, days)
    facts = {
        "days": days,
        "kpi": data.get("kpi"),
        "path_summary": data.get("path_summary"),
        "paths": (data.get("paths") or [])[:10],
        "journey": {
            "first_touch": ((data.get("journey") or {}).get("first_touch") or [])[:5],
            "conversion": (data.get("journey") or {}).get("conversion"),
            "consideration": (data.get("journey") or {}).get("consideration"),
        },
        "rule_template_html": data.get("insight_html"),
    }
    return ok(narrate_attribution_insight(db, facts))


@router.get("/orders/channel-insight")
def orders_channel_insight(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(30, ge=7, le=90),
    room_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """全渠道订单洞察：排行 / 质量分档 / 趋势，全部来自 orders 聚合。"""
    return ok(compose_orders_channel_insight(db, hotel_id, days, room_type_id))


@router.post("/orders/channel-insight/ai")
def orders_channel_insight_ai(
    hotel_id: int = Depends(hotel_scope),
    days: int = Query(30, ge=7, le=90),
    room_type_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """手动触发：用系统配置的 LLM 解读渠道事实（规则兜底）。"""
    from application.analytics import narrate_channel_insight

    data = compose_orders_channel_insight(db, hotel_id, days, room_type_id)
    facts = {
        "days": data.get("days"),
        "window": data.get("window"),
        "kpi": data.get("kpi"),
        "channels": [
            {
                "name": b.get("label") or b.get("channel"),
                "bookings": b.get("bookings"),
                "conversion_pct": b.get("conv"),
                "adr": b.get("adr"),
            }
            for b in (data.get("bubbles") or [])[:15]
        ],
        "quality": [
            {
                "name": m.get("name"),
                "cancel_rate_pct": m.get("cancel_rate"),
                "adr": m.get("adr_value"),
                "bookings": m.get("bookings"),
            }
            for m in (data.get("matrix") or [])[:15]
        ],
        "rule_template_html": data.get("insight_html"),
    }
    return ok(narrate_channel_insight(db, facts))


@router.get("/orders/monitor")
def orders_monitor(
    hotel_id: int = Depends(hotel_scope),
    range: str = Query("7d", description="24h | 7d | 14d"),
    db: Session = Depends(get_db),
):
    """订单异常与流失预警看板。"""
    from application.orders import build_orders_monitor

    return ok(build_orders_monitor(db, hotel_id, range=range))


@router.get("/orders/ai-risks")
def orders_ai_risks(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    """订单列表嵌入用的 AI 风险标签（规则为主，轻量）。"""
    from application.analytics import build_analytics_context

    ctx = build_analytics_context(db, hotel_id)
    risks = ctx.get("order_risks") or []
    by_id = {r["order_id"]: r for r in risks if r.get("order_id")}
    return ok({"items": risks, "by_order_id": by_id, "as_of": ctx.get("as_of")})


@router.get("/orders/summary")
def orders_summary(
    hotel_id: int = Depends(hotel_scope),
    on_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from application.orders import orders_work_summary

    biz_date = date.fromisoformat(on_date) if on_date else date.today()
    return ok(orders_work_summary(db, hotel_id, biz_date))


@router.get("/orders")
def list_orders(
    hotel_id: int = Depends(hotel_scope),
    status: Optional[str] = None,
    channel_id: Optional[int] = None,
    source: Optional[str] = None,
    view: Optional[str] = Query(None, description="arrivals|inhouse|departures|all|created_today|unassigned|pending"),
    q: Optional[str] = None,
    order_no: Optional[str] = Query(None, description="PMS 订单号"),
    external_order_no: Optional[str] = Query(None, description="渠道订单号"),
    reception_no: Optional[str] = Query(None, description="预分房单号（JDD）"),
    room_no: Optional[str] = Query(None, description="房间号"),
    guest_name: Optional[str] = Query(None, description="联系人"),
    phone: Optional[str] = Query(None, description="手机号"),
    note: Optional[str] = Query(None, description="备注"),
    on_date: Optional[str] = Query(None, description="业务日期 YYYY-MM-DD"),
    room_type_id: Optional[int] = Query(None),
    payment_status: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """订单列表。传 page 时分页返回 {items,total,summary}；否则兼容旧版数组。"""
    from application.orders import list_orders_compat

    return ok(
        list_orders_compat(
            db,
            hotel_id,
            status=status,
            channel_id=channel_id,
            source=source,
            view=view,
            q=q,
            order_no=order_no,
            external_order_no=external_order_no,
            reception_no=reception_no,
            room_no=room_no,
            guest_name=guest_name,
            phone=phone,
            note=note,
            on_date=on_date,
            room_type_id=room_type_id,
            payment_status=payment_status,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/orders")
def create_order(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.orders import create_order as create_order_facade

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    ci = datetime.strptime(payload["check_in"], "%Y-%m-%d").date()
    co = datetime.strptime(payload["check_out"], "%Y-%m-%d").date()
    data = create_order_facade(
        db,
        hotel_id=hotel_id,
        guest_name=payload.get("guest_name", "散客"),
        phone=payload.get("phone"),
        room_type_id=int(payload["room_type_id"]),
        channel_id=payload.get("channel_id"),
        check_in=ci,
        check_out=co,
        rooms=int(payload.get("rooms", 1)),
        adults=int(payload.get("adults", 1)),
        children=int(payload.get("children", 0)),
        note=payload.get("note", ""),
        external_order_no=payload.get("external_order_no"),
        voucher_code=payload.get("voucher_code"),
        payment_status=payload.get("payment_status"),
        status=payload.get("status") or "confirmed",
        created_by=ctx.user_id or None,
    )
    return ok(data)


@router.post("/orders/walk-in")
def orders_walk_in(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.orders import walk_in_checkin

    payload["hotel_id"] = assert_hotel_access(payload.get("hotel_id"))
    data = walk_in_checkin(db, payload, ctx.user_id or None)
    return ok(data)


@router.post("/orders/voucher/lookup")
def orders_voucher_lookup(payload: dict, db: Session = Depends(get_db)):
    from application.orders import lookup_voucher

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    return ok(lookup_voucher(db, hotel_id, payload.get("voucher_code", "")))


@router.post("/orders/voucher/verify")
def orders_voucher_verify(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.orders import verify_voucher_and_order

    payload["hotel_id"] = assert_hotel_access(payload.get("hotel_id"))
    data = verify_voucher_and_order(db, payload, ctx.user_id or None)
    return ok(data)


@router.post("/orders/ota/sync")
def orders_ota_sync(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.orders import sync_ota_order

    payload["hotel_id"] = assert_hotel_access(payload.get("hotel_id"))
    data = sync_ota_order(db, payload, ctx.user_id or None)
    return ok(data)


@router.post("/orders/group")
def orders_group_create(payload: dict, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)):
    from application.orders import create_group_order

    payload["hotel_id"] = assert_hotel_access(payload.get("hotel_id"))
    data = create_group_order(db, payload, ctx.user_id or None)
    return ok(data)


@router.post("/orders/{order_id}/group-lines/{line_id}/assign")
def orders_group_line_assign(
    order_id: int,
    line_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.orders import assign_group_line

    data = assign_group_line(
        db,
        order_id,
        line_id,
        int(payload.get("room_id") or 0),
        operator_id=ctx.user_id or None,
    )
    return ok(data)


@router.post("/orders/{order_id}/group-lines/{line_id}/checkin")
def orders_group_line_checkin(
    order_id: int,
    line_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.orders import checkin_group_line

    data = checkin_group_line(
        db,
        order_id,
        line_id,
        room_id=payload.get("room_id"),
        guest_name=payload.get("guest_name"),
        id_doc_type=payload.get("id_doc_type"),
        id_doc_no=payload.get("id_doc_no") or payload.get("id_number"),
    )
    return ok(data)


@router.post("/orders/{order_id}/checkin")
def checkin(order_id: int, payload: dict = {}, db: Session = Depends(get_db)):
    from application.orders import checkin as checkin_facade

    data = checkin_facade(
        db,
        order_id,
        payload.get("room_id"),
        guest_name=payload.get("guest_name"),
        id_doc_type=payload.get("id_doc_type"),
        id_doc_no=payload.get("id_doc_no") or payload.get("id_number"),
    )
    return ok(data)


@router.post("/checkins/{checkin_id}/reveal-id-doc")
def reveal_id_doc(
    checkin_id: int,
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """高权限查看完整证件号。需管理员角色 + 二次密码校验；写不可删审计。"""
    from application.orders import reveal_checkin_id_doc
    from infra.compliance import require_reveal_privilege, verify_secondary_password, write_id_doc_audit
    from models import PmsCheckin

    ci = db.get(PmsCheckin, checkin_id)
    if not ci:
        raise HTTPException(404, "入住登记不存在")
    assert_hotel_access(ci.hotel_id)
    require_reveal_privilege(ctx)
    verify_secondary_password(db, ctx, str(payload.get("password") or ""))
    reason = str(payload.get("reason") or "前台核查")
    try:
        data = reveal_checkin_id_doc(
            db,
            checkin_id,
            operator_id=ctx.user_id or None,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    data["audited"] = True
    data["operator"] = ctx.username
    return ok(data)


@router.delete("/checkins/id-doc-audits/{audit_id}")
def delete_id_doc_audit_forbidden(
    audit_id: int,
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """证件揭密审计不可删除。"""
    raise HTTPException(403, "证件揭密审计日志不可删除，须留存不少于 6 个月")


@router.get("/compliance/status")
def compliance_status_api(
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from infra.compliance import compliance_status

    return ok(compliance_status(db, hotel_id, ctx))


@router.get("/compliance/id-doc-audits")
def list_id_doc_audits(
    hotel_id: int = Depends(hotel_scope),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from infra.compliance import require_reveal_privilege
    from models import PmsIdDocAudit, User

    require_reveal_privilege(ctx)
    rows = db.query(PmsIdDocAudit).filter_by(hotel_id=hotel_id).order_by(PmsIdDocAudit.id.desc()).limit(limit).all()
    out = []
    for a in rows:
        u = db.get(User, a.operator_id) if a.operator_id else None
        out.append(
            {
                "id": a.id,
                "checkin_id": a.checkin_id,
                "order_id": a.order_id,
                "action": a.action,
                "reason": a.reason,
                "operator": (u.full_name or u.username) if u else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return ok(out)


@router.post("/compliance/purge-expired-id-docs")
def purge_id_docs_api(
    payload: dict = {},
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    from application.orders import purge_expired_id_docs
    from infra.compliance import ID_DOC_RETAIN_YEARS, require_reveal_privilege

    require_reveal_privilege(ctx)
    years = int(payload.get("retain_years") or ID_DOC_RETAIN_YEARS)
    return ok(
        purge_expired_id_docs(
            db,
            hotel_id=ctx.hotel_id,
            operator_id=ctx.user_id,
            retain_years=years,
        )
    )


@router.post("/orders/{order_id}/checkout")
def checkout(order_id: int, payload: dict = {}, db: Session = Depends(get_db)):
    from application.orders import checkout as checkout_facade

    data = checkout_facade(
        db,
        order_id,
        payment_mode=str(payload.get("payment_mode") or "auto"),
        method=str(payload.get("method") or "wechat"),
        pos_slip_no=payload.get("pos_slip_no"),
    )
    return ok(data)


@router.post("/orders/{order_id}/cancel")
def cancel_order_api(order_id: int, payload: dict = {}, db: Session = Depends(get_db)):
    from application.orders import cancel_order as cancel_order_facade

    data = cancel_order_facade(db, order_id, payload.get("reason") or "")
    return ok(data)


@router.post("/orders/{order_id}/assign-room")
def assign_room_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import assign_room_only

    data = assign_room_only(db, order_id, int(payload["room_id"]), assigned_by=ctx.user_id or None)
    return ok(data)


@router.post("/orders/{order_id}/change-room")
def change_room_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import change_room

    data = change_room(db, order_id, int(payload["room_id"]), reason=str(payload.get("reason") or ""))
    return ok(data)


@router.post("/orders/{order_id}/extend")
def extend_stay_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import extend_stay

    data = extend_stay(
        db,
        order_id,
        int(payload.get("extra_nights") or payload.get("nights") or 1),
        daily_rate=payload.get("daily_rate"),
    )
    return ok(data)


@router.post("/orders/{order_id}/roommates")
def add_roommate_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import add_roommate

    data = add_roommate(
        db,
        order_id,
        guest_name=str(payload.get("guest_name") or ""),
        phone=payload.get("phone"),
        id_doc_type=str(payload.get("id_doc_type") or "id_card"),
        id_doc_no=payload.get("id_doc_no") or payload.get("id_number"),
    )
    return ok(data)


@router.post("/orders/{order_id}/folio/charge")
def folio_charge_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import add_folio_charge

    data = add_folio_charge(
        db,
        order_id,
        amount=float(payload.get("amount") or 0),
        description=str(payload.get("description") or "住中加收"),
        entry_type=str(payload.get("entry_type") or "misc"),
        operator_id=ctx.user_id or None,
    )
    return ok(data)


@router.post("/orders/{order_id}/folio/pay")
def folio_pay_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import collect_payment

    data = collect_payment(
        db,
        order_id,
        amount=float(payload.get("amount") or 0),
        method=str(payload.get("method") or "wechat_pos"),
        pos_slip_no=payload.get("pos_slip_no"),
        settle_type=str(payload.get("settle_type") or "partial"),
        operator_id=ctx.user_id or None,
        note=str(payload.get("note") or ""),
    )
    return ok(data)


@router.post("/orders/{order_id}/no-show")
def no_show_api(
    order_id: int, payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import mark_no_show

    data = mark_no_show(db, order_id, reason=str(payload.get("reason") or ""))
    return ok(data)


@router.get("/orders/{order_id}/rc")
def order_rc_card(
    order_id: int,
    reveal: bool = False,
    password: Optional[str] = Query(None),
    reason: str = Query("打印登记单核验"),
    db: Session = Depends(get_db),
    ctx: AppContext = Depends(get_current_user),
):
    """RC 入住登记单。默认脱敏；reveal=1 需高权限+二次密码并写审计。"""
    from application.orders import rc_registration_card, rc_registration_card_revealed
    from infra.compliance import require_reveal_privilege, verify_secondary_password
    from models import Order

    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "订单不存在")
    assert_hotel_access(o.hotel_id)
    if reveal:
        require_reveal_privilege(ctx)
        verify_secondary_password(db, ctx, password or "")
        return ok(
            rc_registration_card_revealed(
                db,
                order_id,
                hotel_id=o.hotel_id,
                operator_id=ctx.user_id,
                reason=reason or "打印登记单核验",
            )
        )
    return ok(rc_registration_card(db, order_id, reveal=False))


@router.post("/longstay/monthly-rent")
def longstay_monthly_rent(
    payload: dict = {}, db: Session = Depends(get_db), ctx: AppContext = Depends(get_current_user)
):
    from application.orders import post_longstay_monthly_rent

    hotel_id = assert_hotel_access(payload.get("hotel_id") or ctx.hotel_id)
    as_of = payload.get("as_of")
    d = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else date.today()
    data = post_longstay_monthly_rent(db, hotel_id, as_of=d)
    return ok(data)


# ---------------- 订单 / 房间 详情（钻取用） ----------------
@router.get("/orders/{order_id}")
def order_detail(order_id: int, db: Session = Depends(get_db)):
    from application.orders import list_order_checkins, order_detail_dict
    from models import Order, OrderItem

    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "订单不存在")
    d = order_detail_dict(db, o)
    d["items"] = [row_to_dict(i) for i in db.query(OrderItem).filter_by(order_id=o.id)]
    d["checkins"] = list_order_checkins(db, o.id)
    return ok(d)
