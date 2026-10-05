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

from fastapi import HTTPException
from sqlalchemy.orm import Session

from bootstrap.ensure_wecom import DEFAULT_WECOM_CONFIG, WECOM_SETTING_KEY
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


def _mark_callback_archived(db: Session, row: WecomCallbackEvent) -> None:
    """处理完成后逻辑删除：记录保留在库中供审计，默认列表不再展示。"""
    row.is_deleted = True
    row.deleted_at = datetime.now()


def enqueue_wecom_callback(db: Session, *, hotel_id: int, event: dict) -> WecomCallbackEvent | None:
    """回调先落库；含 welcome_code 的加好友事件必须同步消费（码约 20 秒有效）。"""
    change = (event.get("ChangeType") or "").strip()
    row = WecomCallbackEvent(
        hotel_id=hotel_id,
        change_type=change or None,
        external_userid=(event.get("ExternalUserID") or "").strip() or None,
        follow_userid=(event.get("UserID") or "").strip() or None,
        state=(event.get("State") or "").strip() or None,
        welcome_code=(event.get("WelcomeCode") or "").strip() or None,
        raw_json=json.dumps(event, ensure_ascii=False),
        status="pending",
        is_deleted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if change == "del_follow_user":
        _expire_bind_tickets_for_external(db, row.external_userid or "")
        row.status = "done"
        row.processed_at = datetime.now()
        row.error_message = "handled:del_follow_user"
        _mark_callback_archived(db, row)
        db.commit()
    elif change in ("add_external_contact", "add_half_external_contact"):
        if row.welcome_code:
            try:
                process_wecom_callback_event(db, row.id)
            except Exception as e:
                log.warning("wecom callback sync process #%s failed: %s", row.id, e)
        else:
            _spawn_callback_processor(row.id)
    else:
        row.status = "done"
        row.processed_at = datetime.now()
        row.error_message = f"ignored:{change or 'empty'}"
        _mark_callback_archived(db, row)
        db.commit()
    return row


def _spawn_callback_processor(event_id: int):
    import threading

    def _run():
        from database import session_scope

        try:
            with session_scope(commit=False) as db:
                process_wecom_callback_event(db, event_id)
        except Exception as e:
            log.warning("wecom callback async process #%s failed: %s", event_id, e)

    threading.Thread(target=_run, name=f"wecom-cb-{event_id}", daemon=True).start()


def process_wecom_callback_event(db: Session, event_id: int) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import bind_service as _wecom_bind_service

    row = db.get(WecomCallbackEvent, event_id)
    if not row:
        return {"ok": False, "error": "not_found"}
    if row.is_deleted or row.status == "done":
        return {"ok": True, "skipped": True}
    row.status = "processing"
    db.commit()
    try:
        result = _wecom_bind_service.handle_friend_added(
            db,
            hotel_id=row.hotel_id,
            external_userid=row.external_userid or "",
            follow_userid=row.follow_userid or "",
            state=row.state or "lobby",
            welcome_code=row.welcome_code,
        )
        row.status = "done"
        row.processed_at = datetime.now()
        row.error_message = None
        _mark_callback_archived(db, row)
        db.commit()
        return {"ok": True, "result": result}
    except Exception as e:
        row.status = "failed"
        row.processed_at = datetime.now()
        row.error_message = str(e)[:240]
        _mark_callback_archived(db, row)
        db.commit()
        raise


def list_callback_inbox(db: Session, hotel_id: int, *, limit: int = 30, include_deleted: bool = False) -> list[dict]:
    q = db.query(WecomCallbackEvent).filter_by(hotel_id=hotel_id)
    if not include_deleted:
        q = q.filter(WecomCallbackEvent.is_deleted.is_(False))
    rows = q.order_by(WecomCallbackEvent.id.desc()).limit(limit).all()
    out = []
    for r in rows:
        d = {
            "id": r.id,
            "change_type": r.change_type,
            "external_userid": r.external_userid,
            "follow_userid": r.follow_userid,
            "state": r.state,
            "status": r.status,
            "is_deleted": bool(r.is_deleted),
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else None,
            "processed_at": r.processed_at.isoformat(sep=" ", timespec="seconds") if r.processed_at else None,
            "deleted_at": r.deleted_at.isoformat(sep=" ", timespec="seconds") if r.deleted_at else None,
        }
        out.append(d)
    return out


def drain_pending_wecom_callbacks(limit: int = 20) -> int:
    """启动时/定时扫一遍积压的 pending 回调。"""
    from database import session_scope

    n = 0
    with session_scope(commit=False) as db:
        rows = (
            db.query(WecomCallbackEvent)
            .filter(WecomCallbackEvent.status == "pending", WecomCallbackEvent.is_deleted.is_(False))
            .order_by(WecomCallbackEvent.id.asc())
            .limit(limit)
            .all()
        )
        ids = [r.id for r in rows]
    for eid in ids:
        _spawn_callback_processor(eid)
        n += 1
    return n
