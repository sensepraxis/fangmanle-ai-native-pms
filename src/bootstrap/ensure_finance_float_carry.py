# SPDX-License-Identifier: Apache-2.0
"""财务参数 · 门店备用金：建表 + 店初始化（¥2000 CNY）。

备用金默认值已抽到 `finance.float_defaults`；本文件保留 schema 保活与种子函数。
"""

from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import SessionLocal
from finance.float_defaults import DEFAULT_AMOUNT, DEFAULT_CURRENCY, DEFAULT_DENOM_RATIOS
from infra.auth_local import hash_password
from models import Base, FinanceFloatCarry, FinanceReport, Hotel


def ensure_finance_float_carry_schema(engine):
    insp = inspect(engine)
    if "finance_float_carry" not in insp.get_table_names():
        Base.metadata.create_all(engine, tables=[FinanceFloatCarry.__table__])


def ensure_finance_review_users(db: Session) -> None:
    """双审账号：对齐 RBAC 四角色。"""
    from bootstrap.ensure_rbac import ensure_rbac_users

    ensure_rbac_users(db)


def _sync_finance_report(db: Session, hotel_id: int, amount: float) -> None:
    db.add(
        FinanceReport(
            hotel_id=hotel_id,
            metric="float_carry",
            period=date.today().strftime("%Y-%m-%d"),
            value=amount,
        )
    )


def ensure_float_carry_2000(db: Session, hotel_id: int = 1) -> FinanceFloatCarry:
    """确保店生效备用金为 ¥2000 CNY。"""
    active = (
        db.query(FinanceFloatCarry)
        .filter_by(hotel_id=hotel_id, status="active")
        .order_by(FinanceFloatCarry.id.desc())
        .first()
    )
    now = datetime.now()
    if active:
        active.amount = DEFAULT_AMOUNT
        active.currency = DEFAULT_CURRENCY
        active.denom_ratios = json.dumps(DEFAULT_DENOM_RATIOS, ensure_ascii=False)
        if not active.effective_date:
            active.effective_date = date.today()
        if not active.change_reason:
            active.change_reason = "门店开业初始化设置"
        db.flush()
        _sync_finance_report(db, hotel_id, DEFAULT_AMOUNT)
        db.commit()
        return active

    row = FinanceFloatCarry(
        hotel_id=hotel_id,
        amount=DEFAULT_AMOUNT,
        currency=DEFAULT_CURRENCY,
        denom_ratios=json.dumps(DEFAULT_DENOM_RATIOS, ensure_ascii=False),
        effective_date=date.today(),
        change_reason="门店开业初始化设置",
        status="active",
        activated_at=now,
    )
    db.add(row)
    db.flush()
    _sync_finance_report(db, hotel_id, DEFAULT_AMOUNT)
    db.commit()
    return row


def seed_finance_float_carry(db: Session, hotel_id: int = 1, amount: float = DEFAULT_AMOUNT) -> None:
    ensure_finance_review_users(db)
    ensure_float_carry_2000(db, hotel_id)


def bootstrap_finance_float_carry(engine, hotel_id: int = 1) -> None:
    ensure_finance_float_carry_schema(engine)
    db = SessionLocal()
    try:
        if not db.query(Hotel).filter_by(id=hotel_id).first():
            return
        seed_finance_float_carry(db, hotel_id)
    finally:
        db.close()
