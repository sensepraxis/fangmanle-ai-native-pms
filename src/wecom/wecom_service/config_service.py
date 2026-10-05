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


# 模块加载时注册，便于 CONFIG_REGISTRY.all_keys() 发现
def _register_wecom_spec() -> None:
    from infra.config_registry import CONFIG_REGISTRY, AppSettingSpec

    if CONFIG_REGISTRY.get(WECOM_SETTING_KEY) is None:
        CONFIG_REGISTRY.register(
            AppSettingSpec(
                key=WECOM_SETTING_KEY,
                default_factory=lambda: deepcopy(DEFAULT_WECOM_CONFIG),
                description="企业微信客户联系 / 回调 / 欢迎语",
                protect_keys=(
                    "corp_id",
                    "agent_id",
                    "public_base_url",
                    "app_secret",
                    "callback_token",
                    "callback_aes_key",
                ),
            )
        )


_register_wecom_spec()


def load_wecom_config(db: Session) -> dict:
    """经 CONFIG_REGISTRY / load_app_setting_json 读企微配置（与默认合并）。"""
    from infra.config_registry import load_app_setting_json

    _register_wecom_spec()
    return load_app_setting_json(
        db,
        WECOM_SETTING_KEY,
        default_factory=lambda: deepcopy(DEFAULT_WECOM_CONFIG),
        protect_keys=("corp_id", "agent_id", "public_base_url", "app_secret", "callback_token", "callback_aes_key"),
    )


def save_wecom_config(db: Session, payload: dict) -> dict:
    """保存企微接入层配置（落库 AppSetting.key=wecom）。密钥留空则不覆盖。"""
    current = load_wecom_config(db)
    for k in (
        "enabled",
        "owner_type",
        "status",
        "corp_id",
        "agent_id",
        "follow_userid",
        "public_base_url",
        "welcome_text",
        "welcome_link_title",
        "welcome_link_desc",
        "coupon_name",
        "coupon_discount_rate",
        "coupon_valid_days",
    ):
        if k in payload:
            current[k] = payload[k]
    if "app_secret" in payload:
        secret = str(payload.get("app_secret") or "").strip()
        if secret and "****" not in secret:
            current["app_secret"] = secret
    if "callback_aes_key" in payload:
        aes = str(payload.get("callback_aes_key") or "").strip()
        if aes and "****" not in aes:
            current["callback_aes_key"] = aes
    if "callback_token" in payload:
        tok = str(payload.get("callback_token") or "").strip()
        if tok and "****" not in tok:
            current["callback_token"] = tok
    if payload.get("callback_url") and (not payload.get("public_base_url")):
        cu = str(payload.get("callback_url") or "").strip().rstrip("/")
        suffix = "/api/wecom/callback"
        if cu.endswith(suffix):
            current["public_base_url"] = cu[: -len(suffix)].rstrip("/")
    current["corp_id"] = str(current.get("corp_id") or "").strip()
    current["agent_id"] = str(current.get("agent_id") or "").strip()
    current["follow_userid"] = str(current.get("follow_userid") or "").strip()
    current["public_base_url"] = str(current.get("public_base_url") or "").strip().rstrip("/")
    current.pop("trusted_domain", None)
    owner = str(current.get("owner_type") or "saas_self").strip()
    current["owner_type"] = owner if owner in ("saas_self", "hotel_tenant") else "saas_self"
    current["enabled"] = bool(current.get("enabled", True))
    current["callback_token"] = str(current.get("callback_token") or "").strip()
    try:
        current["coupon_discount_rate"] = float(current.get("coupon_discount_rate") or 0.7)
    except (TypeError, ValueError):
        current["coupon_discount_rate"] = 0.7
    try:
        current["coupon_valid_days"] = int(current.get("coupon_valid_days") or 365)
    except (TypeError, ValueError):
        current["coupon_valid_days"] = 365
    current["coupon_name"] = str(current.get("coupon_name") or "企微好友专享 · 房费7折券").strip()
    if not current["corp_id"]:
        raise ValidationError("企业 ID（corp_id）不能为空")
    required_ready = all(
        [
            bool(current.get("corp_id")),
            bool(current.get("app_secret")),
            bool(current.get("agent_id")),
            bool(current.get("public_base_url")),
            bool(current.get("callback_token")),
            bool(str(current.get("callback_aes_key") or "").strip()),
        ]
    )
    if current.get("enabled") and (not required_ready):
        raise ValidationError("启用前请先配齐企业 ID、Secret、AgentId、回调 URL、Token 与 EncodingAESKey")
    if not required_ready:
        current["enabled"] = False
        current["status"] = "unconfigured"
    else:
        st = str(current.get("status") or "unconfigured")
        if current.get("enabled") and st == "enabled":
            current["status"] = "enabled"
        elif not current.get("enabled") and st == "enabled":
            current["status"] = "verified"
        elif st not in ("verified", "enabled"):
            current["status"] = "verified"
    row = db.query(AppSetting).filter_by(key=WECOM_SETTING_KEY).first()
    if not row:
        row = AppSetting(key=WECOM_SETTING_KEY)
        db.add(row)
    row.value_json = json.dumps(current, ensure_ascii=False)
    db.commit()
    return current


def mask_wecom_config(cfg: dict) -> dict:
    """系统配置页回显：非敏感明文；密钥脱敏，并带 *_set 标志。"""
    out = dict(cfg)
    base = str(cfg.get("public_base_url") or "").rstrip("/")
    out["callback_url"] = f"{base}/api/wecom/callback" if base else ""
    out["owner_type"] = cfg.get("owner_type") or "saas_self"
    out["status"] = cfg.get("status") or ("enabled" if cfg.get("enabled") else "unconfigured")
    out.pop("trusted_domain", None)

    def _mask(v: str) -> str:
        s = (v or "").strip()
        if not s:
            return ""
        if len(s) <= 8:
            return "****"
        return s[:4] + "****" + s[-4:]

    for k in ("app_secret", "callback_token", "callback_aes_key"):
        raw = str(cfg.get(k) or "")
        out[f"{k}_set"] = bool(raw.strip())
        out[k] = _mask(raw) if raw.strip() else ""
    return out


def get_access_token(cfg: dict) -> str:
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common

    corp_id = cfg.get("corp_id") or ""
    secret = cfg.get("app_secret") or ""
    if not corp_id or not secret:
        raise InvalidStateError("请先配置 corp_id 与 app_secret")
    qs = urllib.parse.urlencode({"corpid": corp_id, "corpsecret": secret})
    data = _wecom_common._http_json("GET", f"{QYAPI}/gettoken?{qs}")
    if int(data.get("errcode") or 0) != 0:
        raise BusinessError(f"gettoken 失败：{data.get('errmsg') or data}")
    token = data.get("access_token")
    if not token:
        raise BusinessError("gettoken 未返回 access_token")
    return str(token)


def test_wecom_connection(db: Session) -> dict:
    # lazy cross-import 避开循环
    from wecom.wecom_service import _common as _wecom_common

    cfg = load_wecom_config(db)
    token = get_access_token(cfg)
    userid = cfg.get("follow_userid") or ""
    external_count = 0
    sample: list = []
    if userid:
        qs = urllib.parse.urlencode({"access_token": token, "userid": userid})
        data = _wecom_common._http_json("GET", f"{QYAPI}/externalcontact/list?{qs}")
        err = int(data.get("errcode") or 0)
        if err != 0:
            raise BusinessError(f"外部联系人权限校验失败（userid={userid}）：{data.get('errmsg') or data}")
        ids = data.get("external_userid") or []
        external_count = len(ids)
        sample = ids[:3]
    cfg["enabled"] = True
    cfg["status"] = "enabled"
    row = db.query(AppSetting).filter_by(key=WECOM_SETTING_KEY).first()
    if row:
        row.value_json = json.dumps(cfg, ensure_ascii=False)
        db.commit()
    return {
        "ok": True,
        "corp_id": cfg.get("corp_id"),
        "agent_id": cfg.get("agent_id"),
        "follow_userid": userid,
        "external_contact_count": external_count,
        "sample_external_userid": sample,
        "status": "enabled",
        "token_preview": token[:8] + "…",
    }
