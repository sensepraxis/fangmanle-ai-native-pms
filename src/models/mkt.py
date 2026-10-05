# SPDX-License-Identifier: Apache-2.0
"""mkt 域 ORM 模型。"""

from models._types import (
    Base,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)


class Segment(Base):
    __tablename__ = "segments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"))
    name = Column(String(80), nullable=False)
    filter_rule = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class SegmentMember(Base):
    __tablename__ = "segment_members"
    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("segment_id", "guest_id", name="uq_segment_member"),)


# ============================================================================
class DemandForecast(Base):
    __tablename__ = "demand_forecast"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    predicted_occ = Column(Numeric(5, 4))
    predicted_adr = Column(Numeric(10, 2))
    model_version = Column(String(40))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30))
    name = Column(String(120))
    external_plan_id = Column(String(80))
    status = Column(String(20), default="draft")
    spend = Column(Numeric(12, 2), default=0)
    attributed_rev = Column(Numeric(12, 2), default=0)
    roi = Column(Numeric(8, 2))
    start_date = Column(Date)
    end_date = Column(Date)


# ============================================================================
class AcquisitionContent(Base):
    """获客内容（模拟小红书笔记等），无真实平台账号时用 seed/Mock。"""

    __tablename__ = "acquisition_contents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30), default="xiaohongshu")
    title = Column(String(200), nullable=False)
    topic = Column(String(80))
    status = Column(String(20), default="published")  # draft / published / archived
    impressions = Column(Integer, default=0)
    engagements = Column(Integer, default=0)
    spend = Column(Numeric(12, 2), default=0)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AcquisitionLead(Base):
    """获客线索：new → claimed → private → booked → arrived（Webhook 仅到 new）。"""

    __tablename__ = "acquisition_leads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30), default="xiaohongshu")
    lead_type = Column(String(20), default="dm")  # dm / form / manual
    external_id = Column(String(120))
    nickname = Column(String(80))
    phone = Column(String(30))
    wechat = Column(String(80))
    stage = Column(String(20), default="new")  # new / claimed / private / booked / arrived
    intent = Column(String(20), default="mid")  # high / mid / low
    note_title = Column(String(200))
    source_note_url = Column(String(500))
    xhs_plan_id = Column(String(80))
    xhs_creative_id = Column(String(80))
    xhs_unit_id = Column(String(80))
    payload_type = Column(String(40))
    campaign_json = Column(Text)
    content_id = Column(Integer, ForeignKey("acquisition_contents.id", ondelete="SET NULL"))
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    remark = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class GuestCoupon(Base):
    """客人券包（360 聚合视图）。

    本店营销发行以 MktCouponGrant 为权威，本表通过 grant_id 引用并投影；
    企微直发 / 外渠道（美团、抖音等）可无 grant，仅存在于券包。
    source 约定：native_mkt | wecom | meituan | douyin | xhs | ota
    """

    __tablename__ = "guest_coupons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    grant_id = Column(Integer, ForeignKey("mkt_coupon_grants.id", ondelete="SET NULL"))  # 本店发行实例
    code = Column(String(40), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    recipient_name = Column(String(80))  # 领券人
    channel = Column(String(40), default="企业微信")  # 展示用渠道文案
    coupon_type = Column(String(40), default="room_rate")  # room_rate
    discount_rate = Column(Numeric(4, 3), nullable=False)  # 0.700 = 7折
    source = Column(String(40), default="wecom")  # native_mkt / wecom / meituan / …
    status = Column(String(20), default="active")  # active / used / expired  （券状态）
    redeem_status = Column(String(20), default="unused")  # unused / redeemed （核销状态）
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    used_at = Column(DateTime)


# ============================================================================
class MktCampaign(Base):
    """活动策划。"""

    __tablename__ = "mkt_campaigns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    type = Column(String(32))  # holiday/seasonal/weekend/birthday/ota_compare/custom
    status = Column(String(16), default="draft")  # draft/pending/running/paused/ended/archived
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    template_id = Column(String(48))
    config_json = Column(Text)
    created_by = Column(String(32))
    approved_by = Column(String(32))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class MktCoupon(Base):
    """优惠券批次（语义 = mkt_coupon_batch；表名保留 mkt_coupons 兼容落地页 FK）。"""

    __tablename__ = "mkt_coupons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)  # = property_id
    batch_no = Column(String(40), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)  # 兼容旧值；权威：coupon_type
    coupon_type = Column(String(16))  # CASH_ROOM/CASH_ALL/DISCOUNT/BENEFIT
    face_value = Column(Numeric(10, 2), default=0)  # 兼容旧面额字段
    reduce_amount = Column(Numeric(10, 2))
    threshold = Column(Numeric(10, 2), default=0)
    discount_rate = Column(Numeric(5, 3))
    max_discount = Column(Numeric(10, 2))
    benefit_key = Column(String(32))
    benefit_value = Column(String(64))
    face_text = Column(String(128))
    scope_type = Column(String(16), default="ALL")  # ALL/ROOM_SPECIFIED
    scope_rooms = Column(Text)  # JSON list
    total_qty = Column(Integer, default=1000)
    granted_qty = Column(Integer, default=0)
    per_user_qty = Column(Integer, default=1)
    validity_mode = Column(String(8), default="FIXED")  # FIXED/RELATIVE
    validity_days = Column(Integer)
    batch_valid_from = Column(DateTime)
    batch_valid_to = Column(DateTime)
    valid_from = Column(DateTime)  # 兼容 = batch_valid_from
    valid_to = Column(DateTime)
    scope_json = Column(Text)
    status = Column(String(16), default="draft")  # draft/active/paused/expired
    created_by = Column(String(32))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class MktCouponGrant(Base):
    """券实例（语义 = mkt_coupon_instance；表名保留 mkt_coupon_grants）。"""

    __tablename__ = "mkt_coupon_grants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="CASCADE"), nullable=False)  # batch_id
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)  # customer_id
    code = Column(String(48), unique=True, nullable=False)  # coupon_code
    coupon_type = Column(String(16))
    face_text = Column(String(128))
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    grant_event = Column(String(32))
    grant_channel = Column(String(32), default="manual")
    grant_at = Column(DateTime, server_default=func.now())
    claim_at = Column(DateTime)
    used_at = Column(DateTime)
    used_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    used_amount = Column(Numeric(10, 2))
    redeemed_by = Column(String(32))
    status = Column(String(16), default="AVAILABLE")  # CLAIMABLE/AVAILABLE/USED/EXPIRED/VOID (+旧 unused)


# ============================================================================
class MktCouponTrigger(Base):
    """事件驱动发券规则（产品侧「自动发券」）。"""

    __tablename__ = "mkt_coupon_triggers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    batch_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128))  # 规则展示名
    event_type = Column(String(24), nullable=False)
    event_params = Column(Text)
    is_enabled = Column(Integer, default=1)
    last_run_at = Column(DateTime)
    granted_total = Column(Integer, default=0)  # 累计发放（冗余）
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class MktCouponGrantLog(Base):
    """发放流水（触发去重 + 审计）。"""

    __tablename__ = "mkt_coupon_grant_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger_id = Column(Integer, ForeignKey("mkt_coupon_triggers.id", ondelete="SET NULL"))
    auto_rule_id = Column(Integer, ForeignKey("mkt_coupon_auto_rule.id", ondelete="SET NULL"))
    batch_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    instance_id = Column(Integer, ForeignKey("mkt_coupon_grants.id", ondelete="CASCADE"), nullable=False)
    grant_event = Column(String(32))
    granted_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("trigger_id", "customer_id", "batch_id", name="uk_mkt_grant_dedup"),)


# ============================================================================
class MktCouponAutoRule(Base):
    """自动发券规则主表（替代 mkt_coupon_triggers）。"""

    __tablename__ = "mkt_coupon_auto_rule"
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(String(255))
    event_type = Column(String(24), nullable=False)
    event_params = Column(Text)  # JSON
    scan_frequency = Column(String(16), default="daily")  # realtime/daily/hourly/cron
    max_per_customer_day = Column(Integer, default=1)
    rule_cooldown_days = Column(Integer, default=30)
    global_silence_days = Column(Integer, default=7)
    active_window_start = Column(String(8))  # HH:MM:SS
    active_window_end = Column(String(8))
    push_channel = Column(String(32), default="wecom")
    status = Column(String(16), default="draft")  # draft/active/paused/expired
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    last_triggered_at = Column(DateTime)
    trigger_count_7d = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(32))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(32))
    __table_args__ = (UniqueConstraint("property_id", "name", name="uk_auto_rule_name"),)


# ============================================================================
class MktCouponAutoRuleCoupon(Base):
    """规则绑定的多券批次（优先级排序）。"""

    __tablename__ = "mkt_coupon_auto_rule_coupon"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("mkt_coupon_auto_rule.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint("rule_id", "batch_id", name="uk_rule_batch"),)


# ============================================================================
class MktCouponAutoRuleFilter(Base):
    """规则过滤条件（同 group_id 内 AND，组间 OR）。"""

    __tablename__ = "mkt_coupon_auto_rule_filter"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("mkt_coupon_auto_rule.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(Integer, nullable=False, default=1)
    field = Column(String(64), nullable=False)
    op = Column(String(16), nullable=False)
    value_json = Column(Text)  # JSON
    sort_order = Column(Integer, default=0)


# ============================================================================
class MktCouponAutoRuleTrigger(Base):
    """规则触发审计流水。"""

    __tablename__ = "mkt_coupon_auto_rule_trigger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("mkt_coupon_auto_rule.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="SET NULL"))
    instance_id = Column(Integer, ForeignKey("mkt_coupon_grants.id", ondelete="SET NULL"))
    matched = Column(Integer, default=0)  # 1=成功 / 0=拦截
    reason = Column(String(255))
    triggered_at = Column(DateTime, server_default=func.now())


# ============================================================================
class MktCouponRedeem(Base):
    """核销对账流水。"""

    __tablename__ = "mkt_coupon_redeems"
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("mkt_coupon_grants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    amount_saved = Column(Numeric(10, 2))
    cashier = Column(String(32))
    redeemed_at = Column(DateTime, server_default=func.now())


# ============================================================================
class MktCustomerNote(Base):
    """客户跟进备注。"""

    __tablename__ = "mkt_customer_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    note = Column(Text, nullable=False)
    tag = Column(String(32))
    created_by = Column(String(32))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class HotelMktSettings(Base):
    """门店营销侧轻配置（不含企微密钥）。"""

    __tablename__ = "hotel_mkt_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, unique=True)
    default_receiver_userid = Column(String(80))
    welcome_text = Column(Text)
    welcome_landing_page_id = Column(Integer, ForeignKey("wx_landing_pages.id", ondelete="SET NULL"))
    member_landing_page_id = Column(Integer, ForeignKey("wx_landing_pages.id", ondelete="SET NULL"))
    returning_landing_page_id = Column(Integer, ForeignKey("wx_landing_pages.id", ondelete="SET NULL"))
    points_json = Column(Text)  # 积分规则
    level_rule_json = Column(Text)  # 升降级规则（升级/保级/降级）
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class MktMemberLevel(Base):
    """会员等级规则（规则侧，非档案）。"""

    __tablename__ = "mkt_member_levels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    level_code = Column(String(16), nullable=False)  # silver/gold/platinum/diamond/supreme
    level_name = Column(String(32), nullable=False)
    upgrade_type = Column(String(16), default="growth")  # growth/nights/amount/stored
    upgrade_value = Column(Integer, default=0)
    retention_type = Column(String(16), default="growth")
    retention_value = Column(Integer, default=0)
    color_hex = Column(String(8))
    upgrade_points = Column(Integer, default=0)  # 升级所需成长值
    retain_points = Column(Integer, default=0)  # 保级所需成长值
    valid_months = Column(Integer, default=24)  # 0=终身
    growth_rule_json = Column(Text)  # 成长值来源权重
    benefits_json = Column(Text)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("hotel_id", "level_code", name="uk_mkt_level"),)


# ============================================================================
class MktStoredValuePlan(Base):
    """储值档位。"""

    __tablename__ = "mkt_stored_value_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    tier_name = Column(String(64))
    recharge_amt = Column(Numeric(10, 2), nullable=False)
    bonus_amt = Column(Numeric(10, 2), default=0)
    bonus_type = Column(String(16), default="amount")  # amount/percent
    gift_points = Column(Integer, default=0)
    first_time_only = Column(Boolean, default=False)
    payment_methods_json = Column(Text)  # ["wechat","alipay","card","cash"]
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


# ============================================================================
class MktGuestWallet(Base):
    """私域 H5 会员资产（与 PMS 全局 vip_level / 积分隔离）。"""

    __tablename__ = "mkt_guest_wallets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    level_code = Column(String(16), default="silver")
    points_balance = Column(Integer, default=0)
    stored_balance = Column(Numeric(12, 2), default=0)
    nights_ytd = Column(Integer, default=0)
    spend_ytd = Column(Numeric(12, 2), default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "guest_id", name="uk_mkt_guest_wallet"),)


# ============================================================================
class MktAutomation(Base):
    """营销自动化触发器。"""

    __tablename__ = "mkt_automations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    trigger_type = Column(String(32), nullable=False)  # birthday/checkin_pre/stay_post
    trigger_json = Column(Text)
    action_type = Column(String(32), default="send_coupon")  # send_coupon/send_msg/add_tag/create_task
    action_json = Column(Text)
    frequency_cap_days = Column(Integer, default=30)
    is_enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
