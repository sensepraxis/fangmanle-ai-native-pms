# SPDX-License-Identifier: Apache-2.0
"""企业微信客户联系：配置、同步外部联系人、一对一消息任务。"""

from __future__ import annotations

import json
import logging
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

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
log = logging.getLogger(__name__)


def list_phone_conflicts(db: Session, hotel_id: int, status: str | None = "pending") -> list[dict]:
    from wecom.wecom_service.care_service import _vip_label

    q = db.query(OneIdPhoneConflict).filter_by(hotel_id=hotel_id)
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(OneIdPhoneConflict.id.desc()).limit(50).all()
    out = []
    for c in rows:
        try:
            cand_ids = json.loads(c.candidate_guest_ids_json or "[]")
        except json.JSONDecodeError:
            cand_ids = []
        candidates = []
        for gid in cand_ids:
            g = db.get(Guest, int(gid))
            if not g:
                continue
            order_n = db.query(Order).filter_by(guest_id=g.id).count()
            candidates.append(
                {
                    "guest_id": g.id,
                    "name": g.name,
                    "phone": g.phone,
                    "phone_norm": _normalize_phone_storage(g.phone),
                    "one_id": g.one_id,
                    "vip_level": g.vip_level,
                    "vip_label": _vip_label(g.vip_level or "normal"),
                    "ltv": float(g.ltv or 0),
                    "order_count": order_n,
                    "city": g.city,
                }
            )
        match_type = (c.match_type or "").strip()
        if not match_type:
            match_type = "phone_exact_multi" if "全号" in (c.note or "") else "phone_last6_multi"
        out.append(
            {
                "id": c.id,
                "status": c.status,
                "match_type": match_type,
                "match_type_label": "全号重复（多人同号）" if match_type == "phone_exact_multi" else "后六位多命中",
                "phone_submitted": c.phone_submitted,
                "phone_last6": c.phone_last4,
                "phone_last4": (c.phone_last4 or "")[-4:] if c.phone_last4 else "",
                "external_userid": c.external_userid,
                "nickname": c.nickname,
                "follow_userid": c.follow_userid,
                "bind_ticket_id": c.bind_ticket_id,
                "candidates": candidates,
                "resolved_guest_id": c.resolved_guest_id,
                "note": c.note,
                "created_at": c.created_at.isoformat(sep=" ", timespec="seconds") if c.created_at else None,
                "resolved_at": c.resolved_at.isoformat(sep=" ", timespec="seconds") if c.resolved_at else None,
            }
        )
    return out


def resolve_phone_conflict(db: Session, conflict_id: int, guest_id: int, *, operator: str = "前台运营") -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import bind_service as _wecom_bind_service
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import contact_service as _wecom_contact_service
    from wecom.wecom_service import portal_service as _wecom_portal_service

    conflict = db.get(OneIdPhoneConflict, conflict_id)
    if not conflict:
        raise NotFoundError("冲突记录不存在")
    if conflict.status != "pending":
        raise InvalidStateError(f"冲突已处理（{conflict.status}）")
    try:
        cand_ids = {int(x) for x in json.loads(conflict.candidate_guest_ids_json or "[]")}
    except json.JSONDecodeError:
        cand_ids = set()
    if guest_id not in cand_ids:
        raise InvalidStateError("所选客人不是本冲突的候选")
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")
    phone_norm = _normalize_phone_storage(conflict.phone_submitted) or (conflict.phone_submitted or "")
    guest.phone = phone_norm or guest.phone
    match_type = (conflict.match_type or "").strip() or (
        "phone_exact_multi" if "全号" in (conflict.note or "") else "phone_last6_multi"
    )
    _wecom_contact_service._bind_wecom_identity(
        db,
        guest,
        conflict.external_userid,
        conflict.follow_userid or "",
        "manual_resolve",
        note=f"OneID 人工裁定 · {match_type} · 手机 …{conflict.phone_last4 or ''} · 冲突#{conflict.id}",
    )
    coupon, coupon_created = _wecom_bind_service.issue_wecom_room_coupon(
        db, hotel_id=conflict.hotel_id, guest=guest, recipient_name=conflict.nickname or guest.name
    )
    coupon_public = _coupon_to_public(coupon, guest=guest)
    try:
        from mkt.mkt_service import (
            get_published_landing,
            grant_from_landing,
            mkt_grant_to_public_coupon,
            resolve_landing_coupon,
        )

        page_key = _wecom_portal_service._resolve_welcome_landing_page_key(db, conflict.hotel_id)
        page = get_published_landing(db, page_key, hotel_id=conflict.hotel_id)
        mkt_coupon = resolve_landing_coupon(db, page, live=True)
        if mkt_coupon:
            before = db.query(MktCouponGrant).filter_by(coupon_id=mkt_coupon.id, guest_id=guest.id).first()
            grant = grant_from_landing(db, conflict.hotel_id, guest.id, mkt_coupon)
            coupon_created = before is None
            pub = mkt_grant_to_public_coupon(db, grant)
            if pub:
                coupon_public = pub
                found = db.query(GuestCoupon).filter_by(code=pub.get("code")).first()
                if found:
                    coupon = found
    except Exception as e:
        log.warning("wecom conflict landing grant fallback: %s", e)
    cfg = _wecom_config_service.load_wecom_config(db)
    ticket = db.get(WecomBindTicket, conflict.bind_ticket_id) if conflict.bind_ticket_id else None
    portal_url = ""
    bind_url = ""
    if ticket:
        ticket.status = "bound"
        ticket.guest_id = guest.id
        ticket.phone_submitted = phone_norm or conflict.phone_submitted
        ticket.bound_at = datetime.now()
        ticket.error_message = None
        portal_url = _wecom_portal_service._portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id)
        bind_url = _wecom_portal_service._bind_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id)
    conflict.status = "resolved"
    conflict.resolved_guest_id = guest.id
    conflict.resolved_by = operator
    conflict.resolved_at = datetime.now()
    if not conflict.match_type:
        conflict.match_type = match_type
    db.commit()
    if coupon:
        db.refresh(coupon)
    return {
        "conflict_id": conflict.id,
        "match_type": match_type,
        "guest_id": guest.id,
        "guest_name": guest.name,
        "coupon": coupon_public,
        "coupon_created": coupon_created,
        "portal_url": portal_url,
        "bind_url": bind_url,
        "message": f"已归并到 {guest.name}（#{guest.id}）并发放优惠券。请通知客人重新打开欢迎语卡片 / 领券链接进入专属会员中心。",
    }


def dismiss_phone_conflict(db: Session, conflict_id: int, *, operator: str = "前台运营", note: str = "") -> dict:
    conflict = db.get(OneIdPhoneConflict, conflict_id)
    if not conflict:
        raise NotFoundError("冲突记录不存在")
    if conflict.status != "pending":
        raise InvalidStateError(f"冲突已处理（{conflict.status}）")
    conflict.status = "dismissed"
    conflict.resolved_by = operator
    conflict.resolved_at = datetime.now()
    if note:
        conflict.note = (conflict.note or "") + f" | 驳回：{note}"
    ticket = db.get(WecomBindTicket, conflict.bind_ticket_id) if conflict.bind_ticket_id else None
    if ticket and ticket.status == "conflict":
        ticket.status = "pending"
        ticket.error_message = "冲突已驳回，可重新提交手机号"
    db.commit()
    return {"conflict_id": conflict.id, "status": "dismissed"}
