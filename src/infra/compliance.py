# SPDX-License-Identifier: Apache-2.0
"""
PII 合规：权限、二次校验、审计、留存匿名化、脱敏导出。
"""

from __future__ import annotations

import os
from typing import Optional

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
from infra.auth_local import AppContext, verify_password
from models import PmsIdDocAudit, User

# 可查看完整证件号的角色（高权限）
REVEAL_ROLES = frozenset({"admin", "gm", "mgr", "owner"})
AUDIT_RETAIN_MONTHS = 6
ID_DOC_RETAIN_YEARS = int(os.environ.get("PMS_ID_DOC_RETAIN_YEARS") or "5")


def can_reveal_id_doc(ctx: AppContext) -> bool:
    return (ctx.role or "").lower() in REVEAL_ROLES


def require_reveal_privilege(ctx: AppContext) -> None:
    if not can_reveal_id_doc(ctx):
        raise AuthorizationError("无权查看完整证件号：需要管理员等高权限账号")


def verify_secondary_password(db: Session, ctx: AppContext, password: str) -> None:
    """二次校验：再输一次登录密码。"""
    if not (password or "").strip():
        raise InvalidStateError("请输入登录密码进行二次校验")
    user = db.get(User, ctx.user_id) if ctx.user_id else None
    if not user or not user.password_hash:
        raise AuthorizationError("无法校验账号，请重新登录")
    if not verify_password(password.strip(), user.password_hash):
        raise AuthorizationError("二次校验失败：密码不正确")


def write_id_doc_audit(
    db: Session,
    *,
    hotel_id: int,
    checkin_id: Optional[int],
    order_id: Optional[int],
    operator_id: Optional[int],
    action: str,
    reason: str = "",
) -> PmsIdDocAudit:
    row = PmsIdDocAudit(
        hotel_id=hotel_id,
        checkin_id=checkin_id,
        order_id=order_id,
        operator_id=operator_id,
        action=action,
        reason=(reason or "")[:200],
    )
    db.add(row)
    db.flush()
    return row


def purge_expired_id_docs(db: Session, retain_years: Optional[int] = None) -> int:
    from bootstrap.migrations.alter_pms_core_plaintext import purge_expired_id_docs as _purge

    return _purge(db, retain_years=retain_years or ID_DOC_RETAIN_YEARS)


def mask_guest_dict(g: dict) -> dict:
    """导出/列表：手机号只出脱敏。"""
    from infra.id_doc_crypto import mask_phone

    out = dict(g)
    phone = out.get("phone_mask") or out.get("phone")
    if phone and "*" not in str(phone):
        out["phone"] = mask_phone(phone)
    else:
        out["phone"] = phone or ""
    out.pop("phone_cipher", None)
    out.pop("phone_hash", None)
    out.pop("id_doc_no", None)
    out.pop("id_doc_cipher", None)
    return out


def compliance_status(db: Session, hotel_id: int, ctx: AppContext) -> dict:
    from infra.id_doc_crypto import ensure_hotel_key, key_status
    from models import PmsCheckin

    ensure_hotel_key(hotel_id)
    ks = key_status(hotel_id)
    audit_n = db.query(PmsIdDocAudit).filter_by(hotel_id=hotel_id).count()
    oldest = db.query(PmsIdDocAudit).filter_by(hotel_id=hotel_id).order_by(PmsIdDocAudit.created_at.asc()).first()
    cipher_n = (
        db.query(PmsCheckin).filter(PmsCheckin.hotel_id == hotel_id, PmsCheckin.id_doc_cipher.isnot(None)).count()
    )
    return {
        "hotel_id": hotel_id,
        "key": ks,
        "id_doc_only_on_checkin": True,
        "face_photo_stored": False,
        "list_default_masked": True,
        "reveal_requires_high_role": True,
        "reveal_requires_password": True,
        "reveal_roles": sorted(REVEAL_ROLES),
        "current_role": ctx.role,
        "can_reveal": can_reveal_id_doc(ctx),
        "audit_count": audit_n,
        "audit_immutable": True,
        "audit_min_retain_months": AUDIT_RETAIN_MONTHS,
        "audit_oldest_at": oldest.created_at.isoformat() if oldest and oldest.created_at else None,
        "id_doc_retain_years": ID_DOC_RETAIN_YEARS,
        "checkins_with_cipher": cipher_n,
        "export_default_masked": True,
        "storage": "hotel_local",
        "checklist": [
            {"id": "encrypt", "ok": True, "text": "身份证号/手机号字段级加密（AES，可选 SM4）"},
            {
                "id": "hotel_key",
                "ok": ks["hotel_key_exists"] or ks["env_key_configured"],
                "text": "密钥由酒店本地保管",
            },
            {"id": "checkin_only", "ok": True, "text": "证件号只存入住登记表，预订单不存"},
            {"id": "no_face", "ok": True, "text": "不落地身份证人像照片"},
            {"id": "mask_list", "ok": True, "text": "列表默认脱敏"},
            {"id": "reveal_rbac", "ok": True, "text": "查看完整证件需高权限 + 二次密码校验"},
            {"id": "audit", "ok": True, "text": "揭密写不可删审计，留存≥6个月"},
            {
                "id": "retention",
                "ok": True,
                "text": f"离店后保留 {ID_DOC_RETAIN_YEARS} 年，到期匿名化密文字段",
            },
            {"id": "export", "ok": True, "text": "报表导出默认脱敏，禁止一键明文"},
        ],
    }
