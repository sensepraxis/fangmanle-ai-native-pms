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
from infra.i18n import t as i18n_t
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

_SEND_STATUS_CN = {
    0: "未发送",
    1: "已发送",
    2: "因不是好友发送失败",
    3: "因客户已收到其他群发消息导致失败",
}


def list_msg_tasks(db: Session, hotel_id: int, guest_id: int | None = None, limit: int = 20) -> list[dict]:
    q = db.query(WecomMsgTask).filter_by(hotel_id=hotel_id)
    if guest_id:
        q = q.filter_by(guest_id=guest_id)
    rows = q.order_by(WecomMsgTask.id.desc()).limit(limit).all()
    out = []
    for t in rows:
        d = {
            "id": t.id,
            "guest_id": t.guest_id,
            "external_userid": t.external_userid,
            "sender_userid": t.sender_userid,
            "content": t.content,
            "msgid": t.msgid,
            "status": t.status,
            "status_cn": i18n_t(
                {
                    "pending_confirm": "待企微确认",
                    "submitted": "已提交",
                    "direct_handoff": "1:1 会话待发送",
                    "sidebar_sent": "侧边栏直发",
                    "failed": "失败",
                }.get(t.status or "", t.status or "—")
            ),
            "error_message": t.error_message,
            "created_at": t.created_at.isoformat(sep=" ", timespec="seconds") if t.created_at else None,
        }
        out.append(d)
    return out


def query_groupmsg_result(db: Session, msgid: str | None = None) -> dict:
    """查询企业群发实际送达结果（员工点「发送」之后）。"""
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common
    from wecom.wecom_service import config_service as _wecom_config_service

    cfg = _wecom_config_service.load_wecom_config(db)
    task = None
    mid = (msgid or "").strip()
    if mid:
        task = db.query(WecomMsgTask).filter_by(msgid=mid).order_by(WecomMsgTask.id.desc()).first()
    else:
        task = db.query(WecomMsgTask).filter(WecomMsgTask.msgid.isnot(None)).order_by(WecomMsgTask.id.desc()).first()
        mid = (task.msgid if task else "") or ""
    if not mid:
        raise NotFoundError("没有可查询的群发 msgid，请先模拟扫码创建任务")
    sender = (task.sender_userid if task else "") or cfg.get("follow_userid") or ""
    token = _wecom_config_service.get_access_token(cfg)
    url = f"{QYAPI}/externalcontact/get_groupmsg_send_result?access_token={urllib.parse.quote(token)}"
    data = _wecom_common._http_json("POST", url, {"msgid": mid, "userid": sender, "limit": 100})
    err = int(data.get("errcode") or 0)
    if err != 0:
        raise BusinessError(f"查询群发结果失败：{data.get('errmsg') or data}")
    send_list = data.get("send_list") or []
    rows = []
    for item in send_list:
        st = int(item.get("status") if item.get("status") is not None else -1)
        msgid = _SEND_STATUS_CN.get(st)
        status_cn = i18n_t(msgid) if msgid else i18n_t("未知状态 {st}", st=st)
        rows.append(
            {
                "external_userid": item.get("external_userid"),
                "userid": item.get("userid"),
                "status": st,
                "status_cn": status_cn,
                "send_time": item.get("send_time"),
            }
        )
    hint = i18n_t("未查到该成员的发送明细")
    if rows:
        st0 = rows[0]["status"]
        if st0 == 1:
            hint = i18n_t(
                "企微侧显示已发送。若客人仍看不到，请到个人微信会话刷新；点开链接请用系统浏览器（IP/带端口易被微信拦截）。"
            )
        elif st0 == 3:
            hint = i18n_t(
                "企微侧拒绝送达：该客户已达群发接收上限（反复扫码/发关怀会触发）。请复制话术，在企业微信与该客户的 1:1 会话里直接粘贴发送（不受群发限额）。或等下个月/调整企微「群发助手 → 设置」规则后再试。"
            )
        elif st0 == 2:
            hint = i18n_t("客户与跟进人不是好友，请先用个人微信扫「联系我」加好友。")
        elif st0 == 0:
            hint = i18n_t(
                "仍显示未发送：请到手机企微【工作台 → 客户联系 → 群发助手 → 待发送】找到最新一条，由跟进账号点「发送」（不是只在客户详情里浏览）。"
            )
    if task and rows:
        st0 = rows[0]["status"]
        task.status = {0: "pending_confirm", 1: "sent", 2: "failed", 3: "failed"}.get(st0, task.status)
        task.error_message = rows[0]["status_cn"][:250]
        db.commit()
    return {
        "msgid": mid,
        "sender_userid": sender,
        "send_list": rows,
        "hint": hint,
        "manual_fallback": i18n_t(
            "群发失败时：打开 PMS 返回的绑定链接 → 复制 → 在企业微信与该客户的聊天窗口直接粘贴发出。"
        ),
    }
