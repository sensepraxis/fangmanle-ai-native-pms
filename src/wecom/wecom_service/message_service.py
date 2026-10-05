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


def send_single_message(db: Session, hotel_id: int, guest_id: int, content: str) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common
    from wecom.wecom_service import config_service as _wecom_config_service

    text = (content or "").strip()
    if not text:
        raise ValidationError("消息内容不能为空")
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")
    ident = (
        db.query(GuestIdentity)
        .filter_by(guest_id=guest_id, source="wecom")
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    if not ident or not ident.external_id:
        raise InvalidStateError("该客人尚未绑定企微身份，请先同步外部联系人或扫码加好友")
    cfg = _wecom_config_service.load_wecom_config(db)
    if not cfg.get("enabled", True):
        raise InvalidStateError("企微集成已禁用")
    sender = (ident.matched_by or cfg.get("follow_userid") or "").strip()
    if not sender:
        raise InvalidStateError("未配置跟进人 userid")
    token = _wecom_config_service.get_access_token(cfg)
    payload = {
        "chat_type": "single",
        "external_userid": [ident.external_id],
        "sender": sender,
        "text": {"content": text},
        "allow_select": False,
    }
    url = f"{QYAPI}/externalcontact/add_msg_template?access_token={urllib.parse.quote(token)}"
    data = _wecom_common._http_json("POST", url, payload)
    err = int(data.get("errcode") or 0)
    task = WecomMsgTask(
        hotel_id=hotel_id,
        guest_id=guest_id,
        external_userid=ident.external_id,
        sender_userid=sender,
        content=text,
        msgid=str(data.get("msgid") or "") or None,
        fail_list_json=json.dumps(data.get("fail_list") or [], ensure_ascii=False),
        status="pending_confirm" if err == 0 else "failed",
        error_message=None if err == 0 else str(data.get("errmsg") or data)[:250],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if err != 0:
        raise BusinessError(f"创建企微消息任务失败：{data.get('errmsg') or data}")
    fail_list = data.get("fail_list") or []
    quota_blocked = ident.external_id in fail_list
    return {
        "task_id": task.id,
        "msgid": task.msgid,
        "status": task.status,
        "status_cn": "已提交企微一对一单发",
        "external_userid": ident.external_id,
        "sender_userid": sender,
        "guest_id": guest_id,
        "guest_name": guest.name,
        "content": text,
        "fail_list": fail_list,
        "confirm_steps": [
            "打开手机企业微信",
            "工作台 → 客户联系 → 群发助手",
            "在「待发送的企业消息」找到本条，点「发送」",
        ],
        "hint": f"任务已创建（msgid={task.msgid}）。请到手机企微【工作台 → 客户联系 → 群发助手 → 待发送】点「发送」。注意：此处是「群发助手」待发送列表，不是客户详情页。"
        + (" 企微返回该客户已在 fail_list，可能已达本月/今日群发接收上限。" if quota_blocked else ""),
        "manual_fallback": "若查询结果为「已达群发接收上限」：请复制话术，在企业微信与该客户的 1:1 聊天窗口直接粘贴发送（不走群发限额）。",
    }


def _send_agent_text_message(cfg: dict, token: str, userid: str, content: str) -> dict:
    """向企业内部成员发送应用文本消息（用于关怀话术交接）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common

    agent_raw = str(cfg.get("agent_id") or "").strip()
    if not agent_raw:
        raise InvalidStateError("未配置 agent_id，无法通知管家")
    try:
        agent_id = int(agent_raw)
    except ValueError as e:
        raise InvalidStateError("agent_id 配置无效") from e
    url = f"{QYAPI}/message/send?access_token={urllib.parse.quote(token)}"
    payload = {"touser": userid, "msgtype": "text", "agentid": agent_id, "text": {"content": content[:1800]}, "safe": 0}
    return _wecom_common._http_json("POST", url, payload)


def send_care_direct_message(db: Session, hotel_id: int, guest_id: int, content: str) -> dict:
    """关怀话术：不走群发助手，通知管家在 1:1 会话粘贴发送（无群发次数限制）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service

    text = (content or "").strip()
    if not text:
        raise ValidationError("消息内容不能为空")
    guest = db.get(Guest, guest_id)
    if not guest:
        raise NotFoundError("客人不存在")
    ident = (
        db.query(GuestIdentity)
        .filter_by(guest_id=guest_id, source="wecom")
        .order_by(GuestIdentity.linked_at.desc())
        .first()
    )
    if not ident or not ident.external_id:
        raise InvalidStateError("该客人尚未绑定企微身份，请先同步外部联系人或扫码加好友")
    cfg = _wecom_config_service.load_wecom_config(db)
    if not cfg.get("enabled", True):
        raise InvalidStateError("企微集成已禁用")
    sender = (ident.matched_by or cfg.get("follow_userid") or "").strip()
    if not sender:
        raise InvalidStateError("未配置跟进人 userid")
    token = _wecom_config_service.get_access_token(cfg)
    staff_note = f"【PMS 关怀话术 · 1:1 发送】\n客人：{guest.name}（#{guest.id}）\n外部联系人ID：{ident.external_id}\n\n请打开企业微信 → 客户联系 → 与该客户 1:1 会话，长按粘贴发送。\n（不走群发助手，不受群发次数限制）\n\n—— 话术 ——\n{text}"
    notify_data = _send_agent_text_message(cfg, token, sender, staff_note)
    err = int(notify_data.get("errcode") or 0)
    task = WecomMsgTask(
        hotel_id=hotel_id,
        guest_id=guest_id,
        external_userid=ident.external_id,
        sender_userid=sender,
        content=text,
        msgid=None,
        fail_list_json="[]",
        status="direct_handoff" if err == 0 else "failed",
        error_message=None if err == 0 else str(notify_data.get("errmsg") or notify_data)[:250],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if err != 0:
        raise BusinessError(f"通知管家失败：{notify_data.get('errmsg') or notify_data}")
    return {
        "task_id": task.id,
        "mode": "direct_chat",
        "status": task.status,
        "status_cn": "已通知管家 1:1 发送",
        "external_userid": ident.external_id,
        "sender_userid": sender,
        "guest_id": guest_id,
        "guest_name": guest.name,
        "content": text,
        "hint": f"话术已复制到剪贴板，并已通知 {sender}。请在企业微信打开与该客户的 1:1 聊天窗口，长按粘贴发送。此方式不走群发助手，不受群发次数限制。",
        "steps": [
            "话术已自动复制到剪贴板",
            f"管家 {sender} 会收到企微应用通知",
            "打开与该客户的 1:1 会话 → 长按输入框粘贴 → 发送",
        ],
    }
