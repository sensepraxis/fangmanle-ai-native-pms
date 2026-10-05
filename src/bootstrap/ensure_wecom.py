# SPDX-License-Identifier: Apache-2.0
"""企业微信（私域）配置与消息 / 绑定 / 回调收件箱 / 优惠券表。"""

from __future__ import annotations

import json
import secrets

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models import (
    AppSetting,
    Base,
    GuestCoupon,
    OneIdPhoneConflict,
    WecomBindTicket,
    WecomCallbackEvent,
    WecomMsgTask,
)

WECOM_SETTING_KEY = "wecom"

DEFAULT_WECOM_CONFIG = {
    # 空系统 = 未接入：凭据一律为空，由用户在「企业微信」配置页真实填写。
    # 之前这里写死 enabled=True + 演示 corp_id/app_secret，导致私域健康度凭空得 50 分（总分 12）。
    "enabled": False,
    "owner_type": "hotel_tenant",  # 按酒店租户接入
    "status": "unconfigured",  # unconfigured | verified | enabled
    "corp_id": "",
    "agent_id": "",
    "app_secret": "",
    "follow_userid": "",
    "public_base_url": "",
    "welcome_text": (
        "欢迎添加本店专属管家！\n"
        "点击下方卡片填写手机号，即可领取【房费全年7折券】"
        "（自领取日起1年内有效，可用于本店房费）。"
    ),
    "welcome_link_title": "填写手机号 · 领取房费7折券",
    "welcome_link_desc": "提交后开通专属管家，并获1年房费7折优惠",
    "coupon_name": "企微好友专享 · 房费7折券",
    "coupon_discount_rate": 0.7,
    "coupon_valid_days": 365,
    "callback_token": "",
    "callback_aes_key": "",
}

# 旧欢迎语文案：升级时自动换成领券文案（用户已自定义则不覆盖）
_LEGACY_WELCOME_SNIPPETS = (
    "即可开通个性化关怀服务",
    "开通专属管家",
)


def _add_columns(engine, table: str, columns: dict[str, str]):
    insp = inspect(engine)
    if not insp.has_table(table):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def ensure_wecom_schema(engine):
    AppSetting.__table__.create(bind=engine, checkfirst=True)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    if "wecom_msg_tasks" not in tables:
        need.append(WecomMsgTask.__table__)
    if "wecom_bind_tickets" not in tables:
        need.append(WecomBindTicket.__table__)
    if "guest_coupons" not in tables:
        need.append(GuestCoupon.__table__)
    if "wecom_callback_events" not in tables:
        need.append(WecomCallbackEvent.__table__)
    if "oneid_phone_conflicts" not in tables:
        need.append(OneIdPhoneConflict.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)

    _add_columns(
        engine,
        "guest_coupons",
        {
            "recipient_name": "VARCHAR(80)",
            "channel": "VARCHAR(40)",
            "redeem_status": "VARCHAR(20)",
        },
    )
    _add_columns(
        engine,
        "wecom_callback_events",
        {
            "is_deleted": "BOOLEAN DEFAULT FALSE",
            "deleted_at": "TIMESTAMP",
        },
    )
    _add_columns(
        engine,
        "oneid_phone_conflicts",
        {
            "match_type": "VARCHAR(40)",
        },
    )


def ensure_wecom_defaults(db: Session):
    row = db.query(AppSetting).filter_by(key=WECOM_SETTING_KEY).first()
    if not row:
        cfg = dict(DEFAULT_WECOM_CONFIG)
        cfg["callback_token"] = secrets.token_urlsafe(16)
        db.add(AppSetting(key=WECOM_SETTING_KEY, value_json=json.dumps(cfg, ensure_ascii=False)))
        db.commit()
        return
    try:
        data = json.loads(row.value_json or "{}")
    except json.JSONDecodeError:
        data = {}
    changed = False
    for k, v in DEFAULT_WECOM_CONFIG.items():
        if k not in data:
            data[k] = v
            changed = True
    if not data.get("callback_token"):
        data["callback_token"] = secrets.token_urlsafe(16)
        changed = True
    # 存量：有 corp_id + secret 时，把默认 unconfigured 升到 verified/enabled
    st = str(data.get("status") or "unconfigured")
    if st == "unconfigured" and data.get("corp_id") and data.get("app_secret"):
        data["status"] = "enabled" if data.get("enabled") else "verified"
        changed = True
    # 仍是旧欢迎语时，升级为领券文案
    wt = str(data.get("welcome_text") or "")
    if any(s in wt for s in _LEGACY_WELCOME_SNIPPETS) and "7折" not in wt:
        data["welcome_text"] = DEFAULT_WECOM_CONFIG["welcome_text"]
        data["welcome_link_title"] = DEFAULT_WECOM_CONFIG["welcome_link_title"]
        data["welcome_link_desc"] = DEFAULT_WECOM_CONFIG["welcome_link_desc"]
        changed = True
    if changed:
        row.value_json = json.dumps(data, ensure_ascii=False)
        db.commit()
