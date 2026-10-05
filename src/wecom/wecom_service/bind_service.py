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

from fastapi import HTTPException  # noqa: F401  (except 分支用)
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


def issue_session_for_ticket(db: Session, ticket: WecomBindTicket) -> str:
    from wecom.wecom_portal_auth import issue_portal_session

    if not ticket.guest_id or not ticket.external_userid:
        raise InvalidStateError("票据尚未绑定客人，无法签发专属会话")
    return issue_portal_session(
        external_userid=ticket.external_userid, guest_id=ticket.guest_id, ticket_token=ticket.token
    )


def _welcome_payload(cfg: dict, bind_url: str) -> dict:
    text = (cfg.get("welcome_text") or "").strip() or "欢迎添加本店管家，请点击卡片填写手机号完成绑定。"
    title = (cfg.get("welcome_link_title") or "填写手机号开通专属管家").strip()
    desc = (cfg.get("welcome_link_desc") or "请使用入住登记手机号").strip()
    return {
        "text": {"content": text},
        "attachments": [
            {
                "msgtype": "link",
                "link": {
                    "title": title,
                    "desc": desc,
                    "url": bind_url,
                    "picurl": "https://work.weixin.qq.com/favicon.ico",
                },
            }
        ],
    }


def create_bind_ticket(
    db: Session, *, hotel_id: int, external_userid: str, follow_userid: str, nickname: str = "", state: str = "lobby"
) -> WecomBindTicket:
    existing = (
        db.query(WecomBindTicket)
        .filter_by(external_userid=external_userid, status="pending")
        .order_by(WecomBindTicket.id.desc())
        .first()
    )
    now = datetime.now()
    if existing and existing.expires_at and (existing.expires_at > now):
        if nickname:
            existing.nickname = nickname
        if follow_userid:
            existing.follow_userid = follow_userid
        db.commit()
        db.refresh(existing)
        return existing
    ticket = WecomBindTicket(
        hotel_id=hotel_id,
        token=secrets.token_urlsafe(24),
        external_userid=external_userid,
        follow_userid=follow_userid,
        nickname=(nickname or "")[:80],
        state=state or "lobby",
        status="pending",
        expires_at=now + timedelta(days=7),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def send_welcome_with_bind_link(db: Session, ticket: WecomBindTicket, *, welcome_code: str | None = None) -> dict:
    """真实扫码：用 welcome_code 立即发欢迎语；：用群发模板（需员工确认）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import portal_service as _wecom_portal_service

    cfg = _wecom_config_service.load_wecom_config(db)
    bind_url = _wecom_portal_service._bind_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id)
    body = _welcome_payload(cfg, bind_url)
    token = _wecom_config_service.get_access_token(cfg)
    mode = "link_only"
    errmsg = None
    msgid = None
    if welcome_code:
        payload = {"welcome_code": welcome_code, **body}
        url = f"{QYAPI}/externalcontact/send_welcome_msg?access_token={urllib.parse.quote(token)}"
        data = _wecom_common._http_json("POST", url, payload)
        err = int(data.get("errcode") or 0)
        if err == 0:
            mode = "welcome_code"
        else:
            welcome_err = str(data.get("errmsg") or data)[:250]
            errmsg = f"welcome_code失败({err}): {welcome_err}"[:250]
            log.warning("wecom welcome send_welcome_msg failed: %s", errmsg)
            welcome_code = None
    if mode != "welcome_code":
        sender = ticket.follow_userid or cfg.get("follow_userid") or ""
        text_content = f"{body['text']['content']}\n\n请点击打开绑定页：\n{bind_url}"
        payload = {
            "chat_type": "single",
            "external_userid": [ticket.external_userid],
            "sender": sender,
            "text": {"content": text_content},
            "allow_select": False,
        }
        base = (cfg.get("public_base_url") or "").strip().rstrip("/")
        host = ""
        if "://" in base:
            host = base.split("://", 1)[1].split("/")[0].split(":")[0]
        use_card = (
            base.lower().startswith("https://")
            and ":8000" not in base
            and host
            and (not all(p.isdigit() for p in host.split(".")))
        )
        if use_card:
            payload["attachments"] = body.get("attachments") or []
        url = f"{QYAPI}/externalcontact/add_msg_template?access_token={urllib.parse.quote(token)}"
        data = _wecom_common._http_json("POST", url, payload)
        err = int(data.get("errcode") or 0)
        msgid = str(data.get("msgid") or "") or None
        fail_list = data.get("fail_list") or []
        if err == 0:
            mode = "msg_template"
            if fail_list:
                extra = f"部分客户无效 fail_list={fail_list}"[:250]
                errmsg = f"{errmsg}; {extra}"[:250] if errmsg else extra
            db.add(
                WecomMsgTask(
                    hotel_id=ticket.hotel_id,
                    guest_id=None,
                    external_userid=ticket.external_userid,
                    sender_userid=sender,
                    content=text_content,
                    msgid=msgid,
                    fail_list_json=json.dumps(fail_list, ensure_ascii=False),
                    status="pending_confirm",
                    error_message=errmsg,
                )
            )
        else:
            mode = "link_only"
            if not errmsg:
                errmsg = str(data.get("errmsg") or data)[:250]
    ticket.welcome_sent = mode in ("welcome_code", "msg_template")
    ticket.welcome_mode = mode
    ticket.error_message = errmsg
    db.commit()
    db.refresh(ticket)
    return {
        "ticket_id": ticket.id,
        "token": ticket.token,
        "bind_url": bind_url,
        "welcome_mode": mode,
        "welcome_mode_cn": {
            "welcome_code": "已用欢迎语接口即时发送（客人微信应已收到）",
            "msg_template": "已创建企微群发任务，请管家确认发送。若反复测试易触达群发上限，可复制绑定链接在 1:1 会话粘贴。",
            "link_only": "未能自动推送，请复制绑定链接给客人",
        }.get(mode, mode),
        "msgid": msgid,
        "error_message": errmsg,
        "external_userid": ticket.external_userid,
        "nickname": ticket.nickname,
        "demo_tip": "保底：复制 bind_url，在企业微信与该客户的聊天里直接发送（不走群发，不受月限额影响）。",
    }


def handle_friend_added(
    db: Session,
    *,
    hotel_id: int,
    external_userid: str,
    follow_userid: str,
    state: str = "lobby",
    welcome_code: str | None = None,
    nickname: str = "",
    force_welcome: bool = False,
) -> dict:
    """加好友事件入口：建票据 + 发定制欢迎语（含绑定表单链接）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import contact_service as _wecom_contact_service

    cfg = _wecom_config_service.load_wecom_config(db)
    if not nickname:
        try:
            token = _wecom_config_service.get_access_token(cfg)
            detail = _wecom_contact_service.get_external_contact(token, external_userid)
            nickname = ((detail.get("external_contact") or {}).get("name") or "").strip()
        except Exception:
            nickname = ""
    already = db.query(GuestIdentity).filter_by(source="wecom", external_id=external_userid).first()
    if already and (not force_welcome):
        wallet = build_member_coupon_wallet(db, already.guest_id)
        if wallet["summary"]["total"] > 0:
            ticket = create_bind_ticket(
                db,
                hotel_id=hotel_id,
                external_userid=external_userid,
                follow_userid=follow_userid or cfg.get("follow_userid") or "",
                nickname=nickname,
                state=state or "lobby",
            )
            if not ticket.guest_id:
                ticket.guest_id = already.guest_id
                db.commit()
                db.refresh(ticket)
            sent = send_welcome_with_bind_link(db, ticket, welcome_code=welcome_code)
            return {
                "already_bound": True,
                "guest_id": already.guest_id,
                "external_userid": external_userid,
                "mode": "wallet",
                "wallet_summary": wallet["summary"],
                "hint": "老会员回访：已推送券包入口",
                **sent,
            }
        force_welcome = True
    ticket = create_bind_ticket(
        db,
        hotel_id=hotel_id,
        external_userid=external_userid,
        follow_userid=follow_userid or cfg.get("follow_userid") or "",
        nickname=nickname,
        state=state or "lobby",
    )
    sent = send_welcome_with_bind_link(db, ticket, welcome_code=welcome_code)
    from events import emit

    emit(
        "wecom.friend_added",
        {
            "hotel_id": hotel_id,
            "external_userid": external_userid,
            "ticket_id": ticket.id if ticket else None,
            "already_bound": bool(already),
        },
    )
    return {"already_bound": bool(already), **sent}


def simulate_friend_scan(db: Session, hotel_id: int, external_userid: str | None = None) -> dict:
    """本地：选一个真实外部客户，走「加好友 → 发绑定消息」全流程。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import contact_service as _wecom_contact_service

    cfg = _wecom_config_service.load_wecom_config(db)
    follow = cfg.get("follow_userid") or ""
    token = _wecom_config_service.get_access_token(cfg)
    ids = _wecom_contact_service.list_external_userids(token, follow)
    if not ids:
        raise InvalidStateError("跟进人名下暂无外部联系人，请先用个人微信扫大厅码加好友")
    eid = (external_userid or "").strip() or ids[0]
    if eid not in ids:
        raise InvalidStateError(f"external_userid 不在跟进人客户列表中：{eid}")
    return handle_friend_added(
        db,
        hotel_id=hotel_id,
        external_userid=eid,
        follow_userid=follow,
        state="lobby",
        welcome_code=None,
        force_welcome=True,
    )


def get_bind_ticket_public(db: Session, token: str) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import portal_service as _wecom_portal_service

    cfg = _wecom_config_service.load_wecom_config(db)
    offer = _coupon_offer_public(cfg)
    ticket = db.query(WecomBindTicket).filter_by(token=token).first()
    if not ticket:
        raise NotFoundError("绑定链接无效或已失效")

    def _wallet_payload(guest_id: int, *, status: str, message: str) -> dict:
        guest = db.get(Guest, guest_id)
        wallet = build_member_coupon_wallet(db, guest_id)
        return {
            "status": status,
            "mode": "wallet",
            "nickname": ticket.nickname or (guest.name if guest else "贵宾"),
            "guest_id": guest_id,
            "guest_name": guest.name if guest else None,
            "message": message,
            "offer": offer,
            "coupon": (wallet["unused"] or wallet["coupons"] or [None])[0],
            "wallet": wallet,
            "portal_url": _wecom_portal_service._portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
            "returning_url": _wecom_portal_service._returning_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        }

    if ticket.status == "bound":
        if ticket.guest_id:
            return _wallet_payload(
                ticket.guest_id, status="bound", message="欢迎回来！以下是您在本店私域领取的全部优惠券"
            )
        return {
            "status": "bound",
            "nickname": ticket.nickname,
            "guest_id": ticket.guest_id,
            "message": "您已完成领取，正在进入专属会员中心…",
            "offer": offer,
            "coupon": None,
            "portal_url": _wecom_portal_service._portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
            "returning_url": _wecom_portal_service._returning_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        }
    if ticket.status == "conflict":
        conflict = (
            db.query(OneIdPhoneConflict)
            .filter_by(bind_ticket_id=ticket.id, status="pending")
            .order_by(OneIdPhoneConflict.id.desc())
            .first()
        )
        match_type = (conflict.match_type if conflict else None) or "phone_last6_multi"
        if match_type == "phone_exact_multi":
            msg = "您提交的手机号在系统中对应多位客人档案，已提交前台 OneID 人工确认。确认后请重新打开本页领取优惠券。"
        else:
            msg = "手机号后六位匹配到多位客人，已提交前台 OneID 人工确认。确认后请重新打开本页领取优惠券。"
        return {
            "status": "conflict",
            "nickname": ticket.nickname or "贵宾",
            "message": msg,
            "match_type": match_type,
            "offer": offer,
            "phone_submitted": ticket.phone_submitted,
            "hint": "前台在「OneID 归并」中选定档案后，请刷新本页或再次点开欢迎语卡片。",
        }
    ident = (
        db.query(GuestIdentity)
        .filter_by(source="wecom", external_id=ticket.external_userid)
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    if ident and ident.guest_id:
        wallet = build_member_coupon_wallet(db, ident.guest_id)
        can_claim = False
        claim_hint = ""
        try:
            from mkt.mkt_service import get_published_landing, resolve_landing_coupon
            from models import MktCouponGrant

            page_key = _wecom_portal_service._resolve_welcome_landing_page_key(db, ticket.hotel_id)
            page = get_published_landing(db, page_key, hotel_id=ticket.hotel_id)
            mkt_c = resolve_landing_coupon(db, page, live=True)
            if mkt_c:
                had = db.query(MktCouponGrant).filter_by(coupon_id=mkt_c.id, guest_id=ident.guest_id).first()
                can_claim = had is None and mkt_c.status == "active"
                if can_claim:
                    claim_hint = f"您还可领取本页礼遇：{mkt_c.name}"
        except Exception:
            can_claim = False
        if wallet["summary"]["total"] > 0 or can_claim:
            payload = _wallet_payload(
                ident.guest_id,
                status="member",
                message="欢迎回来！以下是您的私域优惠券" + ("；可继续领取本页新礼遇" if can_claim else ""),
            )
            payload["can_claim"] = can_claim
            payload["claim_hint"] = claim_hint
            return payload
    if ticket.expires_at and ticket.expires_at < datetime.now():
        ticket.status = "expired"
        db.commit()
        raise BusinessError("绑定链接已过期，请重新扫码添加管家")
    return {
        "status": "pending",
        "nickname": ticket.nickname or "贵宾",
        "message": "填写手机号即可领取优惠券并开通专属管家",
        "offer": offer,
    }


def issue_wecom_room_coupon(
    db: Session, *, hotel_id: int, guest: Guest, recipient_name: str | None = None
) -> tuple[GuestCoupon, bool]:
    """发放企微扫码房费折扣券；同一客人同类型只发一次。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service

    cfg = _wecom_config_service.load_wecom_config(db)
    existing = db.query(GuestCoupon).filter_by(guest_id=guest.id, source="wecom_scan", coupon_type="room_rate").first()
    if existing:
        if not existing.recipient_name and (recipient_name or guest.name):
            existing.recipient_name = recipient_name or guest.name
        if not existing.channel:
            existing.channel = "企业微信"
        if not existing.redeem_status:
            existing.redeem_status = "unused" if not existing.used_at else "redeemed"
        return (existing, False)
    rate = float(cfg.get("coupon_discount_rate") or 0.7)
    days = int(cfg.get("coupon_valid_days") or 365)
    name = (cfg.get("coupon_name") or "企微好友专享 · 房费7折券").strip()
    now = datetime.now()
    coupon = GuestCoupon(
        hotel_id=hotel_id,
        guest_id=guest.id,
        code=f"WX70-{guest.id}-{secrets.token_hex(3).upper()}",
        name=name,
        recipient_name=(recipient_name or guest.name or "").strip() or None,
        channel="企业微信",
        coupon_type="room_rate",
        discount_rate=rate,
        source="wecom_scan",
        status="active",
        redeem_status="unused",
        valid_from=now,
        valid_until=now + timedelta(days=days),
        note="企微扫码添加管家后填写手机号领取；可用于本店房费折扣",
    )
    db.add(coupon)
    db.flush()
    return (coupon, True)


def submit_bind_phone(db: Session, token: str, phone: str) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import contact_service as _wecom_contact_service
    from wecom.wecom_service import portal_service as _wecom_portal_service

    ticket = db.query(WecomBindTicket).filter_by(token=token).first()
    if not ticket:
        raise NotFoundError("绑定链接无效")
    if ticket.status == "bound":
        wallet = None
        coupon = None
        if ticket.guest_id:
            wallet = build_member_coupon_wallet(db, ticket.guest_id)
            coupon = (wallet["unused"] or wallet["coupons"] or [None])[0]
        return {
            "ok": True,
            "guest_id": ticket.guest_id,
            "message": "欢迎回来！以下是您的私域优惠券",
            "coupon": coupon,
            "wallet": wallet,
            "mode": "wallet",
            "portal_url": _wecom_portal_service._portal_url(
                _wecom_config_service.load_wecom_config(db), ticket.token, db=db, hotel_id=ticket.hotel_id
            ),
            "returning_url": _wecom_portal_service._returning_url(
                _wecom_config_service.load_wecom_config(db), ticket.token, db=db, hotel_id=ticket.hotel_id
            ),
        }
    if ticket.status == "conflict":
        conf = (
            db.query(OneIdPhoneConflict)
            .filter_by(bind_ticket_id=ticket.id, status="pending")
            .order_by(OneIdPhoneConflict.id.desc())
            .first()
        )
        raise ConflictError(
            "手机号后六位匹配到多位客人，已进入 OneID 人工处理"
            + (f"（冲突#{conf.id}）" if conf else "")
            + "，请联系前台确认后领券"
        )
    if ticket.expires_at and ticket.expires_at < datetime.now():
        raise BusinessError("绑定链接已过期")
    digits = _digits(phone)
    if len(digits) < 7:
        raise ValidationError("请输入有效手机号")
    phone_norm = _normalize_cn_mobile(phone)
    if len(phone_norm) < 8:
        raise ValidationError("请输入有效手机号（可带 +86）")
    last6 = _phone_last6(phone_norm)
    if len(last6) < 6:
        raise ValidationError("手机号位数不足，无法归集")
    created = False
    merge_method = "phone_last6"
    existing_ident = db.query(GuestIdentity).filter_by(source="wecom", external_id=ticket.external_userid).first()
    if existing_ident and existing_ident.guest_id:
        guest = db.get(Guest, existing_ident.guest_id)
        if not guest:
            raise ConflictError(f"企微身份关联的客人 #{existing_ident.guest_id} 不存在")
        merge_method = "wecom_existing"
        old_norm = _normalize_phone_storage(guest.phone)
        if old_norm and old_norm != phone_norm:
            guest.phone = phone_norm
            db.add(
                OneIdMergeEvent(
                    guest_id=guest.id,
                    action="profile_update",
                    source="wecom",
                    external_id=ticket.external_userid,
                    confidence=1.0,
                    merge_method="phone_form_overwrite",
                    operator="手机号绑定页",
                    note=f"扫码领券更新手机号为 …{last6}",
                    occurred_at=datetime.now(),
                )
            )
        else:
            guest.phone = phone_norm
        existing_ident.matched_by = ticket.follow_userid or existing_ident.matched_by
        existing_ident.merge_method = merge_method
        existing_ident.confidence = 1.0
    else:
        guest = None
        exact_matches = find_guests_by_phone_exact(db, phone_norm)

        def _conflict_response(cands: list, *, match_type: str, reason: str, note: str, err: str, msg: str) -> dict:
            conflict = OneIdPhoneConflict(
                hotel_id=ticket.hotel_id,
                status="pending",
                phone_submitted=phone_norm,
                phone_last4=last6,
                match_type=match_type,
                external_userid=ticket.external_userid,
                nickname=ticket.nickname,
                follow_userid=ticket.follow_userid,
                bind_ticket_id=ticket.id,
                candidate_guest_ids_json=json.dumps([g.id for g in cands]),
                note=note,
            )
            db.add(conflict)
            ticket.status = "conflict"
            ticket.phone_submitted = phone_norm
            ticket.error_message = err
            db.commit()
            db.refresh(conflict)
            return {
                "ok": False,
                "status": "conflict",
                "conflict_id": conflict.id,
                "match_type": match_type,
                "match_reason": reason,
                "phone_last6": last6,
                "phone_last4": last6[-4:],
                "candidates": [{"guest_id": g.id, "name": g.name, "phone": g.phone, "one_id": g.one_id} for g in cands],
                "message": msg,
            }

        if len(exact_matches) == 1:
            guest = exact_matches[0]
            merge_method = "phone_exact"
            created = False
            guest.phone = phone_norm
        elif len(exact_matches) > 1:
            return _conflict_response(
                exact_matches,
                match_type="phone_exact_multi",
                reason="phone_exact_multi",
                note="H5 提交手机号全号精确匹配到多位客人（档案重复）",
                err=f"全号匹配 {len(exact_matches)} 位客人，待 OneID 人工",
                msg=f"完整手机号匹配到 {len(exact_matches)} 位客人档案，已提交 OneID 人工归并。前台确认后请重新打开本页领券。",
            )
        else:
            matches = find_guests_by_phone_last6(db, phone_norm)
            if len(matches) > 1:
                return _conflict_response(
                    matches,
                    match_type="phone_last6_multi",
                    reason="phone_last6_multi",
                    note="H5 提交手机号后六位匹配到多位客人（全号未命中）",
                    err=f"后六位 {last6} 匹配 {len(matches)} 位客人，待 OneID 人工",
                    msg=f"手机号后六位（{last6}）匹配到 {len(matches)} 位客人，已提交 OneID 人工归并。前台确认后请重新打开本页领券。",
                )
            if not matches:
                guest = Guest(
                    one_id=f"ONE-BIND-{int(datetime.now().timestamp())}",
                    name=ticket.nickname or "企微客人",
                    phone=phone_norm,
                    vip_level="normal",
                )
                db.add(guest)
                db.flush()
                db.add(
                    OneIdMergeEvent(
                        guest_id=guest.id,
                        action="oneid_born",
                        source="wecom",
                        external_id=ticket.external_userid,
                        confidence=1.0,
                        merge_method="primary_bind",
                        operator="手机号绑定页",
                        note="扫码绑定未命中已有客人（全号/后六位），新建档案并领券",
                        occurred_at=datetime.now(),
                    )
                )
                merge_method = "primary_bind"
                created = True
            else:
                guest = matches[0]
                merge_method = "phone_last6"
                created = False
                guest.phone = phone_norm
        bind_note = (
            f"扫码绑定表单 · 全号精确归集 · {phone_norm}"
            if merge_method == "phone_exact"
            else f"扫码绑定表单 · 手机后六位归集 · {last6}"
        )
        _wecom_contact_service._bind_wecom_identity(
            db, guest, ticket.external_userid, ticket.follow_userid or "", merge_method, note=bind_note
        )
    coupon_public: dict | None = None
    coupon_created = False
    try:
        from mkt.mkt_service import (
            get_published_landing,
            grant_from_landing,
            mkt_grant_to_public_coupon,
            resolve_landing_coupon,
        )

        page_key = _wecom_portal_service._resolve_welcome_landing_page_key(db, ticket.hotel_id)
        page = get_published_landing(db, page_key, hotel_id=ticket.hotel_id)
        mkt_coupon = resolve_landing_coupon(db, page, live=True)
        if mkt_coupon:
            before = db.query(MktCouponGrant).filter_by(coupon_id=mkt_coupon.id, guest_id=guest.id).first()
            grant = grant_from_landing(db, ticket.hotel_id, guest.id, mkt_coupon)
            coupon_created = before is None
            coupon_public = mkt_grant_to_public_coupon(db, grant)
    except HTTPException:
        raise
    except Exception as e:
        log.warning("wecom bind landing grant fallback: %s", e)
        coupon_public = None
    if coupon_public is None:
        coupon, coupon_created = issue_wecom_room_coupon(
            db, hotel_id=ticket.hotel_id, guest=guest, recipient_name=ticket.nickname or guest.name
        )
        coupon_public = _coupon_to_public(coupon, guest=guest)
    ticket.status = "bound"
    ticket.guest_id = guest.id
    ticket.phone_submitted = phone_norm
    ticket.bound_at = datetime.now()
    ticket.error_message = None
    try:
        from mkt.mkt_auto_rules import fire_event_rules as fire_auto_rules

        fire_auto_rules(db, ticket.hotel_id, "NEW_WECHAT_MEMBER", guest.id)
    except Exception as e:
        log.warning("wecom bind NEW_WECHAT_MEMBER auto-rules: %s", e)
    try:
        from mkt.mkt_auto_grant import fire_event_rules

        fire_event_rules(db, ticket.hotel_id, "NEW_WECHAT_MEMBER", guest.id)
    except Exception as e:
        log.warning("wecom bind NEW_WECHAT_MEMBER rules: %s", e)
    db.commit()
    until = (coupon_public.get("valid_until") or coupon_public.get("valid_to") or "")[:10]
    label = coupon_public.get("discount_label") or coupon_public.get("name") or "优惠券"
    cfg = _wecom_config_service.load_wecom_config(db)
    portal_session = ""
    try:
        portal_session = issue_session_for_ticket(db, ticket)
    except Exception:
        portal_session = ""
    wallet = build_member_coupon_wallet(db, guest.id)
    return {
        "ok": True,
        "created_guest": created,
        "guest_id": guest.id,
        "guest_name": guest.name,
        "merge_method": merge_method,
        "coupon": coupon_public,
        "coupon_created": coupon_created,
        "wallet": wallet,
        "mode": "wallet",
        "portal_url": _wecom_portal_service._portal_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        "returning_url": _wecom_portal_service._returning_url(cfg, ticket.token, db=db, hotel_id=ticket.hotel_id),
        "portal_session": portal_session,
        "message": f"领取成功！已为 {guest.name} 开通专属管家，并发放 {label}（券码 {coupon_public.get('code')}，有效期至 {until or '—'}）。欢迎查看您的私域礼遇。",
    }


def list_bind_tickets(db: Session, hotel_id: int, limit: int = 30) -> list[dict]:
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service
    from wecom.wecom_service import portal_service as _wecom_portal_service

    rows = db.query(WecomBindTicket).filter_by(hotel_id=hotel_id).order_by(WecomBindTicket.id.desc()).limit(limit).all()
    out = []
    for t in rows:
        out.append(
            {
                "id": t.id,
                "token": t.token,
                "external_userid": t.external_userid,
                "nickname": t.nickname,
                "status": t.status,
                "guest_id": t.guest_id,
                "phone_submitted": t.phone_submitted,
                "welcome_mode": t.welcome_mode,
                "welcome_sent": t.welcome_sent,
                "bind_url": _wecom_portal_service._bind_url(
                    _wecom_config_service.load_wecom_config(db), t.token, db=db, hotel_id=t.hotel_id
                ),
                "created_at": t.created_at.isoformat(sep=" ", timespec="seconds") if t.created_at else None,
                "bound_at": t.bound_at.isoformat(sep=" ", timespec="seconds") if t.bound_at else None,
            }
        )
    return out


def _expire_bind_tickets_for_external(db: Session, external_userid: str) -> int:
    """客人删除好友后，作废未完成的绑定票据，便于再次添加时重新发欢迎语。"""
    if not external_userid:
        return 0
    rows = db.query(WecomBindTicket).filter_by(external_userid=external_userid, status="pending").all()
    for t in rows:
        t.status = "expired"
        t.error_message = "客人已删除好友，票据作废"
    if rows:
        db.commit()
    return len(rows)
