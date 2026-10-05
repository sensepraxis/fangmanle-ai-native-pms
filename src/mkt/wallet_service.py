# SPDX-License-Identifier: Apache-2.0
"""客人券包钱包业务：列券 / 核销 / 查码 / 分组 / 公私域判定。

原 `wecom/wecom_service.py` 中的纯钱包业务函数抽出至此。与"通道"无关，
所以未来 Line/Telegram 等通道适配时，本模块无需改动。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from guests.phone_utils import _digits
from mkt.wallet_norm import NATIVE_WALLET_SOURCE, WALLET_SOURCE_LABEL, normalize_wallet_source
from models import Guest, GuestCoupon, Order


def _coupon_to_public(c: GuestCoupon, *, guest: Guest | None = None) -> dict:
    rate = float(c.discount_rate or 0.7)
    zhe = int(round(rate * 10)) if rate * 10 == int(rate * 10) else round(rate * 10, 1)
    status = c.status or "active"
    if status == "active" and c.valid_until and c.valid_until < datetime.now():
        status = "expired"
    redeem = c.redeem_status or ("redeemed" if c.used_at or status == "used" else "unused")
    if status == "used":
        redeem = "redeemed"
    recipient = c.recipient_name or (guest.name if guest else None)
    src = normalize_wallet_source(c.source)
    # 外渠道券：360 可见，但不提供本店核销按钮
    external = src in ("meituan", "douyin", "xhs", "ota")
    can_redeem = (not external) and status == "active" and redeem == "unused"
    return {
        "id": c.id,
        "guest_id": c.guest_id,
        "grant_id": getattr(c, "grant_id", None),
        "recipient_name": recipient,
        "code": c.code,
        "name": c.name,
        "channel": c.channel or WALLET_SOURCE_LABEL.get(src, "其他"),
        "coupon_type": c.coupon_type or "room_rate",
        "discount_rate": rate,
        "discount_label": f"{zhe}折" if (c.coupon_type or "") == "room_rate" else None,
        "source": src,
        "source_label": WALLET_SOURCE_LABEL.get(src, src),
        "wallet_source": src,
        "status": status,
        "redeem_status": redeem,
        "can_redeem": can_redeem,
        "redeem_blocked_reason": "请到对应平台核销" if external and redeem == "unused" else None,
        "valid_from": c.valid_from.isoformat(sep=" ", timespec="seconds") if c.valid_from else None,
        "valid_until": c.valid_until.isoformat(sep=" ", timespec="seconds") if c.valid_until else None,
        "used_at": c.used_at.isoformat(sep=" ", timespec="seconds") if c.used_at else None,
        "note": c.note,
    }


def _is_private_domain_coupon(c: GuestCoupon | dict) -> bool:
    """私域发放：本店营销 / 企微。外渠道券也进 360 全量列表，但券包分组可筛。"""
    if isinstance(c, dict):
        src = str(c.get("source") or c.get("wallet_source") or "")
        ch = str(c.get("channel") or "")
    else:
        src = str(c.source or "")
        ch = str(c.channel or "")
    ns = normalize_wallet_source(src)
    if ns in (NATIVE_WALLET_SOURCE, "wecom"):
        return True
    if ch in ("企业微信", "landing_page", "私域", "客群发放", "指定发放") or "企微" in ch:
        return True
    return False


def list_guest_coupons(db: Session, guest_id: int) -> list[dict]:
    guest = db.get(Guest, guest_id)
    rows = db.query(GuestCoupon).filter_by(guest_id=guest_id).order_by(GuestCoupon.id.desc()).all()
    out = []
    for c in rows:
        pub = _coupon_to_public(c, guest=guest)
        # 本店批次：用营销批次展示名/面值
        if pub.get("source") == NATIVE_WALLET_SOURCE and getattr(c, "grant_id", None):
            try:
                from mkt.mkt_service import _coupon_label
                from models import MktCoupon, MktCouponGrant

                grant = db.get(MktCouponGrant, c.grant_id)
                mc = db.get(MktCoupon, grant.coupon_id) if grant else None
                if mc:
                    pub["discount_label"] = _coupon_label(mc)
                    pub["name"] = mc.name or pub["name"]
                    pub["batch_no"] = mc.batch_no
            except Exception:
                pass
        out.append(pub)
    return out


def build_member_coupon_wallet(db: Session, guest_id: int) -> dict:
    """老会员券包：仅私域券，按可使用 / 已核销 / 已过期分组。"""
    all_pub = [c for c in list_guest_coupons(db, guest_id) if _is_private_domain_coupon(c)]
    unused: list[dict] = []
    used: list[dict] = []
    expired: list[dict] = []
    for c in all_pub:
        st = str(c.get("status") or "")
        redeem = str(c.get("redeem_status") or "")
        if st == "expired" or (
            st == "active" and c.get("valid_until") and str(c["valid_until"]) < datetime.now().isoformat(sep=" ")
        ):
            # _coupon_to_public 已把过期标为 expired；双保险
            if redeem in ("redeemed",) or st == "used":
                used.append(c)
            else:
                expired.append(c)
        elif st == "used" or redeem == "redeemed":
            used.append(c)
        elif c.get("can_redeem") or (st == "active" and redeem == "unused"):
            unused.append(c)
        else:
            expired.append(c)
    return {
        "coupons": all_pub,
        "unused": unused,
        "used": used,
        "expired": expired,
        "summary": {
            "total": len(all_pub),
            "unused": len(unused),
            "used": len(used),
            "expired": len(expired),
        },
    }


def lookup_coupon_by_code(db: Session, code: str) -> dict:
    """前台按券码查询（扫码/手输）。支持 GuestCoupon 与券池 grant 码。"""
    raw = (code or "").strip()
    if not raw:
        raise ValidationError("请输入券码")
    row = db.query(GuestCoupon).filter(GuestCoupon.code == raw).first()
    if not row:
        row = db.query(GuestCoupon).filter(GuestCoupon.code.ilike(raw)).first()
    if not row:
        # 券池实例尚未投影时：按 grant 码补投影后再查
        from models import MktCoupon, MktCouponGrant

        grant = db.query(MktCouponGrant).filter(MktCouponGrant.code == raw).first()
        if not grant:
            grant = db.query(MktCouponGrant).filter(MktCouponGrant.code.ilike(raw)).first()
        if grant:
            from mkt.mkt_service import _ensure_guest_coupon_from_mkt

            coupon = db.get(MktCoupon, grant.coupon_id)
            if coupon:
                row = _ensure_guest_coupon_from_mkt(db, grant.hotel_id, grant.guest_id, coupon, grant)
                db.commit()
    if not row:
        raise NotFoundError(f"未找到券码 {raw.upper()}")
    guest = db.get(Guest, row.guest_id)
    pub = _coupon_to_public(row, guest=guest)
    pub["guest_name"] = guest.name if guest else None
    pub["guest_phone_mask"] = (
        f"{_digits(guest.phone)[:3]}****{_digits(guest.phone)[-4:]}"
        if guest and len(_digits(guest.phone)) >= 7
        else (guest.phone if guest else None)
    )
    return pub


def redeem_guest_coupon(
    db: Session,
    *,
    coupon_id: int | None = None,
    code: str | None = None,
    order_id: int | None = None,
    operator: str = "前台",
    remark: str = "",
) -> dict:
    """360 / 前台核销客人券包。

    - 本店发行（grant_id / 同码 Grant）→ 统一走 redeem_instance，Wallet+Grant 同事务
    - 企微直发等无 Grant 的私域券 → 仅更新 GuestCoupon
    - 外渠道（美团/抖音等）→ demo：标记不可在本店核销
    """
    row: GuestCoupon | None = None
    if coupon_id:
        row = db.get(GuestCoupon, coupon_id)
    elif code:
        raw = (code or "").strip()
        row = db.query(GuestCoupon).filter(GuestCoupon.code == raw).first()
        if not row:
            row = db.query(GuestCoupon).filter(GuestCoupon.code.ilike(raw)).first()
    if not row:
        raise NotFoundError("优惠券不存在")

    guest = db.get(Guest, row.guest_id)
    pub = _coupon_to_public(row, guest=guest)
    if pub["status"] == "expired":
        raise InvalidStateError("优惠券已过期，无法核销")
    if pub["redeem_status"] == "redeemed" or pub["status"] == "used":
        raise InvalidStateError("优惠券已核销，请勿重复操作")
    if pub["status"] != "active":
        raise InvalidStateError(f"优惠券状态不可核销：{pub['status']}")

    src = normalize_wallet_source(row.source)
    if src in ("meituan", "douyin", "xhs", "ota"):
        raise InvalidStateError(
            f"该券来自「{pub.get('source_label') or src}」，请到对应平台核销（本店前台暂不代核）",
        )

    # 解析本店 Grant
    grant = None
    if getattr(row, "grant_id", None):
        from models import MktCouponGrant

        grant = db.get(MktCouponGrant, row.grant_id)
    if not grant and row.code:
        from models import MktCouponGrant

        grant = db.query(MktCouponGrant).filter_by(code=row.code).first()
        if grant:
            row.grant_id = grant.id
            row.source = NATIVE_WALLET_SOURCE

    if grant:
        from mkt.mkt_coupon_engine import redeem_instance

        result = redeem_instance(
            db,
            int(row.hotel_id),
            instance_id=grant.id,
            order_id=order_id,
            cashier=operator,
        )
        if not result.get("ok"):
            raise InvalidStateError(result.get("reason") or "核销失败")
        db.refresh(row)
        out = _coupon_to_public(row, guest=guest)
        out["guest_name"] = guest.name if guest else None
        out["redeemed_at"] = result.get("used_at") or (
            row.used_at.isoformat(sep=" ", timespec="seconds") if row.used_at else None
        )
        out["order_id"] = order_id
        out["instance_id"] = grant.id
        out["wallet_source"] = NATIVE_WALLET_SOURCE
        out["message"] = result.get("message") or (
            f"已核销本店券「{out.get('name')}」"
            + (f"，抵扣 ¥{result.get('used_amount')}" if result.get("used_amount") else "")
        )
        return out

    # 无 Grant：企微直发等 Wallet-only
    order = None
    if order_id:
        order = db.get(Order, order_id)
        if not order:
            raise NotFoundError("关联订单不存在")
        if order.guest_id and order.guest_id != row.guest_id:
            raise InvalidStateError("订单不属于该券持有人")

    now = datetime.now()
    bits = [f"前台核销 · {operator} · {now.strftime('%Y-%m-%d %H:%M')}"]
    if order:
        bits.append(f"订单 {order.order_no}(#{order.id})")
    if remark.strip():
        bits.append(remark.strip()[:120])
    line = "；".join(bits)
    row.source = src if src else "wecom"
    row.redeem_status = "redeemed"
    row.status = "used"
    row.used_at = now
    row.note = ((row.note or "").rstrip() + "\n" + line).strip() if row.note else line

    db.commit()
    db.refresh(row)

    from events import emit

    emit(
        "coupon.redeemed",
        {
            "hotel_id": row.hotel_id,
            "code": row.code,
            "source": row.source,
            "guest_id": row.guest_id,
            "coupon_id": row.id,
            "order_id": order.id if order else None,
        },
    )

    out = _coupon_to_public(row, guest=guest)
    out["guest_name"] = guest.name if guest else None
    out["redeemed_at"] = now.isoformat(sep=" ", timespec="seconds")
    out["order_id"] = order.id if order else None
    out["order_no"] = order.order_no if order else None
    out["wallet_source"] = row.source
    out["message"] = f"已核销 {out['discount_label']}「{out['name']}」" + (
        f"，关联订单 {order.order_no}" if order else ""
    )
    return out


def _coupon_offer_public(cfg: dict) -> dict:
    """H5 配置中券展示字段的对外归一（来自 wecom cfg.coupon_*）。"""
    return {
        "name": cfg.get("coupon_name") or "企微好友专享 · 房费7折券",
        "discount_rate": float(cfg.get("coupon_discount_rate") or 0.7),
        "valid_days": int(cfg.get("coupon_valid_days") or 365),
    }
