# SPDX-License-Identifier: Apache-2.0
"""私域运营防腐门面：业务只依赖本模块，不 import wecom / LINE / WhatsApp SDK。

两层能力：
- private_ops_core：分群 / 发券 / 规则 / 看板（全球）
- wecom_deep：侧边栏 / 外部联系人全量同步等（仅企微）
"""

from __future__ import annotations

import os
from typing import Any, Optional

from sqlalchemy.orm import Session

CONFIG_PATH = "/a-ai-core/private-channel"
WECOM_EXTRAS_PATH = "/a-ai-core/wecom-integration"

_VENDOR_LABEL = {
    "wecom": "企业微信",
    "line": "LINE",
    "whatsapp": "WhatsApp",
    "webhook": "Webhook",
    "sms": "SMS",
    "email": "Email",
}

# 可作为「私域建联」的身份 source
IM_IDENTITY_SOURCES = frozenset({"wecom", "line", "whatsapp", "webhook"})


def current_vendor() -> str:
    from messaging import current_vendor as _cv

    return (_cv() or "wecom").strip().lower()


def identity_source(vendor: str | None = None) -> str:
    """GuestIdentity.source 取值 = 当前 messaging primary vendor。"""
    return (vendor or current_vendor()).strip().lower()


def vendor_label(vendor: str | None = None) -> str:
    v = identity_source(vendor)
    return _VENDOR_LABEL.get(v, v)


def config_path_for(vendor: str | None = None) -> str:
    return CONFIG_PATH


def resolve_fallbacks() -> list[str]:
    from infra.private_channel import resolve_fallback

    return resolve_fallback()


def resolve_packs() -> list[str]:
    from infra.private_channel import resolve_packs as _rp

    return _rp()


def region_profile() -> str:
    """粗粒度区域画像：cn（企微深集成）/ intl（LINE/WA + 短信邮件）。"""
    v = current_vendor()
    if v == "wecom":
        return "cn"
    return "intl"


def identity_sources_for_reachability() -> set[str]:
    """发券 / 分群可达性认可的身份来源。"""
    src = identity_source()
    sources = {src}
    # 过渡：非 wecom 酒店仍认可历史企微身份
    if src != "wecom":
        sources.add("wecom")
    return sources


def guest_channel_reachable(db: Session, guest_id: int) -> bool:
    """客人是否已在当前私域 IM 建联（通道无关名）。"""
    from models import GuestIdentity

    sources = identity_sources_for_reachability()
    return (
        db.query(GuestIdentity.id)
        .filter(
            GuestIdentity.guest_id == int(guest_id),
            GuestIdentity.source.in_(list(sources)),
        )
        .first()
        is not None
    )


def channel_status(db: Session) -> dict[str, Any]:
    """
    统一通道状态（看板 / 配置页用）。
    connected：具备可触达能力（有密钥或已验证 / demo 可用）
    selected：酒店已选定该 vendor（YAML / AppSetting）
    """
    from infra.private_channel import load_private_channel_config, resolve_fallback, resolve_packs

    vendor = current_vendor()
    label = vendor_label(vendor)
    packs = resolve_packs()
    fallback = resolve_fallback()
    cfg = {}
    try:
        cfg = load_private_channel_config(db) or {}
    except Exception:
        cfg = {}

    connected = False
    status = "unconfigured"
    hint = ""
    extras: dict[str, Any] = {}

    if vendor == "wecom":
        try:
            from application.wecom import load_wecom_config_masked

            extras = load_wecom_config_masked(db) or {}
        except Exception:
            extras = {}
        connected = bool(extras.get("enabled") or extras.get("status") in ("enabled", "verified"))
        status = str(extras.get("status") or ("enabled" if connected else "unconfigured"))
        hint = str(extras.get("corp_id") or "")[:4] + "****" if extras.get("corp_id") else ""
    elif vendor == "line":
        line = cfg.get("line") if isinstance(cfg.get("line"), dict) else {}
        token = (
            str(line.get("channel_access_token") or "").strip()
            or (os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
        )
        has_token = bool(token)
        connected = True
        status = "enabled" if has_token or line.get("enabled") else "pending_credentials"
        hint = (str(line.get("channel_id") or "")[:4] + "****") if line.get("channel_id") else ""
        extras = {
            "enabled": True,
            "status": status,
            "has_token": has_token,
            "demo_mode": not has_token,
        }
    elif vendor == "whatsapp":
        wa = cfg.get("whatsapp") if isinstance(cfg.get("whatsapp"), dict) else {}
        token = str(wa.get("access_token") or "").strip() or (os.environ.get("WHATSAPP_ACCESS_TOKEN") or "").strip()
        phone_id = (
            str(wa.get("phone_number_id") or "").strip() or (os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        )
        has_creds = bool(token and phone_id)
        connected = True
        status = "enabled" if has_creds or wa.get("enabled") else "pending_credentials"
        hint = (phone_id[:4] + "****") if phone_id else ""
        extras = {
            "enabled": True,
            "status": status,
            "has_token": has_creds,
            "demo_mode": not has_creds,
        }
    else:  # webhook
        connected = True
        status = "enabled"
        extras = {"enabled": True, "status": "enabled"}

    has_wecom_deep = "wecom_deep" in packs and vendor == "wecom"
    return {
        "vendor": vendor,
        "label": label,
        "selected": True,
        "connected": connected,
        "status": status,
        "hint": hint,
        "config_path": CONFIG_PATH,
        "extras_path": WECOM_EXTRAS_PATH if vendor == "wecom" else None,
        "region_profile": region_profile(),
        "packs": packs,
        "fallback": fallback,
        "capabilities": {
            # 全球内核
            "private_ops_core": "private_ops_core" in packs,
            "bind_ticket": vendor in ("wecom", "line", "whatsapp"),
            "staff_notify": vendor in ("wecom", "line", "whatsapp", "webhook"),
            "push_text": vendor in ("wecom", "line", "whatsapp", "webhook"),
            "fallback_sms": "sms" in fallback,
            "fallback_email": "email" in fallback,
            # 企微增强
            "wecom_deep": has_wecom_deep,
            "care_sidebar": has_wecom_deep,
            "sync_external_contacts": has_wecom_deep,
            "group_msg_helper": has_wecom_deep,
        },
        "details": extras,
    }


def private_guest_ids(db: Session, *, hotel_id: int | None = None) -> set[int]:
    """当前通道下已建联客人 + 有私域钱包的客人。"""
    from models import GuestIdentity, MktGuestWallet

    sources = identity_sources_for_reachability()
    ids = {
        int(r[0])
        for r in db.query(GuestIdentity.guest_id).filter(GuestIdentity.source.in_(list(sources))).all()
        if r[0] is not None
    }
    if hotel_id is not None:
        wallet = {
            int(r[0]) for r in db.query(MktGuestWallet.guest_id).filter_by(hotel_id=hotel_id).all() if r[0] is not None
        }
        ids |= wallet
    return ids


def count_links_since(db: Session, since, *, source: str | None = None) -> int:
    from models import GuestIdentity

    if source:
        sources = {identity_source(source)}
    else:
        sources = identity_sources_for_reachability()
    q = db.query(GuestIdentity.id).filter(
        GuestIdentity.source.in_(list(sources)),
        GuestIdentity.linked_at.isnot(None),
        GuestIdentity.linked_at >= since,
    )
    return int(q.count() or 0)


def link_daily_timestamps(db: Session, *, source: str | None = None) -> list:
    from models import GuestIdentity

    if source:
        sources = {identity_source(source)}
    else:
        sources = identity_sources_for_reachability()
    return [
        r[0]
        for r in db.query(GuestIdentity.linked_at)
        .filter(
            GuestIdentity.source.in_(list(sources)),
            GuestIdentity.linked_at.isnot(None),
        )
        .all()
    ]


def send_text(*, hotel_id: int, content: str, guest_id: int | None = None, **kwargs: Any) -> dict:
    """主通道发送；失败或仅 demo 时按 fallback 降级（opt-in）。"""
    from messaging import get_channel, get_fallback_channels

    use_fallback = bool(kwargs.pop("use_fallback", True))
    ch = get_channel()
    result = ch.send_text(hotel_id=hotel_id, content=content, guest_id=guest_id, **kwargs)
    if not use_fallback:
        return result
    if result.get("ok") and not result.get("demo"):
        return result
    attempts = [result]
    for fb in get_fallback_channels():
        try:
            r = fb.send_text(hotel_id=hotel_id, content=content, guest_id=guest_id, **kwargs)
            attempts.append(r)
            if r.get("ok") and not r.get("demo"):
                r = dict(r)
                r["via_fallback"] = True
                r["primary_result"] = result
                return r
        except Exception as e:
            attempts.append({"ok": False, "vendor": getattr(fb, "vendor", "?"), "error": str(e)})
    # 全部 demo / 失败：返回主结果，附带 attempts
    out = dict(result)
    out["fallback_attempts"] = attempts[1:]
    return out


__all__ = [
    "CONFIG_PATH",
    "WECOM_EXTRAS_PATH",
    "IM_IDENTITY_SOURCES",
    "channel_status",
    "config_path_for",
    "count_links_since",
    "current_vendor",
    "guest_channel_reachable",
    "identity_source",
    "identity_sources_for_reachability",
    "link_daily_timestamps",
    "private_guest_ids",
    "region_profile",
    "resolve_fallbacks",
    "resolve_packs",
    "send_text",
    "vendor_label",
]
