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


def sidebar_guest_by_external_userid(db: Session, external_userid: str) -> dict:
    """聊天工具栏：按 external_userid 查 PMS 客人（免登录）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common
    from wecom.wecom_service import portal_service as _wecom_portal_service

    eid = (external_userid or "").strip()
    if not eid:
        raise ValidationError("缺少 external_userid")
    ident = (
        db.query(GuestIdentity)
        .filter_by(source="wecom", external_id=eid)
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    if not ident:
        raise NotFoundError("未找到与该企微客户绑定的 PMS 客人，请先完成扫码加好友与手机号归集")
    guest = db.get(Guest, ident.guest_id)
    if not guest:
        raise NotFoundError("客人档案不存在")
    hotel_id = db.query(Order.hotel_id).filter_by(guest_id=guest.id).order_by(Order.check_in.desc()).limit(
        1
    ).scalar() or (db.query(Hotel.id).order_by(Hotel.id).limit(1).scalar() or 1)
    wecom = _wecom_portal_service.guest_wecom_summary(db, guest.id)
    coupons = list_guest_coupons(db, guest.id)
    phone = str(guest.phone or "").replace(" ", "")
    tail = phone[-6:] if len(phone) >= 6 else phone[-4:] if len(phone) >= 4 else ""
    return {
        "hotel_id": hotel_id,
        "guest_id": guest.id,
        "guest_name": guest.name,
        "phone_tail": tail,
        "salutation": _wecom_common._care_salutation(guest),
        "wecom": wecom,
        "coupons": coupons[:3],
        "external_userid": eid,
    }


def log_sidebar_care_sent(db: Session, external_userid: str, content: str, sender_userid: str | None = None) -> dict:
    """聊天工具栏 sendChatMessage 成功后落库。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service

    text = (content or "").strip()
    if not text:
        raise ValidationError("消息内容不能为空")
    summary = sidebar_guest_by_external_userid(db, external_userid)
    guest_id = summary["guest_id"]
    hotel_id = summary["hotel_id"]
    cfg = _wecom_config_service.load_wecom_config(db)
    sender = (sender_userid or summary.get("wecom", {}).get("follow_userid") or cfg.get("follow_userid") or "").strip()
    if not sender:
        raise InvalidStateError("未配置跟进人 userid")
    task = WecomMsgTask(
        hotel_id=hotel_id,
        guest_id=guest_id,
        external_userid=summary["external_userid"],
        sender_userid=sender,
        content=text,
        msgid=None,
        fail_list_json="[]",
        status="sidebar_sent",
        error_message=None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {
        "task_id": task.id,
        "mode": "sidebar_chat",
        "status": task.status,
        "status_cn": "已通过聊天工具栏直发",
        "guest_id": guest_id,
        "guest_name": summary["guest_name"],
        "external_userid": summary["external_userid"],
        "hint": "消息已通过企微聊天工具栏 sendChatMessage 发送到当前 1:1 会话",
    }
