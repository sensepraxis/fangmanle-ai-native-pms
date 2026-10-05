# SPDX-License-Identifier: Apache-2.0
"""企业微信客户联系：配置、同步外部联系人、一对一消息任务。"""

from __future__ import annotations

import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException  # noqa: F401
from sqlalchemy.orm import Session

from bootstrap.ensure_wecom import DEFAULT_WECOM_CONFIG, WECOM_SETTING_KEY
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from guests.i18n_cn import source_cn
from guests.phone_utils import (
    _digits,
    _normalize_cn_mobile,
    _normalize_phone_storage,
    _phone_last4,
    _phone_last6,
    find_guests_by_phone_exact,
    find_guests_by_phone_last4,
    find_guests_by_phone_last6,
)
from mkt.wallet_service import (
    _coupon_offer_public,
    _coupon_to_public,
    _is_private_domain_coupon,
    build_member_coupon_wallet,
    list_guest_coupons,
    lookup_coupon_by_code,
    redeem_guest_coupon,
)
from models import (
    AppSetting,
    Guest,
    GuestCoupon,
    GuestIdentity,
    GuestTag,
    Hotel,
    MktCouponGrant,
    OneIdMergeEvent,
    OneIdPhoneConflict,
    Order,
    Review,
    RoomType,
    TagDefinition,
    WecomBindTicket,
    WecomCallbackEvent,
    WecomMsgTask,
)

QYAPI = "https://qyapi.weixin.qq.com/cgi-bin"
VIP_LABEL_CN: dict[str, str] = {
    "normal": "普通会员",
    "silver": "白银会员",
    "gold": "黄金会员",
    "platinum": "铂金会员",
    "普通": "普通会员",
}
ROOM_PREF_RE = re.compile(
    "安静|静音|无烟|高楼|高层|低楼|低层|景观|山景|江景|海景|枕头|乳胶|硬枕|软枕|荞麦|矿泉水|夜床|开夜床|管家|亲子|家庭|儿童|加床|无障碍"
)
MARKETING_TAG_RE = re.compile("抖音|小红书|种草|粉丝|直播|投放|获客")
ORDER_ST_CN_H5: dict[str, str] = {
    "pending": "待入住",
    "confirmed": "已确认",
    "checked_in": "在住",
    "checked_out": "已离店",
    "cancelled": "已取消",
    "no_show": "未到",
    "in_house": "在住",
    "reserved": "已预订",
}


def guest_wecom_summary(db: Session, guest_id: int) -> dict | None:
    ident = (
        db.query(GuestIdentity)
        .filter_by(guest_id=guest_id, source="wecom")
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    coupons = list_guest_coupons(db, guest_id)
    if not ident and (not coupons):
        return None
    in_private = bool(ident)
    return {
        "bound": in_private,
        "channel_bound": in_private,
        "channel_reachable": in_private,
        "in_wecom_private": in_private,  # compat
        "external_userid": ident.external_id if ident else None,
        "follow_userid": ident.matched_by if ident else None,
        "linked_at": ident.linked_at.isoformat(sep=" ", timespec="seconds") if ident and ident.linked_at else None,
        "merge_method": ident.merge_method if ident else None,
        "confidence": float(ident.confidence) if ident and ident.confidence is not None else None,
        "coupons": coupons,
    }


def _resolve_welcome_landing_page_key(db: Session, hotel_id: int | None) -> str:
    """扫码欢迎语领券页：优先门店配置的装修落地页，否则 page_key=bind。"""
    if hotel_id:
        try:
            from models import HotelMktSettings, WxLandingPage

            settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
            if settings and settings.welcome_landing_page_id:
                page = db.get(WxLandingPage, settings.welcome_landing_page_id)
                if page and page.status == "published" and page.page_key:
                    return str(page.page_key)
            bind = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="bind", status="published").first()
            if bind:
                return "bind"
        except Exception:
            pass
    return "bind"


def _bind_url(cfg: dict, token: str, *, db: Session | None = None, hotel_id: int | None = None) -> str:
    base = (cfg.get("public_base_url") or "http://127.0.0.1:8000").rstrip("/")
    page_key = "bind"
    if db is not None:
        page_key = _resolve_welcome_landing_page_key(db, hotel_id)
    qs = f"t={urllib.parse.quote(token)}"
    if hotel_id:
        qs += f"&hotel_id={int(hotel_id)}"
    return f"{base}/wecom/landing/{page_key}?{qs}"


def _resolve_member_landing_page_key(db: Session, hotel_id: int | None) -> str:
    """会员中心装修页：优先门店配置，否则 page_key=member。"""
    if hotel_id:
        try:
            from models import HotelMktSettings, WxLandingPage

            settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
            mid = getattr(settings, "member_landing_page_id", None) if settings else None
            if mid:
                page = db.get(WxLandingPage, mid)
                if page and page.status == "published" and page.page_key:
                    return str(page.page_key)
            row = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="member", status="published").first()
            if row:
                return "member"
            any_m = (
                db.query(WxLandingPage)
                .filter_by(hotel_id=hotel_id, page_role="member", status="published")
                .order_by(WxLandingPage.id.desc())
                .first()
            )
            if any_m and any_m.page_key:
                return str(any_m.page_key)
        except Exception:
            pass
    return "member"


def _resolve_returning_landing_page_key(db: Session, hotel_id: int | None) -> str:
    """老客回访装修页：优先门店配置，否则 page_key=returning。"""
    if hotel_id:
        try:
            from models import HotelMktSettings, WxLandingPage

            settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
            rid = getattr(settings, "returning_landing_page_id", None) if settings else None
            if rid:
                page = db.get(WxLandingPage, rid)
                if page and page.status == "published" and page.page_key:
                    return str(page.page_key)
            row = db.query(WxLandingPage).filter_by(hotel_id=hotel_id, page_key="returning", status="published").first()
            if row:
                return "returning"
            any_r = (
                db.query(WxLandingPage)
                .filter_by(hotel_id=hotel_id, page_role="returning", status="published")
                .order_by(WxLandingPage.id.desc())
                .first()
            )
            if any_r and any_r.page_key:
                return str(any_r.page_key)
        except Exception:
            pass
    return "returning"


def _portal_url(cfg: dict, token: str, *, db: Session | None = None, hotel_id: int | None = None) -> str:
    """会员中心 URL：指向装修发布的会员页。"""
    base = (cfg.get("public_base_url") or "http://127.0.0.1:8000").rstrip("/")
    page_key = "member"
    hid = hotel_id
    if db is not None and hid is None:
        try:
            t = db.query(WecomBindTicket).filter_by(token=token).first()
            if t:
                hid = t.hotel_id
        except Exception:
            pass
    if db is not None:
        page_key = _resolve_member_landing_page_key(db, hid)
    qs = f"t={urllib.parse.quote(token)}"
    if hid:
        qs += f"&hotel_id={int(hid)}"
    return f"{base}/wecom/landing/{page_key}?{qs}"


def _returning_url(cfg: dict, token: str, *, db: Session | None = None, hotel_id: int | None = None) -> str:
    """老客回访页 URL：对标原 renderWallet 中间页。"""
    base = (cfg.get("public_base_url") or "http://127.0.0.1:8000").rstrip("/")
    page_key = "returning"
    hid = hotel_id
    if db is not None and hid is None:
        try:
            t = db.query(WecomBindTicket).filter_by(token=token).first()
            if t:
                hid = t.hotel_id
        except Exception:
            pass
    if db is not None:
        page_key = _resolve_returning_landing_page_key(db, hid)
    qs = f"t={urllib.parse.quote(token)}"
    if hid:
        qs += f"&hotel_id={int(hid)}"
    return f"{base}/wecom/landing/{page_key}?{qs}"


def _vip_benefits(level: str | None) -> list[dict]:
    """简易权益中心：按会员等级返回可展示权益（用静态配置）。"""
    raw = (level or "normal").strip().lower()
    base = [
        {"title": "专属管家", "desc": "企微一对一服务，入住与关怀咨询"},
        {"title": "扫码礼遇", "desc": "添加管家可领房费折扣券（每身份限一次）"},
    ]
    if raw in ("silver", "白银"):
        base.extend(
            [
                {"title": "欢迎饮品", "desc": "入住当日赠欢迎饮品一份"},
                {"title": "优先选房", "desc": "同房型内优先安排偏好楼层"},
            ]
        )
    elif raw in ("gold", "黄金"):
        base.extend(
            [
                {"title": "欢迎饮品", "desc": "入住当日赠欢迎饮品一份"},
                {"title": "优先选房", "desc": "同房型内优先安排偏好楼层"},
                {"title": "延迟退房", "desc": "视房态可延迟退房至 14:00"},
                {"title": "升房候补", "desc": "入住日免费升房候补（视空房）"},
            ]
        )
    elif raw in ("platinum", "铂金"):
        base.extend(
            [
                {"title": "管家专属", "desc": "入住前一日主动确认偏好与行程"},
                {"title": "延迟退房", "desc": "视房态可延迟退房至 16:00"},
                {"title": "升房保障", "desc": "同档次空房优先升房"},
                {"title": "欢迎礼遇", "desc": "欢迎果盘 + 饮品"},
            ]
        )
    else:
        base.append({"title": "延迟退房协商", "desc": "视房态可协商延迟至 12:00"})
    return base


def get_guest_portal(db: Session, token: str, *, session_raw: str | None = None, require_auth: bool = True) -> dict:
    """客人 H5 会员中心：票据定位客人 + 会话/OAuth 做专属校验。"""
    # lazy cross-import 避开循环
    from wecom.wecom_portal_auth import build_wecom_oauth_url, parse_portal_session, session_matches_ticket
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service.care_service import _vip_label

    ticket = db.query(WecomBindTicket).filter_by(token=(token or "").strip()).first()
    if not ticket:
        raise NotFoundError("链接无效或已失效，请从企微欢迎语重新打开")
    cfg = _wecom_config_service.load_wecom_config(db)
    guest_id = ticket.guest_id
    if not guest_id:
        ident = (
            db.query(GuestIdentity)
            .filter_by(source="wecom", external_id=ticket.external_userid)
            .order_by(GuestIdentity.linked_at.desc())
            .first()
        )
        if ident:
            guest_id = ident.guest_id
    if not guest_id:
        return {
            "ready": False,
            "auth_ok": False,
            "status": ticket.status,
            "nickname": ticket.nickname or "贵宾",
            "message": "请先完成手机号绑定与领券，即可查看会员中心",
            "bind_url": _bind_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        }
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人档案不存在")
    sess = parse_portal_session(session_raw)
    auth_ok = session_matches_ticket(
        sess, external_userid=ticket.external_userid or "", guest_id=guest.id, ticket_token=ticket.token
    )
    if require_auth and (not auth_ok):
        redirect_uri = f"{(cfg.get('public_base_url') or '').rstrip('/')}/wecom/oauth/callback"
        oauth_url = ""
        try:
            oauth_url = build_wecom_oauth_url(cfg, redirect_uri=redirect_uri, state=ticket.token)
        except HTTPException:
            oauth_url = ""
        return {
            "ready": False,
            "auth_ok": False,
            "need_auth": True,
            "status": ticket.status,
            "nickname": ticket.nickname or guest.name,
            "message": "这是客人专属会员中心。请使用领取优惠券时的微信打开；若从别人转发的链接进入，将无法查看。",
            "hint": "在微信中打开后将自动校验企微客户身份；本机刚领过券的可直接进入。",
            "bind_url": _bind_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
            "portal_url": _portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
            "oauth_url": oauth_url,
            "guest_name_hint": guest.name,
        }
    phone = _digits(guest.phone)
    phone_mask = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else guest.phone or "—"
    orders = db.query(Order).filter_by(guest_id=guest.id).order_by(Order.check_in.desc()).limit(12).all()
    order_list = []
    for o in orders:
        rt_name = None
        if o.room_type_id:
            rt = db.get(RoomType, o.room_type_id)
            rt_name = rt.name if rt else None
        order_list.append(
            {
                "order_no": o.order_no,
                "check_in": str(o.check_in) if o.check_in else None,
                "check_out": str(o.check_out) if o.check_out else None,
                "nights": int(o.nights or 1),
                "room_type": rt_name,
                "total_amount": float(o.total_amount or 0),
                "status": o.status,
                "status_cn": ORDER_ST_CN_H5.get(str(o.status or ""), o.status or "—"),
            }
        )
    coupons = list_guest_coupons(db, guest.id)
    wallet = build_member_coupon_wallet(db, guest.id)
    vip = (guest.vip_level or "normal").strip()
    stay_total = db.query(Order).filter_by(guest_id=guest.id).count()
    hotel = db.get(Hotel, ticket.hotel_id) if ticket.hotel_id else None
    return {
        "ready": True,
        "auth_ok": True,
        "exclusive": True,
        "status": ticket.status,
        "nickname": ticket.nickname or guest.name,
        "portal_url": _portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        "entry_tip": "这是您的专属会员中心入口，请收藏本页或保留与管家聊天中的卡片。请勿转发给他人。",
        "guest": {
            "id": guest.id,
            "name": guest.name,
            "phone_mask": phone_mask,
            "vip_level": vip,
            "vip_label": _vip_label(vip),
            "city": guest.city,
            "ltv": float(guest.ltv or 0),
            "stay_count": stay_total,
            "one_id": guest.one_id,
        },
        "coupons": wallet["coupons"] or coupons,
        "wallet": wallet,
        "orders": order_list,
        "benefits": _vip_benefits(vip),
        "hotel_name": (hotel.name if hotel else None) or "本店",
    }
