# SPDX-License-Identifier: Apache-2.0
"""财务参数扩展：税率账期 / 收单费率 / 信用账龄 — 建表 + 种子。

财务参数种子已抽到 `finance.params_defaults`；本文件保留 schema 保活与种子函数。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import SessionLocal
from finance.params_defaults import SEED_BAD_DEBT, SEED_CHANNELS, SEED_CREDITS, SEED_TERMS
from models import (
    Base,
    FinanceAcquiringChannel,
    FinanceBadDebtRate,
    FinanceCreditCustomer,
    FinanceParamAudit,
    FinancePaymentTerm,
    FinanceTaxConfig,
    Hotel,
)


def ensure_finance_params_ext_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    for model in (
        FinanceTaxConfig,
        FinancePaymentTerm,
        FinanceAcquiringChannel,
        FinanceCreditCustomer,
        FinanceBadDebtRate,
        FinanceParamAudit,
    ):
        if model.__tablename__ not in tables:
            need.append(model.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def seed_finance_params_ext(db: Session, hotel_id: int = 1) -> None:
    from seed.locale_pack import seed_text as _st

    if not db.query(FinanceTaxConfig).filter_by(hotel_id=hotel_id, status="active").first():
        db.add(
            FinanceTaxConfig(
                hotel_id=hotel_id,
                version=3,
                taxpayer_type=_st("一般纳税人"),
                main_rate=0.06,
                price_mode=_st("价外"),
                tax_code="3070401000000000000",
                tax_no="91310101MA1FK****XQ",
                surcharge_note=_st("城建 7% / 教育 3% / 地方教育 2%"),
                effective_date=_d("2026-04-01"),
                status="active",
                change_reason=_st("一般纳税人核定"),
                maintainer_name=_st("财务-周敏"),
            )
        )
        db.add(
            FinanceParamAudit(
                hotel_id=hotel_id,
                domain="tax",
                action_type=_st("税率"),
                target=_st("主营税率"),
                change_text=_st("主营税率 6% → 6%（一般纳税人核定）", "Main rate 6% → 6% (general taxpayer)"),
                reason=_st("一般纳税人核定"),
                effective_date=_d("2026-04-01"),
                actor_names=_st("财务-周敏 / 店长-李建国"),
                status=_st("已生效"),
                created_at=datetime(2026, 4, 1, 10, 32),
            )
        )
        db.add(
            FinanceParamAudit(
                hotel_id=hotel_id,
                domain="tax",
                action_type=_st("初始化"),
                target="—",
                change_text=_st("初始化税率 6% + 8 类客户账期"),
                reason=_st("门店开业初始化"),
                effective_date=_d("2026-01-01"),
                actor_names=_st("系统初始化"),
                status=_st("已生效"),
                created_at=datetime(2026, 1, 1, 9, 0),
            )
        )

    if db.query(FinancePaymentTerm).filter_by(hotel_id=hotel_id).count() == 0:
        for name, label, desc, eff, sort in SEED_TERMS:
            db.add(
                FinancePaymentTerm(
                    hotel_id=hotel_id,
                    customer_type=_st(name),
                    term_label=_st(label),
                    description=_st(desc),
                    effective_date=_d(eff),
                    sort_order=sort,
                )
            )
        db.add(
            FinanceParamAudit(
                hotel_id=hotel_id,
                domain="tax",
                action_type=_st("账期"),
                target=_st("OTA 抖音来客"),
                change_text=_st("OTA 抖音来客 → T+7（新增渠道）", "OTA Douyin Life → T+7 (new channel)"),
                reason=_st("新增渠道", "New channel"),
                effective_date=_d("2026-02-01"),
                actor_names=_st("财务-周敏 / 店长-李建国"),
                status=_st("已生效"),
                created_at=datetime(2026, 2, 1, 9, 11),
            )
        )

    if db.query(FinanceAcquiringChannel).filter_by(hotel_id=hotel_id).count() == 0:
        for row in SEED_CHANNELS:
            code, name, rate, cap, settle, amin, wfee, mfee, gmv, en, st, sort = row
            db.add(
                FinanceAcquiringChannel(
                    hotel_id=hotel_id,
                    channel_code=code,
                    channel_name=_st(name),
                    rate_pct=rate,
                    rate_cap=cap,
                    settle_label=settle,
                    min_settle=amin,
                    withdraw_fee_pct=wfee,
                    month_fee=mfee,
                    month_gmv=gmv,
                    enabled=en,
                    status_label=_st(st),
                    sort_order=sort,
                )
            )
        for t, ch, act, old, neu, reason, who, st in (
            ("2026-01-01 09:00", "微信支付", "初始化", "—", "0.60%", "门店开业初始化", "财务-周敏", "已生效"),
            (
                "2026-01-15 14:20",
                "银联二维码",
                "费率调整",
                "0.60%",
                "0.38%",
                "银联标准类调整",
                "财务-周敏 / 店长-李建国",
                "已生效",
            ),
            (
                "2026-03-08 11:00",
                "云闪付",
                "申请开通",
                "未启用",
                "审核中",
                "门店支持 NFC 闪付",
                "店长-李建国",
                "审核中",
            ),
        ):
            db.add(
                FinanceParamAudit(
                    hotel_id=hotel_id,
                    domain="acquiring",
                    action_type=_st(act),
                    target=_st(ch),
                    change_text=f"{old} → {neu}",
                    reason=_st(reason),
                    actor_names=_st(who),
                    status=_st(st),
                    created_at=datetime.fromisoformat(t.replace(" ", "T")),
                )
            )

    if db.query(FinanceCreditCustomer).filter_by(hotel_id=hotel_id).count() == 0:
        for name, ctype, grade, lim, used, term, rated, st, en, sort in SEED_CREDITS:
            db.add(
                FinanceCreditCustomer(
                    hotel_id=hotel_id,
                    name=_st(name),
                    customer_type=_st(ctype),
                    grade=grade,
                    credit_limit=lim,
                    credit_used=used,
                    term_label=_st(term) if term and term != "—" else term,
                    rated_at=_d(rated),
                    status_label=_st(st),
                    enabled=en,
                    sort_order=sort,
                )
            )
        for t, typ, obj, chg, reason, who, st in (
            (
                "2026-05-10 14:20",
                "停用",
                "某问题客户",
                "正常 → 停用挂账",
                "多次逾期未回款",
                "销售-王芳 / 财务-周敏 / 总经理-张总",
                "已停用",
            ),
            (
                "2026-04-01 10:00",
                "调额",
                "某小旅行社",
                "¥20,000 → ¥10,000",
                "3 次逾期，降级观察",
                "销售-王芳 / 财务-周敏",
                "已生效",
            ),
            (
                "2026-03-10 09:30",
                "新增",
                "本地科技公司",
                "— → ¥20,000",
                "新增协议客户",
                "销售-王芳 / 财务-周敏 / 总经理-张总",
                "已生效",
            ),
            (
                "2026-01-15 10:00",
                "评级",
                "中青旅控股",
                "B → A 优",
                "近 6 个月回款 100% 准时",
                "财务-周敏 / 总经理-张总",
                "已生效",
            ),
            ("2026-01-01 09:00", "初始化", "—", "初始化 4 客户 + 4 档坏账率", "门店开业初始化", "系统初始化", "已生效"),
        ):
            db.add(
                FinanceParamAudit(
                    hotel_id=hotel_id,
                    domain="credit",
                    action_type=_st(typ),
                    target=_st(obj) if obj != "—" else obj,
                    change_text=_st(chg),
                    reason=_st(reason),
                    actor_names=_st(who),
                    status=_st(st),
                    created_at=datetime.fromisoformat(t.replace(" ", "T")),
                )
            )

    if db.query(FinanceBadDebtRate).filter_by(hotel_id=hotel_id).count() == 0:
        for bucket, label, rate, desc, sort in SEED_BAD_DEBT:
            db.add(
                FinanceBadDebtRate(
                    hotel_id=hotel_id,
                    bucket=bucket,
                    bucket_label=_st(label),
                    rate_pct=rate,
                    description=_st(desc),
                    sort_order=sort,
                )
            )

    db.commit()


def bootstrap_finance_params_ext(engine, hotel_id: int = 1) -> None:
    ensure_finance_params_ext_schema(engine)
    db = SessionLocal()
    try:
        if not db.query(Hotel).filter_by(id=hotel_id).first():
            return
        seed_finance_params_ext(db, hotel_id)
    finally:
        db.close()
