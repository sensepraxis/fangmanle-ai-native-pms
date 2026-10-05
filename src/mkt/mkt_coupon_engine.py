# SPDX-License-Identifier: Apache-2.0
"""优惠券系统核心：券码算法 / 有效期 / 状态机 / 发放 / 核销 / 触发（权威稿实现）。

表名沿用 mkt_coupons / mkt_coupon_grants（兼容落地页 FK），语义对齐
mkt_coupon_batch / mkt_coupon_instance；另含 trigger / grant_log / redeem。
租户字段 API 侧暴露为 property_id，存储仍为 hotel_id。
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException  # noqa: F401  (except 分支用)
from sqlalchemy.exc import IntegrityError
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
from mkt.wallet_norm import NATIVE_WALLET_SOURCE
from models import (
    Guest,
    GuestCoupon,
    MktCoupon,
    MktCouponGrant,
    MktCouponGrantLog,
    MktCouponRedeem,
    MktCouponTrigger,
    Order,
)

# ---------- 常量 ----------

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
PREFIX_MAP = {
    "CASH_ROOM": "CSH",
    "CASH_ALL": "CSH",
    "DISCOUNT": "DSC",
    "BENEFIT": "BNF",
}

COUPON_TYPES_V2 = ("CASH_ROOM", "CASH_ALL", "DISCOUNT", "BENEFIT")
# 旧类型 → 新类型（读兼容）
LEGACY_TYPE_MAP = {
    "discount": "DISCOUNT",
    "reduction": "CASH_ROOM",  # 有门槛默认指定/有门槛；threshold=0 再判 CASH_ALL
    "night_up": "BENEFIT",
    "room_up": "BENEFIT",
    "time_window": "BENEFIT",
}

INSTANCE_STATUSES = ("CLAIMABLE", "AVAILABLE", "USED", "EXPIRED", "VOID")
BATCH_STATUSES = ("draft", "active", "paused", "expired")
VALIDITY_MODES = ("FIXED", "RELATIVE")
TRIGGER_EVENTS = (
    "NEW_WECHAT_MEMBER",
    "HOLIDAY",
    "REG_DAYS",
    "CHECKOUT_DAYS",
    "BIRTHDAY",
    "CUSTOM",
)

# 实例旧状态 → 新状态
LEGACY_INSTANCE_STATUS = {
    "unused": "AVAILABLE",
    "used": "USED",
    "expired": "EXPIRED",
    "void": "VOID",
}


def _now() -> datetime:
    return datetime.now()


def normalize_coupon_type(raw: str, *, threshold: float = 0) -> str:
    t = str(raw or "").strip()
    if t in COUPON_TYPES_V2:
        return t
    mapped = LEGACY_TYPE_MAP.get(t.lower() if t else "")
    if mapped == "CASH_ROOM" and float(threshold or 0) <= 0 and t.lower() == "reduction":
        return "CASH_ALL"
    if mapped:
        return mapped
    raise InvalidStateError(f"券类型无效：{raw}（支持 {', '.join(COUPON_TYPES_V2)}）")


def normalize_instance_status(st: Optional[str]) -> str:
    s = str(st or "AVAILABLE").strip()
    if s in INSTANCE_STATUSES:
        return s
    return LEGACY_INSTANCE_STATUS.get(s, s.upper() if s.upper() in INSTANCE_STATUSES else "AVAILABLE")


# ---------- §4 券码算法 ----------


def b32(n: int, width: int) -> str:
    s = ""
    n = abs(int(n))
    for _ in range(width):
        s = CROCKFORD[n % 32] + s
        n //= 32
    return s


def gen_coupon_code(coupon_type: str) -> str:
    ctype = normalize_coupon_type(coupon_type)
    prefix = PREFIX_MAP[ctype]
    tseg = b32(int(time.time()) // 60, 5)
    rseg = b32(int.from_bytes(secrets.token_bytes(4), "big"), 5)
    payload = prefix + tseg + rseg
    num = 0
    for ch in payload:
        num = num * 32 + CROCKFORD.index(ch)
    check = CROCKFORD[num % 32]
    return f"{prefix}-{tseg}-{rseg}-{check}"


def verify_code_format(code: str) -> bool:
    parts = (code or "").strip().upper().split("-")
    if len(parts) != 4:
        return False
    if len(parts[0]) != 3 or len(parts[1]) != 5 or len(parts[2]) != 5 or len(parts[3]) != 1:
        return False
    payload = "".join(parts[:3])
    if any(c not in CROCKFORD for c in payload):
        return False
    if parts[3][0] not in CROCKFORD:
        return False
    num = 0
    for ch in payload:
        num = num * 32 + CROCKFORD.index(ch)
    return CROCKFORD[num % 32] == parts[3][0]


def reserve_code(db: Session, coupon_type: str) -> str:
    """生成全局唯一券码；依赖 UNIQUE(code) + 冲突重试。"""
    last_err: Optional[Exception] = None
    for _ in range(8):
        code = gen_coupon_code(coupon_type)
        exists = db.query(MktCouponGrant.id).filter_by(code=code).first()
        if exists:
            continue
        # 同时查 GuestCoupon，避免投影撞码
        if db.query(GuestCoupon.id).filter_by(code=code).first():
            continue
        return code
    raise BusinessError(f"coupon_code collision after retry: {last_err}")


# ---------- §2 face_text / 批次字段 ----------


def build_face_text(
    coupon_type: str,
    *,
    reduce_amount: Optional[float] = None,
    threshold: Optional[float] = None,
    discount_rate: Optional[float] = None,
    max_discount: Optional[float] = None,
    benefit_key: Optional[str] = None,
    benefit_value: Optional[str] = None,
    face_text: Optional[str] = None,
) -> str:
    if face_text and str(face_text).strip():
        return str(face_text).strip()[:128]
    from mkt.coupon_strategy import build_face_text_by_type

    ctype = normalize_coupon_type(coupon_type, threshold=float(threshold or 0))
    return build_face_text_by_type(
        ctype,
        reduce_amount=reduce_amount,
        threshold=threshold,
        discount_rate=discount_rate,
        max_discount=max_discount,
        benefit_key=benefit_key,
        benefit_value=benefit_value,
    )


def resolve_batch_benefit_fields(coupon: MktCoupon) -> dict[str, Any]:
    """从批次行读出规范化权益字段（兼容旧 face_value）。"""
    ctype = normalize_coupon_type(
        getattr(coupon, "coupon_type", None) or coupon.type,
        threshold=float(coupon.threshold or 0),
    )
    reduce_amount = getattr(coupon, "reduce_amount", None)
    if reduce_amount is None and ctype in ("CASH_ROOM", "CASH_ALL"):
        reduce_amount = coupon.face_value
    discount_rate = getattr(coupon, "discount_rate", None)
    if discount_rate is None and ctype == "DISCOUNT":
        discount_rate = coupon.face_value
    benefit_key = getattr(coupon, "benefit_key", None)
    benefit_value = getattr(coupon, "benefit_value", None)
    if ctype == "BENEFIT" and not benefit_key:
        legacy = str(coupon.type or "").lower()
        if legacy == "night_up":
            benefit_key, benefit_value = "FREE_NIGHT", str(int(float(coupon.face_value or 2)))
        elif legacy == "room_up":
            benefit_key, benefit_value = (
                "ROOM_UPGRADE",
                str((getattr(coupon, "face_text", None) or "") or (_scope(coupon).get("face_text") or "豪华房")),
            )
        elif legacy == "time_window":
            benefit_key, benefit_value = (
                "CUSTOM",
                str(getattr(coupon, "face_text", None) or _scope(coupon).get("face_text") or "指定时段"),
            )
        else:
            benefit_key, benefit_value = "CUSTOM", str(getattr(coupon, "face_text", None) or coupon.name)
    # 结构化字段按当前 X-Locale 重算 face_text；自定义 BENEFIT 文案再尝试 t()
    stored_face = getattr(coupon, "face_text", None) or _scope(coupon).get("face_text")
    use_stored = bool(ctype == "BENEFIT" and str(benefit_key or "").upper() in ("", "CUSTOM") and stored_face)
    if use_stored:
        from infra.i18n import t as _t

        face = _t(str(stored_face))[:128]
    else:
        face = build_face_text(
            ctype,
            reduce_amount=float(reduce_amount) if reduce_amount is not None else None,
            threshold=float(coupon.threshold or 0),
            discount_rate=float(discount_rate) if discount_rate is not None else None,
            max_discount=float(coupon.max_discount) if getattr(coupon, "max_discount", None) is not None else None,
            benefit_key=benefit_key,
            benefit_value=benefit_value,
            face_text=None,
        )
    scope_type = getattr(coupon, "scope_type", None) or ("ROOM_SPECIFIED" if ctype == "CASH_ROOM" else "ALL")
    return {
        "coupon_type": ctype,
        "reduce_amount": float(reduce_amount or 0) if reduce_amount is not None else None,
        "threshold": float(coupon.threshold or 0),
        "discount_rate": float(discount_rate) if discount_rate is not None else None,
        "max_discount": float(coupon.max_discount) if getattr(coupon, "max_discount", None) is not None else None,
        "benefit_key": benefit_key,
        "benefit_value": benefit_value,
        "face_text": face,
        "scope_type": scope_type,
        "scope_rooms": _scope_rooms(coupon),
    }


def _scope(coupon: MktCoupon) -> dict:
    import json

    raw = coupon.scope_json
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else dict(raw)
    except Exception:
        return {}


def _scope_rooms(coupon: MktCoupon) -> list:
    import json

    raw = getattr(coupon, "scope_rooms", None)
    if raw:
        try:
            return json.loads(raw) if isinstance(raw, str) else list(raw)
        except Exception:
            pass
    rooms = _scope(coupon).get("rooms") or _scope(coupon).get("room_types")
    if isinstance(rooms, list):
        return rooms
    if rooms == "all":
        return []
    return []


# ---------- §5 有效期 ----------


def compute_instance_validity(
    coupon: MktCoupon,
    *,
    claim_at: Optional[datetime] = None,
) -> tuple[datetime, datetime]:
    mode = str(getattr(coupon, "validity_mode", None) or "FIXED").upper()
    if mode not in VALIDITY_MODES:
        mode = "FIXED"
    now = claim_at or _now()
    if mode == "RELATIVE":
        days = int(getattr(coupon, "validity_days", None) or 0)
        if days <= 0:
            raise InvalidStateError("RELATIVE 模式必须设置 validity_days>0")
        vf, vt = now, now + timedelta(days=days)
    else:
        vf = getattr(coupon, "batch_valid_from", None) or coupon.valid_from
        vt = getattr(coupon, "batch_valid_to", None) or coupon.valid_to
        if not vf or not vt:
            raise InvalidStateError("FIXED 模式必须设置 batch_valid_from / batch_valid_to（不可为空）")
        if isinstance(vf, str) or isinstance(vt, str):
            raise InvalidStateError("有效期格式无效")
    if vt <= vf:
        raise InvalidStateError("valid_to 必须晚于 valid_from")
    return vf, vt


# ---------- 批次序列化 ----------


def batch_to_dict(c: MktCoupon, db: Optional[Session] = None) -> dict:
    fields = resolve_batch_benefit_fields(c)
    grants_n = used_n = 0
    if db is not None:
        grants_n = int(getattr(c, "granted_qty", None) or 0)
        if not grants_n:
            grants_n = db.query(MktCouponGrant).filter_by(coupon_id=c.id).count()
        used_n = (
            db.query(MktCouponGrant)
            .filter(
                MktCouponGrant.coupon_id == c.id,
                MktCouponGrant.status.in_(("used", "USED")),
            )
            .count()
        )
    mode = str(getattr(c, "validity_mode", None) or "FIXED").upper()
    vf = getattr(c, "batch_valid_from", None) or c.valid_from
    vt = getattr(c, "batch_valid_to", None) or c.valid_to
    return {
        "id": c.id,
        "property_id": c.hotel_id,
        "hotel_id": c.hotel_id,
        "batch_no": c.batch_no,
        "name": c.name,
        "coupon_type": fields["coupon_type"],
        "type": fields["coupon_type"],  # 兼容旧前端
        "reduce_amount": fields["reduce_amount"],
        "threshold": fields["threshold"],
        "discount_rate": fields["discount_rate"],
        "max_discount": fields["max_discount"],
        "benefit_key": fields["benefit_key"],
        "benefit_value": fields["benefit_value"],
        "face_text": fields["face_text"],
        "face_value": float(c.face_value or 0),  # 兼容
        "discount_label": fields["face_text"],
        "scope_type": fields["scope_type"],
        "scope_rooms": fields["scope_rooms"],
        "scope": _scope(c),
        "total_qty": c.total_qty,
        "granted_qty": grants_n,
        "granted": grants_n,
        "remaining": max(0, int(c.total_qty or 0) - grants_n),
        "per_user_qty": c.per_user_qty,
        "validity_mode": mode,
        "validity_days": getattr(c, "validity_days", None),
        "batch_valid_from": vf.isoformat() if vf else None,
        "batch_valid_to": vt.isoformat() if vt else None,
        "valid_from": vf.isoformat() if vf else None,
        "valid_to": vt.isoformat() if vt else None,
        "status": c.status,
        "used": used_n,
        "redeem_rate": round(used_n / grants_n * 100, 1) if grants_n else 0,
        "created_by": getattr(c, "created_by", None),
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def instance_to_dict(g: MktCouponGrant, coupon: Optional[MktCoupon] = None) -> dict:
    st = normalize_instance_status(g.status)
    ctype = getattr(g, "coupon_type", None) or (resolve_batch_benefit_fields(coupon)["coupon_type"] if coupon else None)
    face = getattr(g, "face_text", None) or (coupon and resolve_batch_benefit_fields(coupon)["face_text"])
    vf = getattr(g, "valid_from", None)
    vt = getattr(g, "valid_to", None)
    if not vf and coupon:
        vf = coupon.valid_from
    if not vt and coupon:
        vt = coupon.valid_to
    return {
        "id": g.id,
        "batch_id": g.coupon_id,
        "coupon_id": g.coupon_id,
        "property_id": g.hotel_id,
        "customer_id": g.guest_id,
        "guest_id": g.guest_id,
        "coupon_code": g.code,
        "code": g.code,
        "coupon_type": ctype,
        "face_text": face,
        "valid_from": vf.isoformat() if vf else None,
        "valid_to": vt.isoformat() if vt else None,
        "grant_event": getattr(g, "grant_event", None),
        "grant_channel": g.grant_channel,
        "grant_at": g.grant_at.isoformat() if g.grant_at else None,
        "claim_at": (getattr(g, "claim_at", None) or g.grant_at).isoformat()
        if (getattr(g, "claim_at", None) or g.grant_at)
        else None,
        "used_at": g.used_at.isoformat() if g.used_at else None,
        "used_order_id": g.used_order_id,
        "used_amount": float(g.used_amount) if getattr(g, "used_amount", None) is not None else None,
        "redeemed_by": getattr(g, "redeemed_by", None),
        "status": st,
    }


# ---------- 发放实例 ----------


def _count_user_grants(db: Session, batch_id: int, guest_id: int) -> int:
    """历史发放张数（不含作废）。"""
    return (
        db.query(MktCouponGrant)
        .filter_by(coupon_id=batch_id, guest_id=guest_id)
        .filter(MktCouponGrant.status.notin_(("VOID", "void")))
        .count()
    )


def _holding_statuses() -> tuple[str, ...]:
    return ("AVAILABLE", "CLAIMABLE", "unused", "available", "claimable")


def _count_holding_grants(db: Session, batch_id: int, guest_id: int) -> int:
    """持有中（未核销、未作废、未过期）张数 —— 占用限领名额。"""
    return (
        db.query(MktCouponGrant)
        .filter_by(coupon_id=batch_id, guest_id=guest_id)
        .filter(MktCouponGrant.status.in_(_holding_statuses()))
        .count()
    )


def guest_batch_ownership(db: Session, coupon: MktCoupon, guest_id: int) -> dict:
    """指定客人对此批次的持有/限领信息。"""
    per = max(1, int(coupon.per_user_qty or 1))
    holding = _count_holding_grants(db, coupon.id, guest_id)
    total = _count_user_grants(db, coupon.id, guest_id)
    used = (
        db.query(MktCouponGrant)
        .filter_by(coupon_id=coupon.id, guest_id=guest_id)
        .filter(MktCouponGrant.status.in_(("USED", "used")))
        .count()
    )
    latest = (
        db.query(MktCouponGrant)
        .filter_by(coupon_id=coupon.id, guest_id=guest_id)
        .order_by(MktCouponGrant.id.desc())
        .first()
    )
    at_limit = holding >= per
    code = None
    status = None
    if latest:
        code = latest.code
        status = normalize_instance_status(latest.status)
    return {
        "guest_id": guest_id,
        "holding": holding,
        "used": used,
        "total": total,
        "per_user_qty": per,
        "at_limit": at_limit,
        "can_grant": not at_limit,
        "latest_code": code,
        "latest_status": status,
    }


def issue_instance(
    db: Session,
    coupon: MktCoupon,
    guest_id: int,
    *,
    grant_event: str = "manual",
    grant_channel: str = "manual",
    auto_claim: bool = True,
    trigger_id: Optional[int] = None,
    skip_dedup_log: bool = False,
    allow_over_limit: bool = False,
    over_limit_reason: Optional[str] = None,
    raise_on_limit: bool = False,
) -> MktCouponGrant:
    """发放一张实例：写券码 + 强制有效期 + 状态机；可选 grant_log 去重。

    - 限领按「持有中」张数计（已核销不占名额）
    - allow_over_limit=True：补偿强制发，可超限领
    - raise_on_limit=True：达限领时抛错（人工发放用）；默认幂等返回已有实例（自动/落地页）
    """
    hotel_id = coupon.hotel_id
    if coupon.status != "active":
        raise InvalidStateError("仅 active 批次可发放")

    fields = resolve_batch_benefit_fields(coupon)
    ctype = fields["coupon_type"]

    # 触发去重
    if trigger_id and not skip_dedup_log:
        exist_log = (
            db.query(MktCouponGrantLog)
            .filter_by(trigger_id=trigger_id, customer_id=guest_id, batch_id=coupon.id)
            .first()
        )
        if exist_log:
            inst = db.get(MktCouponGrant, exist_log.instance_id)
            if inst:
                return inst

    per = max(1, int(coupon.per_user_qty or 1))
    holding = _count_holding_grants(db, coupon.id, guest_id)
    if holding >= per and not allow_over_limit:
        exist = (
            db.query(MktCouponGrant)
            .filter_by(coupon_id=coupon.id, guest_id=guest_id)
            .filter(MktCouponGrant.status.in_(_holding_statuses()))
            .order_by(MktCouponGrant.id.desc())
            .first()
        )
        if raise_on_limit:
            raise InvalidStateError("已达每人限领")
        if exist:
            return exist
        # 无持有中但历史达限（极端）：再查任意非作废
        exist = (
            db.query(MktCouponGrant)
            .filter_by(coupon_id=coupon.id, guest_id=guest_id)
            .order_by(MktCouponGrant.id.desc())
            .first()
        )
        if exist:
            return exist
        raise InvalidStateError("已达每人限领")

    granted = int(getattr(coupon, "granted_qty", None) or 0)
    if not granted:
        granted = db.query(MktCouponGrant).filter_by(coupon_id=coupon.id).count()
    if granted >= int(coupon.total_qty or 0):
        raise InvalidStateError("券已发完")

    now = _now()
    vf, vt = compute_instance_validity(coupon, claim_at=now if auto_claim else now)
    code = reserve_code(db, ctype)
    status = "AVAILABLE" if auto_claim else "CLAIMABLE"

    event = grant_event
    if allow_over_limit:
        event = "manual_compensate"
        reason = (over_limit_reason or "").strip()
        if reason and hasattr(MktCouponGrant, "grant_event"):
            # grant_event 字段短，原因写入 face 旁不可靠；拼进 event 后缀有限
            event = "manual_compensate"

    row = MktCouponGrant(
        hotel_id=hotel_id,
        coupon_id=coupon.id,
        guest_id=guest_id,
        code=code,
        grant_channel=grant_channel if not allow_over_limit else (grant_channel or "guest"),
        grant_at=now,
        status=status,
    )
    # 新列（migrate 后可用）
    if hasattr(MktCouponGrant, "coupon_type"):
        row.coupon_type = ctype
    if hasattr(MktCouponGrant, "face_text"):
        face = fields["face_text"]
        if allow_over_limit and (over_limit_reason or "").strip():
            reason = (over_limit_reason or "").strip()[:40]
            face = f"{face} · 补偿:{reason}" if face else f"补偿:{reason}"
        row.face_text = face
    if hasattr(MktCouponGrant, "valid_from"):
        row.valid_from = vf
        row.valid_to = vt
    if hasattr(MktCouponGrant, "grant_event"):
        row.grant_event = event
    if hasattr(MktCouponGrant, "claim_at") and auto_claim:
        row.claim_at = now

    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        # 唯一码冲突：换码重试；若仍有旧 uk_mkt_coupon_guest：回已有实例
        db.expire_all()
        exist = (
            db.query(MktCouponGrant)
            .filter_by(coupon_id=coupon.id, guest_id=guest_id)
            .order_by(MktCouponGrant.id.desc())
            .first()
        )
        if exist and not allow_over_limit:
            return exist
        raise BusinessError(f"发放失败（唯一约束）：{exc}")

    if hasattr(coupon, "granted_qty"):
        coupon.granted_qty = int(getattr(coupon, "granted_qty", 0) or 0) + 1

    if trigger_id or grant_event or allow_over_limit:
        log = MktCouponGrantLog(
            trigger_id=trigger_id,
            batch_id=coupon.id,
            customer_id=guest_id,
            instance_id=row.id,
            grant_event=event,
            granted_at=now,
        )
        db.add(log)
        try:
            db.flush()
        except IntegrityError:
            # uk_dedup：同触发同人同批次已发
            db.expunge(log)

    # 投影 GuestCoupon（前台/H5 兼容）
    _project_guest_coupon(db, hotel_id, guest_id, coupon, row, fields)
    return row


def _project_guest_coupon(
    db: Session,
    hotel_id: int,
    guest_id: int,
    coupon: MktCoupon,
    grant: MktCouponGrant,
    fields: Optional[dict] = None,
) -> Optional[GuestCoupon]:
    fields = fields or resolve_batch_benefit_fields(coupon)
    existing = db.query(GuestCoupon).filter_by(code=grant.code).first()
    st = normalize_instance_status(grant.status)
    if existing:
        if not getattr(existing, "grant_id", None):
            existing.grant_id = grant.id
        existing.source = NATIVE_WALLET_SOURCE
        if st == "USED" and existing.redeem_status != "redeemed":
            existing.redeem_status = "redeemed"
            existing.status = "used"
            existing.used_at = grant.used_at or existing.used_at
        return existing

    guest = db.get(Guest, guest_id)
    ctype = fields["coupon_type"]
    if ctype == "DISCOUNT":
        coupon_type, discount_rate = "room_rate", float(fields["discount_rate"] or 0.7)
    elif ctype in ("CASH_ROOM", "CASH_ALL"):
        coupon_type, discount_rate = "reduction", 1.0
    else:
        coupon_type, discount_rate = (ctype[:40], 1.0)

    vf = getattr(grant, "valid_from", None) or coupon.valid_from
    vt = getattr(grant, "valid_to", None) or coupon.valid_to
    channel_cn = {
        "landing_page": "企业微信",
        "segment": "客群发放",
        "guest": "指定发放",
        "manual": "手动发放",
        "campaign": "活动",
        "trigger": "事件触发",
    }.get(grant.grant_channel or "", grant.grant_channel or "企业微信")

    active = st in ("AVAILABLE", "CLAIMABLE", "unused")
    row = GuestCoupon(
        hotel_id=hotel_id,
        guest_id=guest_id,
        grant_id=grant.id,
        code=grant.code,
        name=coupon.name,
        recipient_name=guest.name if guest else None,
        channel=channel_cn,
        coupon_type=coupon_type,
        discount_rate=discount_rate,
        source=NATIVE_WALLET_SOURCE,
        status="active" if active else ("used" if st == "USED" else "expired"),
        redeem_status="unused" if active else ("redeemed" if st == "USED" else "unused"),
        valid_from=vf,
        valid_until=vt,
        note=f"券池 {coupon.batch_no} · {fields['face_text']} · {grant.code}",
    )
    db.add(row)
    try:
        db.flush()
    except Exception:
        found = db.query(GuestCoupon).filter_by(code=grant.code).first()
        return found
    return row


# ---------- 领取 / 卡包 ----------


def claim_instance(
    db: Session,
    hotel_id: int,
    *,
    code: Optional[str] = None,
    instance_id: Optional[int] = None,
    customer_id: Optional[int] = None,
) -> dict:
    g = None
    if instance_id:
        g = db.query(MktCouponGrant).filter_by(id=instance_id, hotel_id=hotel_id).first()
    elif code:
        g = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, code=code.strip().upper()).first()
        if not g:
            g = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, code=code.strip()).first()
    if not g:
        raise NotFoundError("券实例不存在")
    st = normalize_instance_status(g.status)
    if st == "AVAILABLE":
        return {"ok": True, "already": True, **instance_to_dict(g, db.get(MktCoupon, g.coupon_id))}
    if st != "CLAIMABLE":
        raise InvalidStateError(f"券状态不可领取：{st}")
    if customer_id and g.guest_id and int(g.guest_id) != int(customer_id):
        raise AuthorizationError("券不属于该客人")
    now = _now()
    coupon = db.get(MktCoupon, g.coupon_id)
    if coupon and str(getattr(coupon, "validity_mode", "FIXED")).upper() == "RELATIVE":
        vf, vt = compute_instance_validity(coupon, claim_at=now)
        if hasattr(g, "valid_from"):
            g.valid_from, g.valid_to = vf, vt
    g.status = "AVAILABLE"
    if hasattr(g, "claim_at"):
        g.claim_at = now
    if customer_id and not g.guest_id:
        g.guest_id = int(customer_id)
    if coupon:
        _project_guest_coupon(db, hotel_id, g.guest_id, coupon, g)
    db.commit()
    return {"ok": True, **instance_to_dict(g, coupon)}


def wallet_by_customer(db: Session, hotel_id: int, customer_id: int) -> dict:
    expire_due_instances(db, hotel_id, customer_id=customer_id)
    rows = (
        db.query(MktCouponGrant)
        .filter_by(hotel_id=hotel_id, guest_id=customer_id)
        .order_by(MktCouponGrant.id.desc())
        .all()
    )
    groups = {"AVAILABLE": [], "USED": [], "EXPIRED": [], "VOID": [], "CLAIMABLE": []}
    for g in rows:
        coupon = db.get(MktCoupon, g.coupon_id)
        item = instance_to_dict(g, coupon)
        st = item["status"]
        if st in groups:
            groups[st].append(item)
        else:
            groups.setdefault(st, []).append(item)
    return {
        "oneid": customer_id,
        "customer_id": customer_id,
        "AVAILABLE": groups["AVAILABLE"],
        "USED": groups["USED"],
        "EXPIRED": groups["EXPIRED"],
        "VOID": groups["VOID"],
        "CLAIMABLE": groups["CLAIMABLE"],
        "summary": {k: len(v) for k, v in groups.items()},
    }


# ---------- 核销 ----------


def calc_discount_amount(coupon: MktCoupon, order_amount: Optional[float], grant: MktCouponGrant) -> float:
    from mkt.coupon_strategy import calc_discount_by_type

    fields = resolve_batch_benefit_fields(coupon)
    ctype = fields["coupon_type"]
    amt = float(order_amount or 0)
    return calc_discount_by_type(ctype, fields, amt)


def redeem_instance(
    db: Session,
    hotel_id: int,
    *,
    code: Optional[str] = None,
    instance_id: Optional[int] = None,
    order_id: Optional[int] = None,
    order_amount: Optional[float] = None,
    cashier: Optional[str] = None,
) -> dict:
    g = None
    raw = (code or "").strip()
    if instance_id:
        g = db.query(MktCouponGrant).filter_by(id=instance_id, hotel_id=hotel_id).first()
    elif raw:
        g = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, code=raw).first()
        if not g:
            g = db.query(MktCouponGrant).filter(MktCouponGrant.code.ilike(raw)).first()
            if g and g.hotel_id != hotel_id:
                g = None
    if not g:
        # 兼容仅 GuestCoupon
        gc = db.query(GuestCoupon).filter_by(hotel_id=hotel_id, code=raw).first() if raw else None
        if not gc and raw:
            gc = db.query(GuestCoupon).filter(GuestCoupon.code.ilike(raw), GuestCoupon.hotel_id == hotel_id).first()
        if not gc:
            raise NotFoundError("券码不存在")
        if gc.redeem_status == "redeemed":
            return {"ok": False, "reason": "已核销", "code": gc.code, "status": "USED"}
        gc.redeem_status = "redeemed"
        gc.status = "used"
        gc.used_at = _now()
        db.commit()
        from events import emit

        emit(
            "coupon.redeemed",
            {
                "hotel_id": hotel_id,
                "code": gc.code,
                "source": "guest_coupon",
                "guest_id": gc.guest_id,
                "order_id": order_id,
            },
        )
        return {"ok": True, "source": "guest_coupon", "code": gc.code, "used_amount": 0, "status": "USED"}

    st = normalize_instance_status(g.status)
    if st == "USED":
        return {
            "ok": False,
            "reason": "已核销",
            "code": g.code,
            "status": "USED",
            "used_at": g.used_at.isoformat() if g.used_at else None,
        }
    if st != "AVAILABLE":
        raise InvalidStateError(f"券状态不可核销：{st}")

    now = _now()
    vf = getattr(g, "valid_from", None)
    vt = getattr(g, "valid_to", None)
    coupon = db.get(MktCoupon, g.coupon_id)
    if not vf and coupon:
        vf = coupon.valid_from
    if not vt and coupon:
        vt = coupon.valid_to
    if vf and now < vf:
        raise InvalidStateError("券尚未生效")
    if vt and now > vt:
        g.status = "EXPIRED"
        db.commit()
        raise InvalidStateError("券已过期")

    if order_id:
        od = db.get(Order, order_id)
        if not od or od.hotel_id != hotel_id:
            raise InvalidStateError("订单无效")
        g.used_order_id = order_id
        if order_amount is None and hasattr(od, "total_amount"):
            try:
                order_amount = float(od.total_amount or 0)
            except Exception:
                pass

    used_amount = 0.0
    if coupon:
        used_amount = calc_discount_amount(coupon, order_amount, g)

    g.status = "USED"
    g.used_at = now
    if hasattr(g, "used_amount"):
        g.used_amount = Decimal(str(used_amount))
    if hasattr(g, "redeemed_by"):
        g.redeemed_by = (cashier or "")[:32] or None

    redeem = MktCouponRedeem(
        instance_id=g.id,
        property_id=hotel_id,
        order_id=order_id,
        amount_saved=used_amount,
        cashier=(cashier or "")[:32] or None,
        redeemed_at=now,
    )
    db.add(redeem)

    gc = db.query(GuestCoupon).filter_by(code=g.code).first()
    if not gc and coupon:
        gc = _project_guest_coupon(db, hotel_id, g.guest_id, coupon, g)
    if gc:
        gc.grant_id = g.id
        gc.source = NATIVE_WALLET_SOURCE
        gc.redeem_status = "redeemed"
        gc.status = "used"
        gc.used_at = now

    db.commit()
    from events import emit

    emit(
        "coupon.redeemed",
        {
            "hotel_id": hotel_id,
            "code": g.code,
            "source": NATIVE_WALLET_SOURCE,
            "instance_id": g.id,
            "guest_id": g.guest_id,
            "order_id": order_id,
            "used_amount": used_amount,
        },
    )
    return {
        "ok": True,
        "source": NATIVE_WALLET_SOURCE,
        "code": g.code,
        "instance_id": g.id,
        "status": "USED",
        "used_amount": used_amount,
        "used_at": now.isoformat(sep=" ", timespec="seconds"),
        "used_order_id": order_id,
        "face_text": getattr(g, "face_text", None) or (coupon and resolve_batch_benefit_fields(coupon)["face_text"]),
        "message": f"已核销本店券「{coupon.name if coupon else g.code}」"
        + (f"，抵扣 ¥{used_amount:g}" if used_amount else ""),
    }


def verify_instance_preview(db: Session, hotel_id: int, code: str) -> dict:
    raw = (code or "").strip()
    fmt_ok = verify_code_format(raw) if raw else False
    g = db.query(MktCouponGrant).filter_by(hotel_id=hotel_id, code=raw).first()
    if not g and raw:
        g = db.query(MktCouponGrant).filter(MktCouponGrant.code.ilike(raw)).first()
        if g and g.hotel_id != hotel_id:
            g = None
    if not g:
        return {"ok": False, "format_ok": fmt_ok, "reason": "券码不存在"}
    expire_due_instances(db, hotel_id, instance_id=g.id)
    db.refresh(g)
    coupon = db.get(MktCoupon, g.coupon_id)
    item = instance_to_dict(g, coupon)
    st = item["status"]
    now = _now()
    vf = getattr(g, "valid_from", None) or (coupon.valid_from if coupon else None)
    vt = getattr(g, "valid_to", None) or (coupon.valid_to if coupon else None)
    in_window = True
    if vf and now < vf:
        in_window = False
    if vt and now > vt:
        in_window = False
    return {
        "ok": st == "AVAILABLE" and in_window,
        "format_ok": fmt_ok or True,  # 旧码无校验位也允许查
        "status": st,
        "in_validity": in_window,
        "instance": item,
    }


# ---------- 过期扫描 ----------


def expire_due_instances(
    db: Session,
    hotel_id: Optional[int] = None,
    *,
    customer_id: Optional[int] = None,
    instance_id: Optional[int] = None,
) -> int:
    now = _now()
    q = db.query(MktCouponGrant).filter(MktCouponGrant.status.in_(("AVAILABLE", "CLAIMABLE", "unused")))
    if hotel_id:
        q = q.filter_by(hotel_id=hotel_id)
    if customer_id:
        q = q.filter_by(guest_id=customer_id)
    if instance_id:
        q = q.filter_by(id=instance_id)
    n = 0
    for g in q.limit(500).all():
        vt = getattr(g, "valid_to", None)
        if not vt:
            coupon = db.get(MktCoupon, g.coupon_id)
            vt = coupon.valid_to if coupon else None
        if vt and now > vt:
            g.status = "EXPIRED"
            n += 1
    if n:
        db.commit()
    return n


# ---------- 事件触发 ----------


def create_trigger(db: Session, hotel_id: int, payload: dict) -> dict:
    from mkt.mkt_auto_grant import upsert_rule

    return upsert_rule(db, hotel_id, payload)


def trigger_to_dict(t: MktCouponTrigger) -> dict:
    import json

    params = {}
    try:
        params = json.loads(t.event_params) if t.event_params else {}
    except Exception:
        params = {}
    return {
        "id": t.id,
        "property_id": t.property_id,
        "batch_id": t.batch_id,
        "event_type": t.event_type,
        "event_params": params,
        "is_enabled": bool(t.is_enabled),
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def fire_event(
    db: Session,
    hotel_id: int,
    event_type: str,
    customer_id: int,
    *,
    event_params: Optional[dict] = None,
    commit: bool = True,
) -> dict:
    """事件总线：匹配 trigger → 发放（auto-claim）。"""
    event_type = str(event_type or "").strip().upper()
    triggers = db.query(MktCouponTrigger).filter_by(property_id=hotel_id, event_type=event_type, is_enabled=1).all()
    import json

    granted = []
    skipped = 0
    for t in triggers:
        coupon = db.get(MktCoupon, t.batch_id)
        if not coupon or coupon.status != "active":
            skipped += 1
            continue
        if t.event_params and event_params:
            try:
                tp = json.loads(t.event_params)
            except Exception:
                tp = {}
            mismatch = False
            for k, v in tp.items():
                if k in event_params and event_params[k] != v:
                    mismatch = True
                    break
            if mismatch:
                skipped += 1
                continue
        try:
            inst = issue_instance(
                db,
                coupon,
                customer_id,
                grant_event=event_type,
                grant_channel="trigger",
                auto_claim=True,
                trigger_id=t.id,
            )
            granted.append(instance_to_dict(inst, coupon))
        except HTTPException:
            skipped += 1
    if commit:
        db.commit()
    return {"event_type": event_type, "granted": len(granted), "skipped": skipped, "instances": granted}


def list_redeem_log(db: Session, hotel_id: int, limit: int = 100) -> list[dict]:
    """核销流水：合并券池实例(MktCouponGrant)与私域券(GuestCoupon)，按核销时间倒序。

    360 前台核销写 GuestCoupon；营销发券核销写 Grant。只读一侧会漏数据。
    """
    by_code: dict[str, dict] = {}

    grants = (
        db.query(MktCouponGrant)
        .filter(
            MktCouponGrant.hotel_id == hotel_id,
            MktCouponGrant.used_at.isnot(None),
        )
        .order_by(MktCouponGrant.used_at.desc())
        .limit(limit)
        .all()
    )
    for g in grants:
        if normalize_instance_status(g.status) != "USED" and not g.used_at:
            continue
        c = db.get(MktCoupon, g.coupon_id)
        guest = db.get(Guest, g.guest_id)
        code = (g.code or f"grant-{g.id}").strip()
        used_amount = None
        if c:
            fields = resolve_batch_benefit_fields(c)
            if fields["coupon_type"] in ("CASH_ROOM", "CASH_ALL"):
                used_amount = float(fields["reduce_amount"] or 0)
        if getattr(g, "used_amount", None) is not None:
            used_amount = float(g.used_amount)
        by_code[code.upper()] = {
            "id": f"g-{g.id}",
            "source": NATIVE_WALLET_SOURCE,
            "wallet_source": NATIVE_WALLET_SOURCE,
            "source_label": "本店私域",
            "instance_id": g.id,
            "coupon_id": g.coupon_id,
            "batch_no": c.batch_no if c else None,
            "coupon_name": c.name if c else None,
            "coupon_code": g.code,
            "discount_label": None,
            "used_amount": used_amount,
            "guest_id": g.guest_id,
            "guest_name": guest.name if guest else None,
            "used_order_id": g.used_order_id,
            "used_at": g.used_at.isoformat(sep=" ", timespec="seconds") if g.used_at else None,
            "status": "USED",
            "channel": g.grant_channel,
        }

    gcs = (
        db.query(GuestCoupon)
        .filter(
            GuestCoupon.hotel_id == hotel_id,
            GuestCoupon.used_at.isnot(None),
        )
        .order_by(GuestCoupon.used_at.desc())
        .limit(limit)
        .all()
    )
    for r in gcs:
        redeem = (r.redeem_status or "").lower()
        st = (r.status or "").lower()
        if redeem not in ("redeemed",) and st not in ("used",) and not r.used_at:
            continue
        guest = db.get(Guest, r.guest_id)
        code = (r.code or f"gc-{r.id}").strip()
        key = code.upper()
        # Grant 已有同码则以 Grant 为准，但补全领券人展示名
        if key in by_code:
            if r.recipient_name and not by_code[key].get("recipient_name"):
                by_code[key]["recipient_name"] = r.recipient_name
            continue
        label = None
        if (r.coupon_type or "") == "room_rate" and r.discount_rate:
            rate = float(r.discount_rate)
            zhe = int(round(rate * 10)) if rate * 10 == int(rate * 10) else round(rate * 10, 1)
            label = f"{zhe}折"
        from mkt.wallet_norm import WALLET_SOURCE_LABEL, normalize_wallet_source

        ws = normalize_wallet_source(r.source)
        by_code[key] = {
            "id": f"gc-{r.id}",
            "source": ws,
            "wallet_source": ws,
            "source_label": WALLET_SOURCE_LABEL.get(ws, ws),
            "instance_id": getattr(r, "grant_id", None),
            "coupon_id": None,
            "batch_no": None,
            "coupon_name": r.name,
            "coupon_code": r.code,
            "discount_label": label,
            "used_amount": None,
            "guest_id": r.guest_id,
            "guest_name": guest.name if guest else r.recipient_name,
            "recipient_name": r.recipient_name,
            "used_order_id": None,
            "used_at": r.used_at.isoformat(sep=" ", timespec="seconds") if r.used_at else None,
            "status": "USED",
            "channel": r.channel or WALLET_SOURCE_LABEL.get(ws, "其他"),
        }

    # 兼容旧 MktCouponRedeem 表（若有）
    try:
        rows = (
            db.query(MktCouponRedeem)
            .filter_by(property_id=hotel_id)
            .order_by(MktCouponRedeem.id.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            inst = db.get(MktCouponGrant, r.instance_id)
            code = (inst.code if inst else None) or f"redeem-{r.id}"
            key = code.upper()
            if key in by_code:
                if by_code[key].get("used_amount") is None and r.amount_saved is not None:
                    by_code[key]["used_amount"] = float(r.amount_saved or 0)
                continue
            guest = db.get(Guest, inst.guest_id) if inst else None
            c = db.get(MktCoupon, inst.coupon_id) if inst else None
            by_code[key] = {
                "id": f"r-{r.id}",
                "source": NATIVE_WALLET_SOURCE,
                "wallet_source": NATIVE_WALLET_SOURCE,
                "source_label": "本店私域",
                "instance_id": r.instance_id,
                "coupon_id": inst.coupon_id if inst else None,
                "batch_no": c.batch_no if c else None,
                "coupon_name": c.name if c else None,
                "coupon_code": inst.code if inst else None,
                "discount_label": None,
                "used_amount": float(r.amount_saved or 0),
                "guest_id": inst.guest_id if inst else None,
                "guest_name": guest.name if guest else None,
                "used_order_id": r.order_id,
                "used_at": r.redeemed_at.isoformat(sep=" ", timespec="seconds") if r.redeemed_at else None,
                "status": "USED",
                "cashier": r.cashier,
            }
    except Exception:
        pass

    out = list(by_code.values())
    out.sort(key=lambda x: x.get("used_at") or "", reverse=True)
    return out[:limit]
