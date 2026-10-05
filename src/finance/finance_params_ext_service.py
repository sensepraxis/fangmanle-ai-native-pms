# SPDX-License-Identifier: Apache-2.0
"""财务参数扩展：税率账期 / 收单费率 / 信用账龄。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
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
from models import (
    FinanceAcquiringChannel,
    FinanceBadDebtRate,
    FinanceCreditCustomer,
    FinanceParamAudit,
    FinancePaymentTerm,
    FinanceTaxConfig,
    User,
)


def _f(v: Any) -> float:
    return round(float(v or 0), 4)


def _money(v: Any) -> float:
    return round(float(v or 0), 2)


def _user_name(db: Session, user_id: int | None) -> str:
    if not user_id:
        return "—"
    u = db.get(User, user_id)
    return (u.full_name or u.username) if u else "—"


def _resolve_effective(mode: str, specified: str | None = None) -> date:
    today = date.today()
    if mode == "立即生效":
        return today
    if mode == "次日 0 时":
        return today + timedelta(days=1)
    if mode == "次月 1 日" or mode == "次月 1 日（推荐）":
        if today.month == 12:
            return date(today.year + 1, 1, 1)
        return date(today.year, today.month + 1, 1)
    if mode == "指定日期" and specified:
        return date.fromisoformat(specified)
    return today


def _audit(
    db: Session,
    hotel_id: int,
    domain: str,
    action_type: str,
    target: str,
    change_text: str,
    reason: str,
    actor: str,
    status: str = "已生效",
    effective_date: date | None = None,
) -> None:
    db.add(
        FinanceParamAudit(
            hotel_id=hotel_id,
            domain=domain,
            action_type=action_type,
            target=target,
            change_text=change_text,
            reason=reason,
            effective_date=effective_date,
            actor_names=actor,
            status=status,
        )
    )


# ---------- 税率与账期 ----------


def get_tax_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    tax = (
        db.query(FinanceTaxConfig)
        .filter_by(hotel_id=hotel_id, status="active")
        .order_by(FinanceTaxConfig.id.desc())
        .first()
    )
    terms = (
        db.query(FinancePaymentTerm)
        .filter_by(hotel_id=hotel_id)
        .order_by(FinancePaymentTerm.sort_order.asc(), FinancePaymentTerm.id.asc())
        .all()
    )
    history = (
        db.query(FinanceParamAudit)
        .filter_by(hotel_id=hotel_id, domain="tax")
        .order_by(FinanceParamAudit.id.desc())
        .limit(30)
        .all()
    )
    rate_pct = round(_f(tax.main_rate) * 100, 2) if tax else 6.0
    from infra.i18n import t as _t

    return {
        "tax": {
            "id": tax.id if tax else None,
            "version": tax.version if tax else 1,
            "taxpayer_type": _t(tax.taxpayer_type if tax else "一般纳税人"),
            "main_rate": rate_pct,
            "price_mode": _t(tax.price_mode if tax else "价外"),
            "tax_code": tax.tax_code if tax else "3070401000000000000",
            "tax_no": tax.tax_no if tax else "",
            "surcharge_note": _t(tax.surcharge_note if tax else "城建 7% / 教育 3% / 地方教育 2%"),
            "effective_date": tax.effective_date.isoformat() if tax and tax.effective_date else None,
            "maintainer_name": _t(tax.maintainer_name) if tax and tax.maintainer_name else None,
            "future_version": None,
        },
        "terms": [
            {
                "id": term.id,
                "customer_type": _t(term.customer_type or ""),
                "term_label": _t(term.term_label or ""),
                "description": _t(term.description or "") if term.description else "",
                "effective_date": term.effective_date.isoformat() if term.effective_date else None,
            }
            for term in terms
        ],
        "history": [
            {
                "id": h.id,
                "time": h.created_at.isoformat(timespec="minutes") if h.created_at else None,
                "type": _t(h.action_type or "") if h.action_type else None,
                "change": _t(h.change_text or "") if h.change_text else None,
                "effective_date": h.effective_date.isoformat() if h.effective_date else None,
                "who": _t(h.actor_names or "") if h.actor_names else None,
                "status": _t(h.status or "") if h.status else None,
            }
            for h in history
        ],
    }


def update_tax_config(
    db: Session,
    hotel_id: int,
    *,
    taxpayer_type: str,
    main_rate_pct: float,
    price_mode: str,
    effective_mode: str,
    reason: str,
    specified_date: str | None = None,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    if main_rate_pct <= 0 or main_rate_pct > 100:
        raise InvalidStateError("税率无效")
    active = (
        db.query(FinanceTaxConfig)
        .filter_by(hotel_id=hotel_id, status="active")
        .order_by(FinanceTaxConfig.id.desc())
        .first()
    )
    old_rate = round(_f(active.main_rate) * 100, 2) if active else 0
    old_ver = active.version if active else 0
    if active:
        active.status = "superseded"
    eff = _resolve_effective(effective_mode, specified_date)
    row = FinanceTaxConfig(
        hotel_id=hotel_id,
        version=old_ver + 1,
        taxpayer_type=taxpayer_type or "一般纳税人",
        main_rate=Decimal(str(round(main_rate_pct / 100, 4))),
        price_mode=price_mode or "价外",
        tax_code=active.tax_code if active else "3070401000000000000",
        tax_no=active.tax_no if active else "",
        surcharge_note=active.surcharge_note if active else "城建 7% / 教育 3% / 地方教育 2%",
        effective_date=eff,
        status="active",
        change_reason=reason,
        maintainer_name=_user_name(db, operator_id),
    )
    db.add(row)
    _audit(
        db,
        hotel_id,
        "tax",
        "税率",
        "主营税率",
        f"主营税率 {old_rate}% → {main_rate_pct}%（v{old_ver + 1}）",
        reason,
        _user_name(db, operator_id),
        effective_date=eff,
    )
    db.commit()
    return get_tax_workspace(db, hotel_id)


def update_payment_term(
    db: Session,
    hotel_id: int,
    term_id: int,
    *,
    term_label: str,
    effective_mode: str,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    row = db.get(FinancePaymentTerm, term_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("账期配置不存在")
    old = row.term_label
    row.term_label = term_label
    row.effective_date = _resolve_effective(effective_mode)
    _audit(
        db,
        hotel_id,
        "tax",
        "账期",
        row.customer_type,
        f"{row.customer_type}：{old} → {term_label}",
        reason,
        _user_name(db, operator_id),
        effective_date=row.effective_date,
    )
    db.commit()
    return get_tax_workspace(db, hotel_id)


# ---------- 收单费率 ----------


def get_acquiring_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    channels = (
        db.query(FinanceAcquiringChannel)
        .filter_by(hotel_id=hotel_id)
        .order_by(FinanceAcquiringChannel.sort_order.asc())
        .all()
    )
    enabled = [c for c in channels if c.enabled and c.rate_pct is not None]
    online = [c for c in enabled if (c.status_label or "") in ("上线", "Live") or (not c.status_label and c.enabled)]
    total_fee = sum(_money(c.month_fee) for c in enabled)
    total_gmv = sum(_money(c.month_gmv) for c in enabled) or 1
    weighted = sum(_f(c.rate_pct) * _money(c.month_gmv) for c in enabled) / total_gmv if enabled else 0
    t1 = sum(1 for c in online if (c.settle_label or "").startswith("T+1"))
    history = (
        db.query(FinanceParamAudit)
        .filter_by(hotel_id=hotel_id, domain="acquiring")
        .order_by(FinanceParamAudit.id.desc())
        .limit(30)
        .all()
    )
    from infra.i18n import t as _t

    return {
        "kpi": {
            "active_channels": len(online),
            "weighted_rate": round(weighted, 2),
            "month_fee": round(total_fee, 2),
            "t1_ok": f"{t1}/{len(online)}" if online else "0/0",
            "fee_of_revenue_pct": round(total_fee / total_gmv * 100, 2) if total_gmv else 0,
        },
        "channels": [
            {
                "id": c.id,
                "code": c.channel_code,
                "name": _t(c.channel_name or ""),
                "rate_pct": _f(c.rate_pct) if c.rate_pct is not None else None,
                "rate_cap": _money(c.rate_cap) if c.rate_cap is not None else None,
                "rate_display": (
                    f"{_f(c.rate_pct):.2f}% {_t('封顶')} ¥{_money(c.rate_cap):.0f}"
                    if c.rate_pct is not None and c.rate_cap
                    else (f"{_f(c.rate_pct):.2f}%" if c.rate_pct is not None else "—")
                ),
                "settle_label": c.settle_label or "—",
                "min_settle": _money(c.min_settle) if c.min_settle is not None else None,
                "withdraw_fee_pct": _f(c.withdraw_fee_pct) if c.withdraw_fee_pct is not None else None,
                "month_fee": _money(c.month_fee),
                "month_gmv": _money(c.month_gmv),
                "enabled": bool(c.enabled),
                "status_label": _t(c.status_label or ("上线" if c.enabled else "未启用")),
            }
            for c in channels
        ],
        "history": [
            {
                "id": h.id,
                "time": h.created_at.isoformat(timespec="minutes") if h.created_at else None,
                "channel": _t(h.target or "") if h.target else None,
                "action": _t(h.action_type or "") if h.action_type else None,
                "change": h.change_text,
                "reason": _t(h.reason or "") if h.reason else None,
                "who": _t(h.actor_names or "") if h.actor_names else None,
                "status": _t(h.status or "") if h.status else None,
            }
            for h in history
        ],
    }


def update_acquiring_rate(
    db: Session,
    hotel_id: int,
    channel_id: int,
    *,
    rate_pct: float,
    effective_mode: str,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    if rate_pct < 0 or rate_pct > 10:
        raise InvalidStateError("费率无效")
    row = db.get(FinanceAcquiringChannel, channel_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("渠道不存在")
    old = _f(row.rate_pct) if row.rate_pct is not None else 0
    row.rate_pct = Decimal(str(round(rate_pct, 4)))
    if not row.enabled:
        row.enabled = True
        row.status_label = "上线"
    impact = (rate_pct - old) / 100 * _money(row.month_gmv)
    _audit(
        db,
        hotel_id,
        "acquiring",
        "费率调整",
        row.channel_name,
        f"{old:.2f}% → {rate_pct:.2f}%（预计月影响 {impact:+.2f}）",
        reason,
        _user_name(db, operator_id),
        effective_date=_resolve_effective(effective_mode),
    )
    db.commit()
    return get_acquiring_workspace(db, hotel_id)


def toggle_acquiring_channel(
    db: Session,
    hotel_id: int,
    channel_id: int,
    *,
    enabled: bool,
    operator_id: int | None = None,
) -> dict:
    row = db.get(FinanceAcquiringChannel, channel_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("渠道不存在")
    if row.rate_pct is None and enabled:
        raise InvalidStateError("未配置费率的渠道请先申请开通")
    old = "上线" if row.enabled else "未启用"
    row.enabled = enabled
    row.status_label = "上线" if enabled else "未启用"
    _audit(
        db,
        hotel_id,
        "acquiring",
        "上线" if enabled else "下线",
        row.channel_name,
        f"{old} → {row.status_label}",
        "渠道开关",
        _user_name(db, operator_id),
    )
    db.commit()
    return get_acquiring_workspace(db, hotel_id)


# ---------- 信用与账龄 ----------


def get_credit_workspace(db: Session, hotel_id: int) -> dict[str, Any]:
    customers = (
        db.query(FinanceCreditCustomer)
        .filter_by(hotel_id=hotel_id)
        .order_by(FinanceCreditCustomer.sort_order.asc())
        .all()
    )
    rates = (
        db.query(FinanceBadDebtRate).filter_by(hotel_id=hotel_id).order_by(FinanceBadDebtRate.sort_order.asc()).all()
    )
    history = (
        db.query(FinanceParamAudit)
        .filter_by(hotel_id=hotel_id, domain="credit")
        .order_by(FinanceParamAudit.id.desc())
        .limit(30)
        .all()
    )
    active = [c for c in customers if c.enabled]
    total_limit = sum(_money(c.credit_limit) for c in customers)
    total_used = sum(_money(c.credit_used) for c in active)
    remain = total_limit - total_used
    usage = round(100 * total_used / total_limit, 1) if total_limit else 0
    grade_cnt = {"A": 0, "B": 0, "C": 0, "D": 0}
    for c in customers:
        g = (c.grade or "B").upper()[:1]
        if g in grade_cnt:
            grade_cnt[g] += 1

    # 90+ / 账龄分桶：与应收应付中心同源（ArInvoice 未结余额）
    from finance.ar_ap_service import list_workspace as list_ar_ap_workspace

    ar_ws = list_ar_ap_workspace(db, hotel_id)
    ar_kpi = ar_ws.get("kpi") or {}
    aging = ar_ws.get("aging") or {}
    ar_balance = _money(ar_kpi.get("ar_balance"))
    overdue_90_amt = _money(aging.get("d90_plus") or ar_kpi.get("ar_aging_90_plus"))
    overdue_90_pct = round(100 * overdue_90_amt / ar_balance, 1) if ar_balance > 0 else 0.0

    def _age_hint(amt: float, tone_text: str) -> str:
        from infra.i18n import t as _t

        return f"¥{_money(amt):,.0f} · {_t(tone_text)}"

    items = []
    for c in customers:
        lim = _money(c.credit_limit)
        used = _money(c.credit_used)
        rem = lim - used
        pct = round(100 * used / lim, 1) if lim > 0 else 0
        from infra.i18n import t as _t

        items.append(
            {
                "id": c.id,
                "name": _t(c.name or "") if c.name else "",
                "customer_type": _t(c.customer_type or "") if c.customer_type else "",
                "grade": c.grade,
                "credit_limit": lim,
                "credit_used": used,
                "credit_remain": rem,
                "usage_pct": pct,
                "term_label": _t(c.term_label or "") if c.term_label else "",
                "rated_at": c.rated_at.isoformat() if c.rated_at else None,
                "status_label": _t(c.status_label or "") if c.status_label else "",
                "enabled": bool(c.enabled),
            }
        )
    from infra.i18n import t as _t

    return {
        "kpi": {
            "customer_count": len(customers),
            "grade_breakdown": f"A {grade_cnt['A']} / B {grade_cnt['B']} / C {grade_cnt['C']} / D {grade_cnt['D']}",
            "total_limit": total_limit,
            "remain": remain,
            "usage_pct": usage,
            "overdue_90_pct": overdue_90_pct,
            "overdue_90_amt": overdue_90_amt,
            "ar_balance": ar_balance,
        },
        "customers": items,
        "aging_buckets": [
            {
                "key": "0-30",
                "label": _t("0–30 天"),
                "tone": "ok",
                "hint": _age_hint(_money(aging.get("d0_30")), "正常"),
                "amount": _money(aging.get("d0_30")),
            },
            {
                "key": "30-60",
                "label": _t("30–60 天"),
                "tone": "warn",
                "hint": _age_hint(_money(aging.get("d30_60")), "提醒"),
                "amount": _money(aging.get("d30_60")),
            },
            {
                "key": "60-90",
                "label": _t("60–90 天"),
                "tone": "warn",
                "hint": _age_hint(_money(aging.get("d60_90")), "催收"),
                "amount": _money(aging.get("d60_90")),
            },
            {
                "key": "90+",
                "label": _t("90+ 天"),
                "tone": "bad",
                "hint": _age_hint(overdue_90_amt, "坏账风险"),
                "amount": overdue_90_amt,
            },
        ],
        "bad_debt_rates": [
            {
                "id": r.id,
                "bucket": r.bucket,
                "bucket_label": _t(r.bucket_label or ""),
                "rate_pct": _f(r.rate_pct),
                "description": _t(r.description or "") if r.description else "",
            }
            for r in rates
        ],
        "history": [
            {
                "id": h.id,
                "time": h.created_at.isoformat(timespec="minutes") if h.created_at else None,
                "type": h.action_type,
                "target": h.target,
                "change": h.change_text,
                "reason": h.reason,
                "who": h.actor_names,
                "status": h.status,
            }
            for h in history
        ],
    }


def create_credit_customer(
    db: Session,
    hotel_id: int,
    *,
    name: str,
    customer_type: str,
    grade: str,
    credit_limit: float,
    term_label: str,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    """新增已准入的授信客户（本页不走客户准入，只维护额度）。"""
    name = (name or "").strip()
    reason = (reason or "").strip()
    customer_type = (customer_type or "").strip() or "企业挂账"
    grade = ((grade or "B").strip().upper()[:1]) or "B"
    term_label = (term_label or "").strip() or "30 天"
    if len(name) < 2:
        raise InvalidStateError("客户名称不少于 2 字")
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    if credit_limit < 0:
        raise InvalidStateError("额度不能为负")
    if grade not in ("A", "B", "C", "D"):
        raise InvalidStateError("信用等级无效")
    exists = db.query(FinanceCreditCustomer).filter_by(hotel_id=hotel_id, name=name).first()
    if exists:
        raise InvalidStateError(f"客户「{name}」已存在")
    max_sort = db.query(FinanceCreditCustomer).filter_by(hotel_id=hotel_id).count()
    row = FinanceCreditCustomer(
        hotel_id=hotel_id,
        name=name,
        customer_type=customer_type,
        grade=grade,
        credit_limit=Decimal(str(round(credit_limit, 2))),
        credit_used=Decimal("0"),
        term_label=term_label,
        rated_at=date.today(),
        status_label="正常" if credit_limit > 0 else "停用挂账",
        enabled=credit_limit > 0,
        sort_order=max_sort + 1,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        hotel_id,
        "credit",
        "新增",
        name,
        f"— → ¥{credit_limit:,.0f}",
        reason,
        _user_name(db, operator_id),
    )
    db.commit()
    return get_credit_workspace(db, hotel_id)


def update_credit_limit(
    db: Session,
    hotel_id: int,
    customer_id: int,
    *,
    new_limit: float,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    if new_limit < 0:
        raise InvalidStateError("额度不能为负")
    row = db.get(FinanceCreditCustomer, customer_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("授信客户不存在")
    old = _money(row.credit_limit)
    used = _money(row.credit_used)
    if new_limit < used:
        raise InvalidStateError(f"新额度不能低于已用金额 ¥{used:,.2f}")
    row.credit_limit = Decimal(str(round(new_limit, 2)))
    if not row.enabled and new_limit > 0:
        row.enabled = True
        row.status_label = "正常"
    pct = round(100 * used / new_limit, 1) if new_limit else 0
    if pct >= 95:
        row.status_label = "超额预警"
    elif row.grade == "C":
        row.status_label = "降级观察"
    elif row.enabled:
        row.status_label = "正常"
    _audit(
        db,
        hotel_id,
        "credit",
        "调额",
        row.name,
        f"¥{old:,.0f} → ¥{new_limit:,.0f}",
        reason,
        _user_name(db, operator_id),
    )
    db.commit()
    return get_credit_workspace(db, hotel_id)


def update_bad_debt_rate(
    db: Session,
    hotel_id: int,
    rate_id: int,
    *,
    rate_pct: float,
    reason: str,
    operator_id: int | None = None,
) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 4:
        raise InvalidStateError("变更原因不少于 4 字")
    if rate_pct < 0 or rate_pct > 100:
        raise InvalidStateError("计提率无效")
    row = db.get(FinanceBadDebtRate, rate_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("坏账准备率配置不存在")
    old = _f(row.rate_pct)
    row.rate_pct = Decimal(str(round(rate_pct, 2)))
    _audit(
        db,
        hotel_id,
        "credit",
        "坏账率",
        row.bucket_label or row.bucket,
        f"{old:.0f}% → {rate_pct:.0f}%",
        reason,
        _user_name(db, operator_id),
    )
    db.commit()
    return get_credit_workspace(db, hotel_id)
