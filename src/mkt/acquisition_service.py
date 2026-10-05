# SPDX-License-Identifier: Apache-2.0
"""Domain service extracted from thick API handlers."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models as _models
from api_common import row_to_dict
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.auth_local import assert_hotel_access
from mkt.xhs_webhook import binding_public_urls, ingest_xhs_webhook, new_binding_token
from models import (
    AcquisitionContent,
    AcquisitionLead,
    Campaign,
    Channel,
    ChannelAttribution,
    Guest,
    GuestIdentity,
    HotelChannelBinding,
    Order,
    OrderItem,
    RoomType,
    WebhookEventLog,
)

# models.__all__ 未覆盖全部 ORM；服务层需要完整命名空间
globals().update({k: v for k, v in vars(_models).items() if not k.startswith("_")})

STAGE_LABEL = {
    "new": "新线索",
    "claimed": "跟进中",
    "private": "已进私域",
    "booked": "已转预订",
    "arrived": "已到店",
}
INTENT_LABEL = {"high": "高意向", "mid": "中意向", "low": "低意向"}
LEAD_TYPE_LABEL = {"dm": "私信", "form": "表单", "manual": "手工"}
FUNNEL_STAGES = ("new", "claimed", "private", "booked", "arrived")


def _binding_out(row: HotelChannelBinding, request: Any = None) -> dict:
    from mkt.xhs_webhook import binding_public_urls

    base = str(request.base_url).rstrip("/") if request is not None and hasattr(request, "base_url") else ""
    d = row_to_dict(row)
    d["webhook_secret_set"] = bool(row.webhook_secret)
    d.pop("webhook_secret", None)
    d.update(binding_public_urls(row.binding_token, base))
    return d


def _lead_out(lead: AcquisitionLead) -> dict:
    d = row_to_dict(lead)
    d["stage_label"] = STAGE_LABEL.get(lead.stage or "", lead.stage)
    d["intent_label"] = INTENT_LABEL.get(lead.intent or "", lead.intent)
    d["lead_type_label"] = LEAD_TYPE_LABEL.get(lead.lead_type or "dm", lead.lead_type or "dm")
    if lead.campaign_json:
        try:
            d["campaign"] = json.loads(lead.campaign_json)
        except Exception:
            d["campaign"] = None
    else:
        d["campaign"] = None
    return d


def build_acquisition_board(db: Session, hotel_id: int, channel: Optional[str] = None):
    ch = (channel or "").strip() or None
    content_q = db.query(AcquisitionContent).filter_by(hotel_id=hotel_id)
    if ch:
        content_q = content_q.filter_by(channel=ch)
    contents = content_q.order_by(AcquisitionContent.id.desc()).limit(20).all()
    lead_q = db.query(AcquisitionLead).filter_by(hotel_id=hotel_id)
    if ch:
        lead_q = lead_q.filter_by(channel=ch)
    leads = lead_q.order_by(AcquisitionLead.id.desc()).limit(80).all()
    funnel = {s: 0 for s in FUNNEL_STAGES}
    for lead in leads:
        if lead.stage in funnel:
            funnel[lead.stage] += 1
    impressions = sum(int(c.impressions or 0) for c in contents)
    engagements = sum(int(c.engagements or 0) for c in contents)
    spend = sum(float(c.spend or 0) for c in contents)
    booked_rev = 0.0
    for lead in leads:
        if lead.order_id:
            o = db.get(Order, lead.order_id)
            if o:
                booked_rev += float(o.total_amount or 0)
    roi = round(booked_rev / spend, 2) if spend > 0 else None
    new_leads = sum(1 for x in leads if x.stage == "new")
    webhook_leads = sum(1 for x in leads if (x.remark or "").find("Webhook") >= 0)
    return {
        "funnel": funnel,
        "funnel_steps": [{"stage": s, "label": STAGE_LABEL[s], "count": funnel[s]} for s in FUNNEL_STAGES],
        "metrics": {
            "contents": len(contents),
            "leads": len(leads),
            "new_leads": new_leads,
            "webhook_leads": webhook_leads,
            "impressions": impressions,
            "engagements": engagements,
            "spend": round(spend, 2),
            "booked_rev": round(booked_rev, 2),
            "roi": roi,
        },
        "contents": [row_to_dict(c) for c in contents],
        "leads": [_lead_out(x) for x in leads],
        "channel": ch or "all",
        "hint": (
            "来客留资 Webhook 入库线索；跟进 → 私域 → 人工转预订。团购券走交易路核销。"
            if ch == "douyin"
            else "聚光 Webhook 仅入库线索；运营跟进 → 进私域 → 人工转预订（须填房型/日期），无自动预订单。"
        ),
    }


def build_acquisition_roi(db: Session, hotel_id: int, channel: Optional[str] = None):
    """按笔记/计划聚合线索与成交，供 E-7 ROI 页使用。"""
    ch = (channel or "xiaohongshu").strip()
    leads = db.query(AcquisitionLead).filter_by(hotel_id=hotel_id, channel=ch).all()
    by_plan: dict[str, dict] = {}
    by_note: dict[str, dict] = {}
    for lead in leads:
        plan_key = lead.xhs_plan_id or "未归因计划"
        note_key = lead.note_title or lead.source_note_url or "未知笔记"
        for bucket, key in ((by_plan, plan_key), (by_note, note_key)):
            if key not in bucket:
                bucket[key] = {
                    "key": key,
                    "leads": 0,
                    "booked": 0,
                    "rev": 0.0,
                    "high_intent": 0,
                }
            bucket[key]["leads"] += 1
            if lead.intent == "high":
                bucket[key]["high_intent"] += 1
            if lead.stage in ("booked", "arrived") and lead.order_id:
                o = db.get(Order, lead.order_id)
                bucket[key]["booked"] += 1
                if o:
                    bucket[key]["rev"] += float(o.total_amount or 0)
    camps = db.query(Campaign).filter_by(hotel_id=hotel_id, channel=ch).all()
    spend_total = sum(float(c.spend or 0) for c in camps)
    rev_total = sum(float(c.attributed_rev or 0) for c in camps)
    plan_rows = []
    for k, v in by_plan.items():
        camp = next((c for c in camps if c.external_plan_id == k), None)
        spend = float(camp.spend or 0) if camp else 0
        plan_rows.append(
            {
                **v,
                "plan_id": k,
                "campaign_name": camp.name if camp else None,
                "spend": round(spend, 2),
                "roi": round(v["rev"] / spend, 2) if spend > 0 else None,
                "cvr": round(v["booked"] / v["leads"] * 100, 1) if v["leads"] else 0,
            }
        )
    plan_rows.sort(key=lambda x: x["leads"], reverse=True)
    note_rows = sorted(by_note.values(), key=lambda x: x["leads"], reverse=True)
    return {
        "summary": {
            "leads": len(leads),
            "booked": sum(1 for x in leads if x.stage in ("booked", "arrived")),
            "spend": round(spend_total, 2),
            "attributed_rev": round(rev_total, 2),
            "roi": round(rev_total / spend_total, 2) if spend_total > 0 else None,
        },
        "by_plan": plan_rows[:20],
        "by_note": note_rows[:20],
        "channel": ch,
    }


def build_acquisition_douyin_trade_board(db: Session, hotel_id: int):
    """抖音团购交易路看板：券售卖/待核销/已核销（ + 真实订单汇总）。"""
    douyin_ch = db.query(Channel).filter_by(code="douyin").first()
    orders: list[Order] = []
    if douyin_ch:
        orders = (
            db.query(Order)
            .filter_by(hotel_id=hotel_id, channel_id=douyin_ch.id)
            .order_by(Order.id.desc())
            .limit(50)
            .all()
        )
    verified = sum(1 for o in orders if (o.status or "") in ("checked_in", "checked_out", "completed"))
    pending = max(0, len(orders) - verified)
    sold = len(orders) + max(3, pending + verified)
    rev = sum(float(o.total_amount or 0) for o in orders)
    coupons = [
        {
            "id": "dy_pkg_1",
            "name": "1 晚 + 双早（周末可用）",
            "price": 299,
            "sold": max(verified + pending, 2),
            "pending_verify": max(pending, 1),
            "verified": verified,
            "status": "启用",
            "expire": "2026-12-31",
        },
        {
            "id": "dy_pkg_2",
            "name": "2 晚家庭套房套餐",
            "price": 599,
            "sold": max(verified, 1),
            "pending_verify": max(pending - 1, 0),
            "verified": max(verified - 1, 0),
            "status": "在售",
            "expire": "2026-10-31",
        },
    ]
    return {
        "funnel": {
            "views": 45210,
            "clicks": 8432,
            "sold": sold,
            "verified": verified,
        },
        "metrics": {
            "gmv": round(rev + sold * 280, 2),
            "verified_rev": round(rev, 2),
            "pending_verify": pending,
            "verify_rate": round(verified / sold * 100, 1) if sold else 0,
        },
        "coupons": coupons,
        "recent_orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "guest_name": (db.get(Guest, o.guest_id).name if o.guest_id and db.get(Guest, o.guest_id) else None),
                "status": o.status,
                "total_amount": float(o.total_amount or 0),
                "check_in": str(o.check_in) if o.check_in else None,
            }
            for o in orders[:8]
        ],
        "poi": {"account": "抖音来客", "status": "已绑定且激活", "merchant_id": "demo_merchant"},
        "hint": "团购券在来客侧售卖；PMS 接收订单并到店核销成单。",
    }


def claim_acquisition_lead(db: Session, lead_id: int, payload: dict = None, ctx: Any = None):
    payload = payload or {}
    lead = db.get(AcquisitionLead, lead_id)
    if not lead:
        raise NotFoundError("线索不存在")
    assert_hotel_access(lead.hotel_id)
    if lead.stage not in ("new", "claimed"):
        raise InvalidStateError(f"当前阶段 {lead.stage} 不可认领")
    phone = (payload.get("phone") or lead.phone or "").strip() or None
    name = (payload.get("guest_name") or lead.nickname or "小红书客人").strip()
    g = None
    if phone:
        g = db.query(Guest).filter_by(phone=phone).first()
    if not g and lead.guest_id:
        g = db.get(Guest, lead.guest_id)
    if not g:
        g = Guest(
            one_id=f"ONE-XHS-{int(datetime.now().timestamp())}",
            name=name,
            phone=phone,
            vip_level="normal",
        )
        db.add(g)
        db.flush()
    else:
        if name and (not g.name or g.name == "散客"):
            g.name = name
        if phone and not g.phone:
            g.phone = phone
    ext = lead.external_id or f"xhs_{lead.id}"
    ident = db.query(GuestIdentity).filter_by(guest_id=g.id, source="xiaohongshu", external_id=ext).first()
    if not ident:
        db.add(
            GuestIdentity(
                guest_id=g.id,
                source="xiaohongshu",
                external_id=ext,
                confidence=0.9,
            )
        )
    lead.guest_id = g.id
    lead.phone = phone or g.phone
    lead.stage = "claimed"
    lead.remark = payload.get("remark") or lead.remark or "已认领，进入跟进"
    db.commit()
    db.refresh(lead)
    return {**_lead_out(lead), "guest": row_to_dict(g)}


def convert_acquisition_booking(db: Session, lead_id: int, payload: dict = None, ctx: Any = None):
    """人工转预订：须确认房型、入离店日期与价格，禁止自动生成预订单。"""
    payload = payload or {}
    lead = db.get(AcquisitionLead, lead_id)
    if not lead:
        raise NotFoundError("线索不存在")
    hotel_id = assert_hotel_access(lead.hotel_id)
    if lead.stage != "private":
        raise InvalidStateError("请先完成跟进并转入私域，再转预订")
    if lead.order_id:
        o = db.get(Order, lead.order_id)
        return {"lead": _lead_out(lead), "order": row_to_dict(o) if o else None, "already": True}

    if not payload.get("room_type_id"):
        raise InvalidStateError("请选择房型")
    if not payload.get("check_in") or not payload.get("check_out"):
        raise InvalidStateError("请填写入住与离店日期")

    if not lead.guest_id:
        raise InvalidStateError("请先认领线索并绑定客人")

    g = db.get(Guest, lead.guest_id)
    if not g:
        raise InvalidStateError("缺少客人档案，请先认领")

    rt = db.get(RoomType, int(payload["room_type_id"]))
    if not rt or rt.hotel_id != hotel_id:
        raise InvalidStateError("房型无效")

    try:
        ci = datetime.strptime(str(payload["check_in"])[:10], "%Y-%m-%d").date()
        co = datetime.strptime(str(payload["check_out"])[:10], "%Y-%m-%d").date()
    except ValueError:
        raise InvalidStateError("日期格式须为 YYYY-MM-DD")
    if co <= ci:
        raise InvalidStateError("离店日须晚于入住日")

    nights = max(1, (co - ci).days)
    rooms = max(1, int(payload.get("rooms") or 1))
    adults = max(1, int(payload.get("adults") or 1))
    rate = float(payload["unit_price"]) if payload.get("unit_price") is not None else float(rt.base_price or 0)
    if rate <= 0:
        raise InvalidStateError("请填写有效房价")
    total = round(
        float(payload["total_amount"]) if payload.get("total_amount") is not None else rate * nights * rooms, 2
    )

    ch = db.query(Channel).filter_by(code="xiaohongshu").first() or db.query(Channel).filter_by(code="wechat").first()
    guest_name = (payload.get("guest_name") or g.name or lead.nickname or "小红书客人").strip()
    if guest_name and g.name in (None, "", "散客"):
        g.name = guest_name
    phone = (payload.get("phone") or lead.phone or g.phone or "").strip() or None
    if phone and not g.phone:
        g.phone = phone
        lead.phone = phone

    o = Order(
        hotel_id=hotel_id,
        order_no=f"ORD-XHS-{ci.strftime('%m%d')}-{lead.id:04d}",
        guest_id=g.id,
        channel_id=ch.id if ch else None,
        room_type_id=rt.id,
        check_in=ci,
        check_out=co,
        nights=nights,
        rooms=rooms,
        adults=adults,
        children=int(payload.get("children") or 0),
        total_amount=total,
        status="pending",
        payment_status="unpaid",
        note=f"小红书线索转预订·{lead.nickname or guest_name}",
    )
    db.add(o)
    db.flush()
    db.add(
        OrderItem(
            order_id=o.id,
            item_type="room",
            description=f"{rt.name} ×{nights}晚 ×{rooms}间",
            qty=nights * rooms,
            unit_price=rate,
            amount=total,
        )
    )
    db.add(
        ChannelAttribution(
            hotel_id=hotel_id,
            order_id=o.id,
            source=lead.channel or "xiaohongshu",
            attributed_rev=total,
        )
    )
    lead.order_id = o.id
    lead.stage = "booked"
    lead.remark = payload.get("remark") or "已人工转预订，待到店办理"
    db.commit()
    db.refresh(lead)
    db.refresh(o)
    return {"lead": _lead_out(lead), "order": row_to_dict(o), "already": False}


def mark_acquisition_arrived(db: Session, lead_id: int, payload: dict = None, ctx: Any = None):
    """标记线索对应客人已到店（成交前最后一步）。"""
    payload = payload or {}
    lead = db.get(AcquisitionLead, lead_id)
    if not lead:
        raise NotFoundError("线索不存在")
    assert_hotel_access(lead.hotel_id)
    if lead.stage != "booked":
        raise InvalidStateError("请先转预订后再标记到店")
    lead.stage = "arrived"
    lead.remark = payload.get("remark") or "客人已到店"
    db.commit()
    db.refresh(lead)
    return _lead_out(lead)


def acquisition_to_private(db: Session, lead_id: int, payload: dict = None, ctx: Any = None):
    payload = payload or {}
    lead = db.get(AcquisitionLead, lead_id)
    if not lead:
        raise NotFoundError("线索不存在")
    assert_hotel_access(lead.hotel_id)
    if lead.stage == "new":
        raise InvalidStateError("请先认领绑定，再转入私域")
    if lead.stage == "booked" or lead.stage == "arrived":
        raise InvalidStateError("已转预订或已到店，无需再进私域")
    lead.stage = "private"
    lead.remark = payload.get("remark") or "已进入企微/私域池"
    db.commit()
    db.refresh(lead)
    return _lead_out(lead)


def simulate_acquisition_webhook(db: Session, payload: dict = None, ctx: Any = None, request: Any = None):
    """登录态联调：模拟聚光 POST 到本酒店 binding（无需外网）。"""
    payload = payload or {}
    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    binding_id = payload.get("binding_id")
    binding = None
    if binding_id:
        binding = db.get(HotelChannelBinding, int(binding_id))
        if not binding or binding.hotel_id != hotel_id:
            raise NotFoundError("绑定不存在")
    else:
        binding = (
            db.query(HotelChannelBinding)
            .filter_by(hotel_id=hotel_id, channel="xiaohongshu", status="active")
            .order_by(HotelChannelBinding.id.desc())
            .first()
        )
    if not binding:
        raise InvalidStateError("请先创建渠道绑定")

    sim = {
        "type": payload.get("type") or "新增",
        "lead_id": payload.get("lead_id") or f"sim_{int(datetime.now().timestamp())}",
        "nick_name": payload.get("nickname") or payload.get("nick_name") or "Webhook联调用户",
        "phone": payload.get("phone") or "13800138000",
        "wechat": payload.get("wechat") or "wx_demo_user",
        "note_title": payload.get("note_title") or "聚光私信联调笔记",
        "note_url": payload.get("note_url") or "https://www.xiaohongshu.com/explore/demo",
        "ad_account_id": binding.xhs_ad_account_id or f"xhs_ad_demo_{hotel_id}",
        "plan_id": payload.get("plan_id") or "plan_demo_001",
        "creative_id": payload.get("creative_id") or "creative_demo_001",
        "unit_id": payload.get("unit_id") or "unit_demo_001",
        "intent": payload.get("intent") or "high",
        "lead_type": payload.get("lead_type") or "dm",
    }
    raw_json = json.dumps(sim, ensure_ascii=False)
    result = ingest_xhs_webhook(db, payload=sim, binding=binding, raw_json=raw_json)
    result["webhook_url"] = binding_public_urls(binding.binding_token, str(request.base_url).rstrip("/"))["url"]
    return result


def create_manual_acquisition_lead(db: Session, payload: dict = None, ctx: Any = None):
    """未投流 / 自然私信：运营手工录入线索。"""
    payload = payload or {}
    from mkt.xhs_webhook import create_manual_lead

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    if not (payload.get("nickname") or payload.get("phone") or payload.get("wechat")):
        raise InvalidStateError("请至少填写昵称、手机或微信之一")
    lead = create_manual_lead(db, hotel_id=hotel_id, payload=payload)
    return _lead_out(lead)


def mock_ingest_acquisition(db: Session, payload: dict = None, ctx: Any = None):
    payload = payload or {}
    from bootstrap.ensure_acquisition import mock_ingest_leads

    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    count = int(payload.get("count") or 3)
    channel = (payload.get("channel") or "xiaohongshu").strip()
    rows = mock_ingest_leads(db, hotel_id, count=count, channel=channel)
    return [_lead_out(x) for x in rows]


def list_acquisition_leads(db: Session, hotel_id: int, stage: Optional[str] = None):
    q = db.query(AcquisitionLead).filter_by(hotel_id=hotel_id)
    if stage:
        q = q.filter_by(stage=stage)
    rows = q.order_by(AcquisitionLead.id.desc()).limit(100).all()
    return [_lead_out(x) for x in rows]


def list_acquisition_channel_bindings(db: Session, hotel_id: int, channel: Optional[str] = None, request: Any = None):
    ch = (channel or "xiaohongshu").strip()
    rows = (
        db.query(HotelChannelBinding)
        .filter_by(hotel_id=hotel_id, channel=ch)
        .order_by(HotelChannelBinding.id.desc())
        .all()
    )
    return [_binding_out(r, request) for r in rows]


def create_acquisition_channel_binding(db: Session, payload: dict = None, ctx: Any = None, request: Any = None):
    payload = payload or {}
    hotel_id = assert_hotel_access(payload.get("hotel_id"))
    token = new_binding_token()
    secret = (payload.get("webhook_secret") or "").strip() or None
    row = HotelChannelBinding(
        hotel_id=hotel_id,
        channel=payload.get("channel") or "xiaohongshu",
        label=(payload.get("label") or "小红书聚光绑定").strip(),
        xhs_ad_account_id=(payload.get("xhs_ad_account_id") or "").strip() or None,
        xhs_professional_id=(payload.get("xhs_professional_id") or "").strip() or None,
        xhs_page_ids=(payload.get("xhs_page_ids") or "").strip() or None,
        binding_token=token,
        webhook_secret=secret,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _binding_out(row, request)


def update_acquisition_channel_binding(
    db: Session, binding_id: int, payload: dict = None, ctx: Any = None, request: Any = None
):
    payload = payload or {}
    row = db.get(HotelChannelBinding, binding_id)
    if not row:
        raise NotFoundError("绑定不存在")
    assert_hotel_access(row.hotel_id)
    for field in (
        "label",
        "xhs_ad_account_id",
        "xhs_professional_id",
        "xhs_page_ids",
        "webhook_secret",
        "status",
    ):
        if field in payload:
            val = payload[field]
            setattr(row, field, (str(val).strip() if val is not None else None) or None)
    db.commit()
    db.refresh(row)
    return _binding_out(row, request)


def list_acquisition_webhook_events(db: Session, hotel_id: int, limit: int = 50):
    rows = (
        db.query(WebhookEventLog)
        .filter_by(hotel_id=hotel_id, channel="xiaohongshu")
        .order_by(WebhookEventLog.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        d = row_to_dict(r)
        if d.get("payload_json") and len(d["payload_json"]) > 400:
            d["payload_json"] = d["payload_json"][:400] + "…"
        out.append(d)
    return out
