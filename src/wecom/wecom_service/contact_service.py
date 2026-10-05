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


def list_external_userids(token: str, userid: str) -> list[str]:
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common

    qs = urllib.parse.urlencode({"access_token": token, "userid": userid})
    data = _wecom_common._http_json("GET", f"{QYAPI}/externalcontact/list?{qs}")
    if int(data.get("errcode") or 0) != 0:
        raise BusinessError(f"list 外部联系人失败：{data.get('errmsg') or data}")
    return list(data.get("external_userid") or [])


def get_external_contact(token: str, external_userid: str) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common

    qs = urllib.parse.urlencode({"access_token": token, "external_userid": external_userid})
    data = _wecom_common._http_json("GET", f"{QYAPI}/externalcontact/get?{qs}")
    if int(data.get("errcode") or 0) != 0:
        raise BusinessError(f"获取客户详情失败：{data.get('errmsg') or data}")
    return data


def _find_guest_by_phone(db: Session, phones: list[str]) -> Guest | None:
    """同步通讯录用：优先全号精确，其次后六位唯一命中。"""
    cleaned = [_normalize_phone_storage(p) for p in phones if _digits(p)]
    if not cleaned:
        return None
    for p in cleaned:
        exact = find_guests_by_phone_exact(db, p)
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            return None
    for p in cleaned:
        hits = find_guests_by_phone_last6(db, p)
        if len(hits) == 1:
            return hits[0]
    return None


def _bind_wecom_identity(
    db: Session, guest: Guest, external_userid: str, follow_userid: str, merge_method: str, note: str
) -> tuple[GuestIdentity, bool]:
    existing = db.query(GuestIdentity).filter_by(guest_id=guest.id, source="wecom", external_id=external_userid).first()
    if existing:
        existing.matched_by = follow_userid
        existing.merge_method = merge_method
        existing.confidence = (
            1.0
            if merge_method in ("phone_exact", "phone_last4", "phone_last6", "wecom_existing", "manual_resolve")
            else existing.confidence or 0.9
        )
        return (existing, False)
    conflict = db.query(GuestIdentity).filter_by(source="wecom", external_id=external_userid).first()
    if conflict and conflict.guest_id != guest.id:
        raise ConflictError(f"external_userid 已绑定客人 #{conflict.guest_id}，请到 OneID 人工归并")
    ident = GuestIdentity(
        guest_id=guest.id,
        source="wecom",
        external_id=external_userid,
        confidence=1.0
        if merge_method in ("phone_exact", "phone_last4", "phone_last6", "wecom_existing", "manual_resolve")
        else 0.92,
        linked_at=datetime.now(),
        is_primary=False,
        merge_method=merge_method,
        matched_by=follow_userid,
    )
    db.add(ident)
    db.add(
        OneIdMergeEvent(
            guest_id=guest.id,
            action="channel_merge",
            source="wecom",
            external_id=external_userid,
            confidence=ident.confidence,
            merge_method=merge_method,
            operator="企微同步",
            note=note,
            occurred_at=datetime.now(),
        )
    )
    return (ident, True)


def sync_external_contacts(db: Session, hotel_id: int) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import config_service as _wecom_config_service

    cfg = _wecom_config_service.load_wecom_config(db)
    if not cfg.get("enabled", True):
        raise InvalidStateError("企微集成已禁用")
    follow = cfg.get("follow_userid") or ""
    token = _wecom_config_service.get_access_token(cfg)
    external_ids = list_external_userids(token, follow)
    created_guests = 0
    bound = 0
    updated = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    for eid in external_ids:
        detail = get_external_contact(token, eid)
        contact = detail.get("external_contact") or {}
        name = (contact.get("name") or "企微客人").strip() or "企微客人"
        follow_info = (detail.get("follow_user") or [{}])[0] if detail.get("follow_user") else {}
        remark = (follow_info.get("remark") or "").strip()
        mobiles = list(follow_info.get("remark_mobiles") or [])
        if contact.get("gender") is not None:
            pass
        guest = _find_guest_by_phone(db, mobiles)
        merge_method = "phone_exact" if guest else "wecom_sync"
        if not guest:
            cand = db.query(Guest).filter(Guest.name == name).order_by(Guest.id.asc()).first()
            if cand:
                has_wecom = db.query(GuestIdentity).filter_by(guest_id=cand.id, source="wecom").first()
                if not has_wecom:
                    guest = cand
                    merge_method = "name_match"
        if not guest:
            guest = Guest(
                one_id=f"ONE-WC-{int(datetime.now().timestamp())}-{created_guests}",
                name=remark or name,
                phone=mobiles[0] if mobiles else None,
                vip_level="normal",
            )
            db.add(guest)
            db.flush()
            db.add(
                OneIdMergeEvent(
                    guest_id=guest.id,
                    action="oneid_born",
                    source="wecom",
                    external_id=eid,
                    confidence=1.0,
                    merge_method="primary_bind",
                    operator="企微同步",
                    note=f"扫码/加好友建档 · 跟进人 {follow}",
                    occurred_at=datetime.now(),
                )
            )
            created_guests += 1
            merge_method = "primary_bind"
        try:
            _ident, is_new = _bind_wecom_identity(
                db,
                guest,
                eid,
                follow,
                merge_method if merge_method != "primary_bind" else "primary_bind",
                note=f"同步跟进人 {follow} · 昵称 {name}",
            )
            if is_new:
                bound += 1
            else:
                updated += 1
        except HTTPException:
            skipped += 1
            items.append({"external_userid": eid, "name": name, "status": "conflict"})
            continue
        items.append(
            {
                "external_userid": eid,
                "name": name,
                "guest_id": guest.id,
                "guest_name": guest.name,
                "merge_method": merge_method,
                "status": "bound",
            }
        )
    db.commit()
    return {
        "follow_userid": follow,
        "fetched": len(external_ids),
        "created_guests": created_guests,
        "bound": bound,
        "updated": updated,
        "skipped": skipped,
        "items": items,
    }
