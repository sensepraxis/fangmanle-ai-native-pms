# SPDX-License-Identifier: Apache-2.0
"""finance 域 ORM 模型。"""

from models._types import (
    Base,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)


class ChannelCommission(Base):
    """渠道佣金覆盖层：按酒店 × 渠道 × 房型/价格代码（呼应携程按房型分设）。"""

    __tablename__ = "channel_commission"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel_code = Column(String(32), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=True)
    rate_code = Column(String(32), nullable=True)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    settle_cycle = Column(String(16))
    is_enabled = Column(Boolean, default=True)
    effective_from = Column(Date)
    effective_to = Column(Date)
    owner_role = Column(String(32), default="老板/财务")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(32))
    note = Column(String(255))
    __table_args__ = (
        UniqueConstraint(
            "hotel_id",
            "channel_code",
            "room_type_id",
            "rate_code",
            "effective_from",
            name="uq_channel_commission_dim",
        ),
    )


# ============================================================================
class CorpAccount(Base):
    """合作企业（协议客账户）：量价置换、挂账结算、价格刚性；授信与 AR 主档联动。"""

    __tablename__ = "corp_accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    industry = Column(String(60))
    contact_name = Column(String(60))
    contact_phone = Column(String(30))
    settlement_mode = Column(String(20), default="挂账")  # 挂账 / 月结
    price_policy = Column(String(20), default="rigid")  # rigid = 不随淡旺季浮动
    annual_commit_nights = Column(Integer, default=0)
    used_nights_ytd = Column(Integer, default=0)
    # AR / 授信（与 pms_ar 对齐）
    credit_limit = Column(Numeric(14, 2), default=0)
    credit_used = Column(Numeric(14, 2), default=0)
    settle_cycle = Column(String(20), default="monthly")  # monthly / weekly / periody
    valid_from = Column(Date)
    valid_to = Column(Date)
    status = Column(String(20), default="active")
    note = Column(Text)
    __table_args__ = (UniqueConstraint("hotel_id", "code", name="uq_corp_hotel_code"),)


# ============================================================================
class CorpPriceLadder(Base):
    """企业协议价阶梯：按年累计间夜量价置换，合同期内刚性价。"""

    __tablename__ = "corp_price_ladders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_id = Column(Integer, ForeignKey("corp_accounts.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    tier_name = Column(String(60), nullable=False)
    min_annual_nights = Column(Integer, default=0)
    max_annual_nights = Column(Integer)  # None = 无上限
    contract_price = Column(Numeric(10, 2), nullable=False)
    sort_order = Column(SmallInteger, default=0)
    seasonal_float = Column(Boolean, default=False)  # False = 价格刚性
    __table_args__ = (UniqueConstraint("corp_id", "room_type_id", "tier_name", name="uq_corp_ladder_tier"),)


# ============================================================================
class OtaSettlement(Base):
    """OTA 平台结算批次：房费毛额 / 佣金 / 结算净额，与财务对账同源。"""

    __tablename__ = "ota_settlements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"))
    platform = Column(String(40), nullable=False)  # ctrip / meituan / fliggy / douyin
    period = Column(String(7), nullable=False)  # YYYY-MM
    gross_amount = Column(Numeric(14, 2), default=0)
    commission_amount = Column(Numeric(14, 2), default=0)
    net_amount = Column(Numeric(14, 2), default=0)
    paid_net = Column(Numeric(14, 2), default=0)
    recon_batch_id = Column(Integer, ForeignKey("recon_batches.id", ondelete="SET NULL"))
    status = Column(String(20), default="open")  # open / partial / settled
    due_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "channel_id", "period", name="uq_ota_settle_period"),)


# ============================================================================
class ArInvoice(Base):
    """应收单据：企业挂账 / OTA 结算 / 会议 / 长包等。"""

    __tablename__ = "ar_invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    invoice_no = Column(String(32), nullable=False)
    ar_type = Column(
        String(30), nullable=False
    )  # corp_on_account / ota_settlement / meeting / longstay / member_prepaid
    customer_name = Column(String(120), nullable=False)
    corp_id = Column(Integer, ForeignKey("corp_accounts.id", ondelete="SET NULL"))
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    ota_settlement_id = Column(Integer, ForeignKey("ota_settlements.id", ondelete="SET NULL"))
    pms_ar_entry_id = Column(Integer, ForeignKey("pms_ar_entries.id", ondelete="SET NULL"))
    doc_label = Column(String(120))
    amount = Column(Numeric(14, 2), default=0)
    paid_amount = Column(Numeric(14, 2), default=0)
    due_date = Column(Date)
    status = Column(String(20), default="open")  # open / partial / settled / overdue / bad_debt
    credit_limit_snapshot = Column(Numeric(14, 2))
    pill_note = Column(String(80))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "invoice_no", name="uq_ar_invoice_no"),)


# ============================================================================
class ApInvoice(Base):
    """应付单据：OTA 佣金 / 供应商 / 外包 / 房租等。"""

    __tablename__ = "ap_invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    invoice_no = Column(String(32), nullable=False)
    ap_type = Column(String(30), nullable=False)  # ota_commission / supplier / outsource / rent
    vendor_name = Column(String(120), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"))
    ota_settlement_id = Column(Integer, ForeignKey("ota_settlements.id", ondelete="SET NULL"))
    doc_label = Column(String(120))
    amount = Column(Numeric(14, 2), default=0)
    paid_amount = Column(Numeric(14, 2), default=0)
    due_date = Column(Date)
    status = Column(String(20), default="open")  # open / partial / settled / pending_deduct / disputed
    note = Column(String(120))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "invoice_no", name="uq_ap_invoice_no"),)


# ============================================================================
class ArApLog(Base):
    """应收应付审计日志：挂账 / 回款 / 付款 / 坏账 / 授信校验。"""

    __tablename__ = "ar_ap_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(30), nullable=False)  # charge / receipt / payment / write_off / credit_check
    ref_type = Column(String(10))  # ar / ap
    ref_id = Column(Integer)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    operator_name = Column(String(60))
    amount = Column(Numeric(14, 2), default=0)
    reason = Column(Text)
    meta = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Deposit(Base):
    """押金主档：从属订单，PMS 只记账不碰钱。"""

    __tablename__ = "deposits"
    deposit_id = Column(String(32), primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String(64), nullable=False)  # Guest.one_id
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    room_no = Column(String(8), nullable=False)
    form = Column(String(24), nullable=False)  # PREAUTH_CARD / WECHAT_DEPOSIT / ...
    original_amount = Column(Integer, nullable=False)  # 分
    captured_amount = Column(Integer, nullable=False, default=0)
    remaining_refund = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="CREATED")
    auth_code = Column(String(64))
    auth_expire_at = Column(DateTime)
    ar_account_id = Column(String(32))
    receipt_no = Column(String(32))
    operator_id = Column(String(32), nullable=False, default="system")
    idempotency_key = Column(String(64), unique=True)
    guest_name = Column(String(80))  # 冗余展示
    order_no = Column(String(40))  # 冗余展示
    created_at = Column(DateTime, server_default=func.now())
    released_at = Column(DateTime)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def apply_event(self, event: str, *, full_capture: bool | None = None) -> str:
        """按押金状态机推进；返回新 status。"""
        from finance.deposit_status import next_status

        to = next_status(self.status or "CREATED", event, full_capture=full_capture)
        self.status = to
        return to


# ============================================================================
class DepositLedgerEntry(Base):
    """押金状态变更流水（审计）。"""

    __tablename__ = "deposit_ledger_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    deposit_id = Column(String(32), ForeignKey("deposits.deposit_id", ondelete="CASCADE"), nullable=False)
    event = Column(String(32), nullable=False)
    from_status = Column(String(32))
    to_status = Column(String(32))
    amount_delta = Column(Integer, default=0)  # 分
    operator_id = Column(String(32))
    channel_ref = Column(String(64))
    memo = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    invoice_no = Column(String(40), unique=True)
    amount = Column(Numeric(12, 2))
    tax = Column(Numeric(12, 2), default=0)
    status = Column(String(20), default="open")
    issued_at = Column(DateTime)


# ============================================================================
class Payment(Base):
    """收款记录（逻辑域 pms_payment）：POS 人工录入 + 小票对账，无支付网关对接。"""

    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    folio_id = Column(Integer, ForeignKey("pms_folios.id", ondelete="SET NULL"))
    method = Column(String(30))
    # cash / wechat_pos / alipay_pos / card / ar / deposit_offset
    amount = Column(Numeric(12, 2))  # 应收/记账金额
    received_amount = Column(Numeric(12, 2))  # 实收
    pos_slip_no = Column(String(60))  # POS 小票号（财务对账核心）
    settle_type = Column(String(20), default="full")  # full / partial / deposit
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    paid_at = Column(DateTime, server_default=func.now())
    note = Column(Text)


# ============================================================================
class NightAuditLog(Base):
    __tablename__ = "night_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    exceptions = Column(Integer, default=0)
    revenue = Column(Numeric(12, 2), default=0)
    room_nights = Column(Integer, default=0)
    ran_at = Column(DateTime)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    __table_args__ = (UniqueConstraint("hotel_id", "biz_date", name="uq_nightaudit_hotel_date"),)


# ============================================================================
class FinanceReport(Base):
    __tablename__ = "finance_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    period = Column(String(20))
    metric = Column(String(40))
    value = Column(Numeric(14, 2))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class FinanceReportExport(Base):
    """财务报表导出归档（≥7 年）。"""

    __tablename__ = "finance_report_exports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    report_code = Column(String(40), nullable=False)
    report_name = Column(String(120))
    format = Column(String(10), nullable=False)  # xlsx / pdf / csv
    status = Column(String(20), default="ready")  # processing / ready / failed
    file_name = Column(String(200))
    file_path = Column(String(500))
    size_bytes = Column(Integer, default=0)
    row_count = Column(Integer, default=0)
    async_job = Column(Integer, default=0)
    period_start = Column(Date)
    period_end = Column(Date)
    generated_at = Column(DateTime)
    generated_by = Column(String(60))
    expires_at = Column(DateTime)
    snapshot_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class NightAuditException(Base):
    """夜审异常项（自动修复 / 巡航台用）。"""

    __tablename__ = "night_audit_exceptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    audit_log_id = Column(Integer, ForeignKey("night_audit_logs.id", ondelete="SET NULL"))
    biz_date = Column(Date, nullable=False)
    code = Column(String(40))
    title = Column(String(120))
    detail = Column(Text)
    severity = Column(String(20), default="mid")  # low / mid / high
    status = Column(String(20), default="open")  # open / fixed / ignored
    fixed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ReconBatch(Base):
    """渠道对账批次。"""

    __tablename__ = "recon_batches"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    channel = Column(String(40))  # ota / wechat / alipay / bank / all
    status = Column(String(20), default="open")  # open / matched / conflict / closed
    pms_total = Column(Numeric(14, 2), default=0)
    channel_total = Column(Numeric(14, 2), default=0)
    variance = Column(Numeric(14, 2), default=0)
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ReconItem(Base):
    """对账明细 / 冲突下钻。"""

    __tablename__ = "recon_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("recon_batches.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    side = Column(String(20), default="pms")  # pms / channel
    ref_no = Column(String(60))
    amount = Column(Numeric(12, 2), default=0)
    match_status = Column(String(20), default="unmatched")  # matched / unmatched / conflict
    note = Column(String(200))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))


# ============================================================================
class TaxFiling(Base):
    """报税 / 开票任务。"""

    __tablename__ = "tax_filings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    period = Column(String(20))  # YYYY-MM
    filing_type = Column(String(40), default="vat")  # vat / invoice_pack
    tax_amount = Column(Numeric(14, 2), default=0)
    invoice_count = Column(Integer, default=0)
    status = Column(String(20), default="draft")  # draft / ready / filed / failed
    filed_at = Column(DateTime)
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RefundAdjustConfig(Base):
    """退改与反结账 · 酒店级授权阈值。"""

    __tablename__ = "refund_adjust_configs"
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), primary_key=True)
    refund_threshold_yuan = Column(Integer, nullable=False, default=2000)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class RefundAdjustTicket(Base):
    """退改 / 改账 / 反结账工单。"""

    __tablename__ = "refund_adjust_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_no = Column(String(40), nullable=False, unique=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    op_type = Column(String(20), nullable=False)  # refund | adjust | reverse
    status = Column(String(32), nullable=False, default="pending_approval")
    # pending_approval / pending_dual_auth / approved / done / rejected / failed
    title = Column(String(120), nullable=False)
    detail = Column(String(255))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    order_no = Column(String(40))
    guest_name_masked = Column(String(40))
    amount_cents = Column(Integer, default=0)
    reason = Column(String(200))
    refund_method = Column(String(40))
    applicant_id = Column(String(40))
    auth_mgr_done = Column(Integer, default=0)
    auth_fin_done = Column(Integer, default=0)
    auth_mgr_by = Column(String(40))
    auth_fin_by = Column(String(40))
    payload_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class RefundAdjustAudit(Base):
    """退改审计留痕。"""

    __tablename__ = "refund_adjust_audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    ticket_id = Column(Integer, ForeignKey("refund_adjust_tickets.id", ondelete="CASCADE"))
    event = Column(String(40), nullable=False)
    actor_id = Column(String(40))
    memo = Column(String(255))
    before_json = Column(Text)
    after_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class FinanceFloatCarry(Base):
    """门店备用金底数：生效配置 + 变更审批流水（审计留痕）。"""

    __tablename__ = "finance_float_carry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(8), default="CNY")
    denom_ratios = Column(Text)  # JSON: [{denom, ratio, label}]
    effective_date = Column(Date)
    change_reason = Column(Text)
    old_amount = Column(Numeric(14, 2))
    status = Column(String(24), default="active")  # active / pending_finance / pending_manager / rejected / superseded
    applicant_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    finance_approver_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    finance_approved_at = Column(DateTime)
    manager_approver_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    manager_approved_at = Column(DateTime)
    rejected_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    rejected_at = Column(DateTime)
    reject_reason = Column(Text)
    activated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class FinanceTaxConfig(Base):
    """税率配置（门店级，版本化）。"""

    __tablename__ = "finance_tax_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)
    taxpayer_type = Column(String(40), default="一般纳税人")
    main_rate = Column(Numeric(6, 4), default=0.06)  # 0.06 = 6%
    price_mode = Column(String(20), default="价外")  # 价外 / 价内
    tax_code = Column(String(40), default="3070401000000000000")
    tax_no = Column(String(40))
    surcharge_note = Column(String(120), default="城建 7% / 教育 3% / 地方教育 2%")
    effective_date = Column(Date)
    status = Column(String(24), default="active")  # active / superseded / pending
    change_reason = Column(Text)
    maintainer_name = Column(String(80))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class FinancePaymentTerm(Base):
    """客户类型账期。"""

    __tablename__ = "finance_payment_terms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    customer_type = Column(String(60), nullable=False)
    term_label = Column(String(40), nullable=False)  # 即付 · 0 天 / T+15
    description = Column(String(200))
    effective_date = Column(Date)
    sort_order = Column(SmallInteger, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class FinanceAcquiringChannel(Base):
    """收单渠道费率（店方承担手续费）。"""

    __tablename__ = "finance_acquiring_channels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel_code = Column(String(40), nullable=False)
    channel_name = Column(String(80), nullable=False)
    rate_pct = Column(Numeric(8, 4))  # 0.60 = 0.60%
    rate_cap = Column(Numeric(10, 2))  # 封顶金额，如借记卡 ¥20
    settle_label = Column(String(20), default="T+1")
    min_settle = Column(Numeric(10, 2), default=0.01)
    withdraw_fee_pct = Column(Numeric(8, 4), default=0)
    month_fee = Column(Numeric(14, 2), default=0)
    month_gmv = Column(Numeric(14, 2), default=0)  # 用于预估月影响
    enabled = Column(Boolean, default=True)
    status_label = Column(String(20), default="上线")  # 上线 / 低用量 / 未启用 / 审核中
    sort_order = Column(SmallInteger, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class FinanceCreditCustomer(Base):
    """授信客户清单（财务参数 · 信用与账龄）。"""

    __tablename__ = "finance_credit_customers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    customer_type = Column(String(40))  # 旅行社 / 企业挂账 / OTA
    grade = Column(String(4), default="B")  # A/B/C/D
    credit_limit = Column(Numeric(14, 2), default=0)
    credit_used = Column(Numeric(14, 2), default=0)
    term_label = Column(String(40))
    rated_at = Column(Date)
    status_label = Column(String(40), default="正常")  # 正常 / 超额预警 / 降级观察 / 停用挂账
    enabled = Column(Boolean, default=True)
    sort_order = Column(SmallInteger, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class FinanceBadDebtRate(Base):
    """账龄段坏账准备率。"""

    __tablename__ = "finance_bad_debt_rates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    bucket = Column(String(20), nullable=False)  # 0-30 / 30-60 / 60-90 / 90+
    bucket_label = Column(String(40))
    rate_pct = Column(Numeric(6, 2), default=0)  # 5 = 5%
    description = Column(String(120))
    sort_order = Column(SmallInteger, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class FinanceParamAudit(Base):
    """财务参数通用变更历史。"""

    __tablename__ = "finance_param_audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    domain = Column(String(40), nullable=False)  # tax / acquiring / credit
    action_type = Column(String(40))
    target = Column(String(120))
    change_text = Column(String(255))
    reason = Column(Text)
    effective_date = Column(Date)
    actor_names = Column(String(160))
    status = Column(String(24), default="已生效")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ShiftFloatCount(Base):
    """备用金盘库明细（清点到分）。"""

    __tablename__ = "shift_float_counts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    handover_id = Column(Integer, ForeignKey("shift_handovers.id", ondelete="CASCADE"), nullable=False)
    denom = Column(Numeric(8, 2), nullable=False)
    label = Column(String(20))
    expected_qty = Column(Integer, default=0)
    actual_qty = Column(Integer, default=0)
    received_qty = Column(Integer)
    subtotal = Column(Numeric(14, 2), default=0)


# ============================================================================
class ShiftAuditLog(Base):
    """交班审计日志。"""

    __tablename__ = "shift_audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    handover_id = Column(Integer, ForeignKey("shift_handovers.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(40), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    actor_name = Column(String(80))
    payload = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
