# SPDX-License-Identifier: Apache-2.0
"""财务参数 · 门店备用金底数（定额备用金制 + 双授权审批）。"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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
from models import FinanceFloatCarry, FinanceReport, User

# 复核制度：角色 + 二次密码（§4.7 身份复核）
FINANCE_PARAM_EDIT_ROLES = frozenset({"admin", "gm", "fin", "mgr"})
FINANCE_REVIEW_ROLES = frozenset({"admin", "gm", "fin", "mgr"})
MANAGER_REVIEW_ROLES = frozenset({"admin", "gm", "mgr"})

DEFAULT_DENOM_RATIOS = [
    {"denom": 100, "ratio": 0.50, "label": "100 元"},
    {"denom": 50, "ratio": 0.25, "label": "50 元"},
    {"denom": 20, "ratio": 0.15, "label": "20 元"},
    {"denom": 10, "ratio": 0.05, "label": "10 元"},
    {"denom": 5, "ratio": 0.03, "label": "5 元"},
    {"denom": 1, "ratio": 0.02, "label": "1 元（硬币）"},
]


def _normalize_denom_ratios(ratios: list[dict]) -> list[dict]:
    """面额标准：仅保留元级（100/50/20/10/5/1），散角不数。"""
    out = []
    for item in ratios or []:
        denom = float(item.get("denom") or 0)
        if denom < 1:
            continue
        out.append(
            {
                "denom": denom,
                "ratio": float(item.get("ratio") or 0),
                "label": item.get("label") or (f"{int(denom)} 元" if denom >= 1 else str(denom)),
            }
        )
    return out or list(DEFAULT_DENOM_RATIOS)


def _user_label(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    u = db.get(User, user_id)
    if not u:
        return None
    return u.full_name or u.username


def _parse_ratios(raw: str | None) -> list[dict]:
    if not raw:
        return list(DEFAULT_DENOM_RATIOS)
    try:
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return _normalize_denom_ratios(data)
    except json.JSONDecodeError:
        pass
    return list(DEFAULT_DENOM_RATIOS)


def suggest_denom_breakdown(amount: float, ratios: list[dict] | None = None) -> list[dict]:
    """按配比建议各面额数量（清点辅助，非实盘）。"""
    from infra.i18n import t

    ratios = ratios or DEFAULT_DENOM_RATIOS
    out = []
    for item in ratios:
        denom = float(item.get("denom") or 0)
        ratio = float(item.get("ratio") or 0)
        raw_label = item.get("label") or (f"{int(denom)} 元" if denom >= 1 else str(denom))
        label = t(str(raw_label))
        if denom <= 0:
            continue
        qty = int(round(amount * ratio / denom)) if amount > 0 else 0
        out.append({"denom": denom, "label": label, "expected_qty": qty, "ratio": ratio})
    return out


def get_active_float_carry(db: Session, hotel_id: int) -> FinanceFloatCarry | None:
    return (
        db.query(FinanceFloatCarry)
        .filter_by(hotel_id=hotel_id, status="active")
        .order_by(FinanceFloatCarry.id.desc())
        .first()
    )


def get_active_float_carry_amount(db: Session, hotel_id: int) -> float:
    row = get_active_float_carry(db, hotel_id)
    return float(row.amount) if row and row.amount is not None else 0.0


def get_active_denom_ratios(db: Session, hotel_id: int) -> list[dict]:
    row = get_active_float_carry(db, hotel_id)
    return _parse_ratios(row.denom_ratios if row else None)


def _sync_finance_report(db: Session, hotel_id: int, amount: float) -> None:
    db.add(
        FinanceReport(
            hotel_id=hotel_id,
            metric="float_carry",
            period=date.today().strftime("%Y-%m-%d"),
            value=amount,
        )
    )


def _row_to_dict(db: Session, row: FinanceFloatCarry) -> dict[str, Any]:
    applicant = _user_label(db, row.applicant_user_id)
    finance_appr = _user_label(db, row.finance_approver_user_id)
    manager_appr = _user_label(db, row.manager_approver_user_id)
    rejected_by = _user_label(db, row.rejected_by_user_id)
    approvers = []
    if finance_appr:
        approvers.append(finance_appr)
    if manager_appr:
        approvers.append(manager_appr)
    return {
        "id": row.id,
        "hotel_id": row.hotel_id,
        "amount": float(row.amount or 0),
        "currency": row.currency or "CNY",
        "effective_date": row.effective_date.isoformat() if row.effective_date else None,
        "change_reason": row.change_reason or "",
        "old_amount": float(row.old_amount) if row.old_amount is not None else None,
        "status": row.status,
        "applicant_name": applicant,
        "finance_approver_name": finance_appr,
        "manager_approver_name": manager_appr,
        "approver_names": " / ".join(approvers) if approvers else "—",
        "rejected_by_name": rejected_by,
        "reject_reason": row.reject_reason or "",
        "created_at": row.created_at.isoformat(timespec="minutes") if row.created_at else None,
        "activated_at": row.activated_at.isoformat(timespec="minutes") if row.activated_at else None,
        "finance_approved_at": row.finance_approved_at.isoformat(timespec="minutes")
        if row.finance_approved_at
        else None,
        "manager_approved_at": row.manager_approved_at.isoformat(timespec="minutes")
        if row.manager_approved_at
        else None,
        "denom_breakdown": suggest_denom_breakdown(float(row.amount or 0), _parse_ratios(row.denom_ratios)),
    }


def get_float_carry_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    active = get_active_float_carry(db, hotel_id)
    pending = (
        db.query(FinanceFloatCarry)
        .filter(
            FinanceFloatCarry.hotel_id == hotel_id,
            FinanceFloatCarry.status.in_(("pending_finance", "pending_manager")),
        )
        .order_by(FinanceFloatCarry.id.desc())
        .first()
    )
    history = (
        db.query(FinanceFloatCarry)
        .filter(
            FinanceFloatCarry.hotel_id == hotel_id,
            FinanceFloatCarry.status.in_(("active", "superseded", "rejected")),
        )
        .order_by(FinanceFloatCarry.id.desc())
        .limit(20)
        .all()
    )
    if active:
        history = [h for h in history if h.id != active.id or h.status != "active"]
    change_count = (
        db.query(FinanceFloatCarry)
        .filter(
            FinanceFloatCarry.hotel_id == hotel_id,
            FinanceFloatCarry.status.in_(("active", "superseded")),
            FinanceFloatCarry.old_amount.isnot(None),
        )
        .count()
    )
    maintainer = None
    maintainer_at = None
    if active:
        maintainer = _user_label(db, active.applicant_user_id) or _user_label(db, active.manager_approver_user_id)
        maintainer_at = active.activated_at or active.created_at
    return {
        "active": _row_to_dict(db, active) if active else None,
        "pending": _row_to_dict(db, pending) if pending else None,
        "history": [_row_to_dict(db, h) for h in history],
        "change_count_8m": change_count,
        "maintainer_name": maintainer,
        "maintainer_at": maintainer_at.isoformat(timespec="minutes") if maintainer_at else None,
        "default_ratios": DEFAULT_DENOM_RATIOS,
        "currency_label": "人民币（CNY）",
        "review_required": True,
    }


def _require_role(role: str, allowed: frozenset[str], action: str) -> None:
    code = (role or "").lower()
    if code not in allowed:
        raise AuthorizationError(f"{action}需要以下角色之一：{', '.join(sorted(allowed))}")


def _verify_review(db: Session, ctx, password: str, action: str) -> None:
    from infra.compliance import verify_secondary_password

    verify_secondary_password(db, ctx, password or "")


def submit_float_carry_change(
    db: Session,
    hotel_id: int,
    amount: float,
    reason: str,
    ctx,
    denom_ratios: list[dict] | None = None,
    review_password: str = "",
) -> dict[str, Any]:
    _require_role(ctx.role, FINANCE_PARAM_EDIT_ROLES, "提交备用金变更")
    _verify_review(db, ctx, review_password, "提交")
    applicant_user_id = ctx.user_id
    if amount <= 0:
        raise InvalidStateError("备用金本金须大于 0")
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    active = get_active_float_carry(db, hotel_id)
    old_amount = float(active.amount) if active else 0.0
    if active and abs(amount - old_amount) < 0.01:
        raise InvalidStateError("新本金与当前生效值相同，无需变更")
    existing_pending = (
        db.query(FinanceFloatCarry)
        .filter(
            FinanceFloatCarry.hotel_id == hotel_id,
            FinanceFloatCarry.status.in_(("pending_finance", "pending_manager")),
        )
        .first()
    )
    if existing_pending:
        raise InvalidStateError("已有在途审批，请先处理后再提交")
    ratios = denom_ratios or DEFAULT_DENOM_RATIOS
    row = FinanceFloatCarry(
        hotel_id=hotel_id,
        amount=Decimal(str(round(amount, 2))),
        currency="CNY",
        denom_ratios=json.dumps(ratios, ensure_ascii=False),
        effective_date=date.today(),
        change_reason=reason,
        old_amount=Decimal(str(round(old_amount, 2))) if active else None,
        status="pending_finance",
        applicant_user_id=applicant_user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(db, row)


def approve_float_carry_finance(
    db: Session,
    hotel_id: int,
    request_id: int,
    ctx,
    review_password: str = "",
) -> dict[str, Any]:
    _require_role(ctx.role, FINANCE_REVIEW_ROLES, "财务复核")
    _verify_review(db, ctx, review_password, "财务复核")
    row = db.get(FinanceFloatCarry, request_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("变更申请不存在")
    if row.status != "pending_finance":
        raise InvalidStateError("当前状态不可进行财务经理审批")
    if row.applicant_user_id and row.applicant_user_id == ctx.user_id:
        raise AuthorizationError("申请人不能复核自己的变更申请")
    row.status = "pending_manager"
    row.finance_approver_user_id = ctx.user_id
    row.finance_approved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _row_to_dict(db, row)


def approve_float_carry_manager(
    db: Session,
    hotel_id: int,
    request_id: int,
    ctx,
    review_password: str = "",
) -> dict[str, Any]:
    _require_role(ctx.role, MANAGER_REVIEW_ROLES, "店长复核")
    _verify_review(db, ctx, review_password, "店长复核")
    row = db.get(FinanceFloatCarry, request_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("变更申请不存在")
    if row.status != "pending_manager":
        raise InvalidStateError("当前状态不可进行店长审批")
    if row.applicant_user_id and row.applicant_user_id == ctx.user_id:
        raise AuthorizationError("申请人不能复核自己的变更申请")
    if row.finance_approver_user_id and row.finance_approver_user_id == ctx.user_id:
        raise AuthorizationError("财务复核人与店长复核须为不同操作员")
    active = get_active_float_carry(db, hotel_id)
    if active:
        active.status = "superseded"
    now = datetime.now()
    row.status = "active"
    row.manager_approver_user_id = ctx.user_id
    row.manager_approved_at = now
    row.activated_at = now
    row.effective_date = date.today()
    _sync_finance_report(db, hotel_id, float(row.amount))
    db.commit()
    db.refresh(row)
    return _row_to_dict(db, row)


def reject_float_carry_change(
    db: Session,
    hotel_id: int,
    request_id: int,
    ctx,
    reject_reason: str = "",
    review_password: str = "",
) -> dict[str, Any]:
    _require_role(ctx.role, FINANCE_REVIEW_ROLES | MANAGER_REVIEW_ROLES, "驳回")
    _verify_review(db, ctx, review_password, "驳回")
    row = db.get(FinanceFloatCarry, request_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("变更申请不存在")
    if row.status not in ("pending_finance", "pending_manager"):
        raise InvalidStateError("当前状态不可驳回")
    row.status = "rejected"
    row.rejected_by_user_id = ctx.user_id
    row.rejected_at = datetime.now()
    row.reject_reason = (reject_reason or "审批驳回").strip()
    db.commit()
    db.refresh(row)
    return _row_to_dict(db, row)
