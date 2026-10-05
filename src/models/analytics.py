# SPDX-License-Identifier: Apache-2.0
"""analytics 域 ORM 模型。"""

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
    func,
)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    account = Column(String(40))
    debit = Column(Numeric(12, 2), default=0)
    credit = Column(Numeric(12, 2), default=0)
    currency = Column(String(3), default="CNY")
    ref_type = Column(String(30))
    ref_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AiReportInterpretation(Base):
    """财务报表 AI 解读记录（报告特化 · Harness 起草）。"""

    __tablename__ = "ai_report_interpretations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    report_code = Column(String(40), nullable=False)
    report_type = Column(String(60), nullable=False)
    period_start = Column(Date)
    period_end = Column(Date)
    period_label = Column(String(80))
    compare = Column(String(20), default="yoy")
    snapshot_hash = Column(String(64))
    snapshot_json = Column(Text)
    insight = Column(Text)
    findings_json = Column(Text)
    suggestions_json = Column(Text)
    actions_json = Column(Text)
    raw_response = Column(Text)
    model_name = Column(String(80), default="")  # 运行时写入当前配置的模型名
    prompt_version = Column(String(40), default="report-ai-v1")
    status = Column(String(20), default="ready")  # ready / failed / partial
    created_by = Column(String(60), default="ai_agent")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AiActionConfirmation(Base):
    """财务报表 AI 解读 · 可执行操作人工确认闸。"""

    __tablename__ = "ai_action_confirmations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    interpretation_id = Column(Integer, ForeignKey("ai_report_interpretations.id", ondelete="CASCADE"), nullable=False)
    action_index = Column(Integer, nullable=False, default=0)
    action_kind = Column(String(40), nullable=False)
    action_payload = Column(Text)
    decision = Column(String(20), nullable=False)  # confirmed / dismissed
    decided_by = Column(String(80))
    decided_at = Column(DateTime)
    decision_remark = Column(String(200))
    exec_result = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ProfitInsight(Base):
    """AI 利润优化建议快照。"""

    __tablename__ = "profit_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    title = Column(String(120))
    recommendation = Column(Text)
    impact_amount = Column(Numeric(12, 2), default=0)
    category = Column(String(40))  # rate / cost / channel / tax
    status = Column(String(20), default="open")  # open / accepted / dismissed
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RevenueAnomaly(Base):
    """营收异常 / 欺诈监控告警。"""

    __tablename__ = "revenue_anomalies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(40))  # ANM-xxxx
    category = Column(String(20), default="price")  # price / ota / void
    title = Column(String(120))
    subtitle = Column(String(200))
    score = Column(Integer, default=50)
    tone = Column(String(10), default="mid")  # high / mid / low
    description = Column(Text)
    detail_title = Column(String(80))
    actor = Column(String(80))
    room_label = Column(String(80))
    event_time = Column(String(40))
    orig_amount = Column(Numeric(12, 2), default=0)
    new_amount = Column(Numeric(12, 2), default=0)
    diff_label = Column(String(40))
    timeline_json = Column(Text)  # JSON array of {tone,title,time,text,ai?}
    ai_hint = Column(Text)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AiDiagnosisResult(Base):
    """智能问数诊断结果（只存建议，执行在价格助手）。"""

    __tablename__ = "ai_diagnosis_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime, nullable=False)
    snapshot_json = Column(Text)  # 入模快照留痕
    model_name = Column(String(80), default="")  # 运行时写入当前配置的模型名
    issues_json = Column(Text)  # issues[]
    status = Column(String(20), default="done")  # done / failed / adopted / ignored
    created_by = Column(String(40), default="ai_agent")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class InsightDiagnosisResult(Base):
    """数据洞察 · 四维诊断卡留痕（只读建议，不改业务数据）。"""

    __tablename__ = "insight_diagnosis_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_range = Column(String(64), nullable=False)
    compare_baseline = Column(String(20), default="yoy")
    dimension = Column(String(40), nullable=False)  # segment / channel / review / profit
    severity = Column(String(8), default="P3")
    evidence_json = Column(Text)
    revenue_impact = Column(String(80))
    suggested_action = Column(String(240))
    confidence = Column(String(8), default="中")
    snapshot_hash = Column(String(64))
    created_by = Column(String(40), default="ai_agent")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AiAskSession(Base):
    """AI 问数会话（多轮追问上下文）。"""

    __tablename__ = "ai_ask_sessions"
    session_id = Column(String(64), primary_key=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class AiAskQuery(Base):
    """数据洞察 · AI 问数会话留痕（确认前不查库）。"""

    __tablename__ = "ai_ask_queries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    parent_query_id = Column(Integer, ForeignKey("ai_ask_queries.id", ondelete="SET NULL"))
    raw_question = Column(Text)
    normalized_question = Column(Text)  # v1.2 术语归一化后
    resolved_question = Column(Text)  # 指代消解后的完整问句
    intent_id = Column(String(64))
    intent_label = Column(String(120))
    metric_id = Column(String(64))
    operator_id = Column(String(32))
    slots_json = Column(Text)
    tier0_candidates = Column(Text)
    need_clarify = Column(Boolean, default=True)
    clarify_round = Column(Integer, default=0)
    confirmed_at = Column(DateTime)
    query_ref = Column(String(80))
    result_json = Column(Text)
    answer_json = Column(Text)
    playbook_tips = Column(Text)  # JSON：本轮命中的 playbook 条目
    model_name = Column(String(80), default="")  # 运行时写入当前配置的模型名
    snapshot_hash = Column(String(64))
    pii_accessed = Column(Boolean, default=False)
    pii_ack_by = Column(String(40))
    pii_ack_at = Column(DateTime)
    created_by = Column(String(40), default="ai_agent")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(40))
    level = Column(String(20))
    message = Column(Text)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AiCommand(Base):
    __tablename__ = "ai_commands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    utterance = Column(String(255))
    intent = Column(String(40))
    result = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ShiftHandover(Base):
    """交班主档：钱/物/事 + 三方签字。"""

    __tablename__ = "shift_handovers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    shift_no = Column(SmallInteger, nullable=False, default=1)  # 1早中 / 2晚 / 3夜
    shift_date = Column(Date, nullable=False)
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    scheduled_handover_at = Column(DateTime)
    outgoing_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    incoming_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    manager_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(String(30), default="in_progress")
    total_revenue = Column(Numeric(14, 2), default=0)
    float_expected = Column(Numeric(14, 2), default=5000)
    float_actual = Column(Numeric(14, 2))
    float_diff = Column(Numeric(14, 2), default=0)
    diff_type = Column(String(10))  # flat / long / short
    diff_reason = Column(Text)
    float_confirmed = Column(Boolean, default=False)
    assets_confirmed = Column(Boolean, default=False)
    deposit_collected = Column(Numeric(14, 2), default=0)
    deposit_refunded = Column(Numeric(14, 2), default=0)
    deposit_net = Column(Numeric(14, 2), default=0)
    deposit_collected_count = Column(SmallInteger, default=0)
    deposit_refunded_count = Column(SmallInteger, default=0)
    incoming_ack_money = Column(Boolean, default=False)
    incoming_ack_assets = Column(Boolean, default=False)
    incoming_ack_tasks = Column(Boolean, default=False)
    received_revenue_ok = Column(Boolean, default=False)
    deposit_ack = Column(Boolean, default=False)
    float_received_confirmed = Column(Boolean, default=False)
    assets_received_confirmed = Column(Boolean, default=False)
    matters_confirmed = Column(Boolean, default=False)
    received_float_actual = Column(Numeric(14, 2))
    received_float_match_outgoing = Column(Boolean, default=True)
    guest_situation_acks = Column(Text)  # JSON: list of situation keys
    task_claims = Column(Text)  # JSON: {index: claimed|escalated}
    carryover_acks = Column(Text)  # JSON: list of carryover ids
    narrative = Column(Text)  # 交班叙事（AI 确认后可改）
    ai_draft_json = Column(Text)  # JSON: 待确认 AI 草稿
    ai_approved_json = Column(Text)  # JSON: 已确认 AI 项快照
    guest_situations_snapshot = Column(Text)  # JSON: 冻结客情（签字/AI确认）
    ai_session_id = Column(String(64))
    ai_draft_confirmed_at = Column(DateTime)
    ai_draft_confirmed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    manager_required = Column(Boolean, default=False)
    outgoing_signed_at = Column(DateTime)
    incoming_signed_at = Column(DateTime)
    manager_signed_at = Column(DateTime)
    completed_at = Column(DateTime)
    archived_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ShiftHandoverTask(Base):
    """交班待办 / 遗留事项。"""

    __tablename__ = "shift_handover_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    handover_id = Column(Integer, ForeignKey("shift_handovers.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    priority = Column(String(4), default="P2")  # P0/P1/P2
    content = Column(Text, nullable=False)
    owner_name = Column(String(80))
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    due_at = Column(DateTime)
    status = Column(String(20), default="open")  # open / escalated / done / carried
    linked_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    source_shift_no = Column(SmallInteger)
    is_carryover = Column(Boolean, default=False)
    task_type = Column(String(20), default="normal")  # normal / replenish
    created_by = Column(String(40), default="manual")  # manual / ai_agent
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    ai_session_id = Column(String(64))
    source = Column(String(40))  # oneid_history / system_events / ...
    escalated_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ShiftReceiveDiff(Base):
    """接班人差异上报（内控留痕）。"""

    __tablename__ = "shift_receive_diffs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    handover_id = Column(Integer, ForeignKey("shift_handovers.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(40), nullable=False)  # float / asset
    item_key = Column(String(80))
    declared_val = Column(Numeric(14, 2))
    received_val = Column(Numeric(14, 2))
    diff_val = Column(Numeric(14, 2))
    reason = Column(Text)
    suggestion = Column(String(20))  # 追补 / 交回（AI 拟稿）
    reporter_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(String(24), default="pending_manager")  # pending_manager / resolved
    created_at = Column(DateTime, server_default=func.now())
