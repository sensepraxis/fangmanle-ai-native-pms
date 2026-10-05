# SPDX-License-Identifier: Apache-2.0
"""营销仪表盘与时间线。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    Guest,
    HotelMktSettings,
    MktCampaign,
    MktCoupon,
    MktCouponGrant,
    WxLandingPage,
)


def mkt_dashboard(db: Session, hotel_id: int) -> dict:
    camps = db.query(MktCampaign).filter_by(hotel_id=hotel_id).all()
    coupons = db.query(MktCoupon).filter_by(hotel_id=hotel_id).all()
    grants = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id).all()
    pages = db.query(WxLandingPage).filter_by(hotel_id=hotel_id).all()
    running = sum(1 for c in camps if c.status == "running")
    pending = sum(1 for c in camps if c.status == "pending")
    active_batches = sum(1 for c in coupons if c.status == "active")
    granted = len(grants)
    used = sum(1 for g in grants if g.status == "used")
    return {
        "kpi": {
            "campaigns_running": running,
            "campaigns_pending": pending,
            "campaigns_total": len(camps),
            "coupon_batches_active": active_batches,
            "grants": granted,
            "used": used,
            "redeem_rate": round(used / granted * 100, 1) if granted else 0,
            "landing_published": sum(1 for p in pages if p.status == "published"),
            "new_customers_est": min(granted, max(0, granted // 3)),
        },
        "modules": [
            {"key": "dashboard", "title": "私域总览", "phase": "mvp", "path": "/acquisition"},
            {"key": "campaigns", "title": "活动中心", "phase": "mvp", "path": "/acquisition/campaigns"},
            {"key": "coupons", "title": "优惠券中心", "phase": "mvp", "path": "/acquisition/coupons"},
            {"key": "landing", "title": "页面装修器", "phase": "mvp", "path": "/acquisition/landing-pages"},
            {"key": "members", "title": "会员体系设置", "phase": "mvp", "path": "/acquisition/members"},
            {"key": "automation", "title": "配置发放规则", "phase": "mvp", "path": "/acquisition/coupons?tab=rules"},
        ],
        "timeline": _recent_timeline(db, hotel_id),
        "channel": _channel_mirror(db, hotel_id),
        "wecom": _channel_mirror(db, hotel_id),  # 兼容旧前端
    }


def _recent_timeline(db: Session, hotel_id: int) -> list[dict]:
    from infra.i18n import t as _t

    out = []
    for g in db.query(MktCouponGrant).filter_by(hotel_id=hotel_id).order_by(MktCouponGrant.id.desc()).limit(5).all():
        c = db.get(MktCoupon, g.coupon_id)
        guest = db.get(Guest, g.guest_id)
        out.append(
            {
                "at": g.grant_at.isoformat() if g.grant_at else None,
                "text": _t(
                    "发放「{name}」→ {guest}",
                    name=(c.name if c else g.code),
                    guest=(guest.name if guest else g.guest_id),
                ),
                "kind": "grant",
            }
        )
    for camp in (
        db.query(MktCampaign).filter_by(hotel_id=hotel_id).order_by(MktCampaign.updated_at.desc()).limit(3).all()
    ):
        out.append(
            {
                "at": camp.updated_at.isoformat() if camp.updated_at else None,
                "text": _t("活动「{name}」状态 {status}", name=camp.name, status=camp.status),
                "kind": "campaign",
            }
        )
    out.sort(key=lambda x: x.get("at") or "", reverse=True)
    return out[:8]


def _channel_mirror(db: Session, hotel_id: int) -> dict:
    from extensions.messaging.facade import channel_status

    ch = channel_status(db)
    settings = db.query(HotelMktSettings).filter_by(hotel_id=hotel_id).first()
    details = ch.get("details") if isinstance(ch.get("details"), dict) else {}
    return {
        "vendor": ch.get("vendor"),
        "label": ch.get("label"),
        "enabled": bool(ch.get("connected")),
        "status": ch.get("status") or "unconfigured",
        "owner_type": details.get("owner_type") or "saas_self",
        "corp_id_hint": ch.get("hint") or "",
        "hint": ch.get("hint") or "",
        "agent_id": details.get("agent_id"),
        "follow_userid": details.get("follow_userid"),
        "default_receiver_userid": settings.default_receiver_userid if settings else None,
        "config_path": ch.get("config_path") or "/a-ai-core/private-channel",
        "capabilities": ch.get("capabilities") or {},
    }


# 兼容旧 import 名
_wecom_mirror = _channel_mirror
