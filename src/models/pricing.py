# SPDX-License-Identifier: Apache-2.0
"""pricing 域 ORM 模型。"""

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


class RateStrategy(Base):
    __tablename__ = "rate_strategies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(80))
    min_floor_price = Column(Numeric(10, 2))
    max_ceiling_price = Column(Numeric(10, 2))
    auto_cruise = Column(Boolean, default=False)
    effective_from = Column(Date)
    effective_to = Column(Date)
    is_active = Column(Boolean, default=True)


# ============================================================================
class PriceSuggestion(Base):
    __tablename__ = "price_suggestions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    current_price = Column(Numeric(10, 2))
    suggested_price = Column(Numeric(10, 2))
    confidence = Column(String(10))
    status = Column(String(20), default="pending")
    guardrail_msg = Column(String(200))
    model_version = Column(String(40))
    created_at = Column(DateTime, server_default=func.now())
    decided_at = Column(DateTime)


# ============================================================================
class PricingAssistantConfig(Base):
    """酒店级执行模式与佣金配置。"""

    __tablename__ = "pricing_assistant_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, unique=True)
    # shadow / assisted / delegated
    execution_mode = Column(String(16), default="assisted")
    delegated_enabled = Column(Boolean, default=False)
    commission_json = Column(Text)  # {"ota_ctrip":0.15,"ota_meituan":0.16,"direct":0.015,"member":0}
    # 竞品对比开关（§3.8.2 双模式）
    comp_compare_enabled = Column(Boolean, default=False)
    # L0-L5 定价参数快照（§5.9）
    params_json = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class PricingRecommendation(Base):
    __tablename__ = "pricing_recommendation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reco_id = Column(String(48), unique=True, nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(32), nullable=False, default="direct")
    stay_date = Column(Date, nullable=False)
    current_price = Column(Numeric(10, 2))
    suggested_price = Column(Numeric(10, 2), nullable=False)
    suggested_base = Column(Numeric(10, 2), nullable=False)
    est_n = Column(Numeric(10, 2))
    est_occ_pct = Column(Numeric(5, 2))
    est_revpar_delta = Column(Numeric(10, 2))
    confidence = Column(String(8))
    top_reasons = Column(Text)  # JSON list
    features_snapshot = Column(Text)  # JSON
    explain_json = Column(Text)  # §5.7 算法推导快照（含 params / fair_price_band）
    execution_mode = Column(String(16))
    # pending / accepted / rejected / ignored / auto_executed / expired / blocked
    status = Column(String(16), default="pending")
    snapshot_hash = Column(String(64))
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)


# ============================================================================
class PricingDecision(Base):
    __tablename__ = "pricing_decision"
    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(48), unique=True, nullable=False)
    reco_id = Column(String(48), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    # accept / reject / ignore / auto_execute
    decision = Column(String(16), nullable=False)
    decided_by = Column(String(32))
    decided_at = Column(DateTime)
    before_price = Column(Numeric(10, 2))
    after_price = Column(Numeric(10, 2))
    reason_note = Column(String(255))
    audit_id = Column(String(48))


# ============================================================================
class PricingEffect(Base):
    __tablename__ = "pricing_effect"
    id = Column(Integer, primary_key=True, autoincrement=True)
    effect_id = Column(String(48), unique=True, nullable=False)
    decision_id = Column(String(48), nullable=False)
    reco_id = Column(String(48), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    stay_date = Column(Date, nullable=False)
    metric = Column(String(32))
    baseline_value = Column(Numeric(10, 2))
    actual_value = Column(Numeric(10, 2))
    delta_pct = Column(Numeric(5, 2))
    recorded_at = Column(DateTime, server_default=func.now())


# ============================================================================
class CompetitorSet(Base):
    __tablename__ = "competitor_set"
    id = Column(Integer, primary_key=True, autoincrement=True)
    set_id = Column(String(48), unique=True, nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    set_name = Column(String(64))
    segment_tag = Column(String(32))
    default_radius_km = Column(Numeric(5, 2), default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class CompetitorProperty(Base):
    __tablename__ = "competitor_property"
    id = Column(Integer, primary_key=True, autoincrement=True)
    comp_id = Column(String(48), unique=True, nullable=False)
    set_id = Column(String(48), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    comp_name = Column(String(128))
    comp_lat = Column(Numeric(10, 6))
    comp_lng = Column(Numeric(10, 6))
    address = Column(String(255))
    star_rating = Column(SmallInteger)
    review_score = Column(Numeric(3, 1))
    distance_km = Column(Numeric(5, 2))
    # rate_shopping / manual / public_scrape
    data_source = Column(String(32), default="manual")
    source_ref = Column(String(64))
    ota_public_url = Column(String(255))
    is_active = Column(Boolean, default=True)


# ============================================================================
class CompetitorRateSnapshot(Base):
    __tablename__ = "competitor_rate_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(64), unique=True, nullable=False)
    comp_id = Column(String(48), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    stay_date = Column(Date, nullable=False)
    room_type_eq = Column(String(64))
    channel = Column(String(32), default="ota_ctrip")
    observed_price = Column(Numeric(10, 2))
    observed_currency = Column(String(8), default="CNY")
    rate_plan_code = Column(String(64), default="BAR")
    captured_at = Column(DateTime, server_default=func.now())


# ============================================================================
class CompetitorRoomMap(Base):
    __tablename__ = "competitor_room_map"
    id = Column(Integer, primary_key=True, autoincrement=True)
    map_id = Column(String(64), unique=True, nullable=False)
    comp_id = Column(String(48), nullable=False)
    self_room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    comp_room_type_raw = Column(String(64))
    weight = Column(Numeric(4, 3), default=1.000)  # 可比性权重 0.1~1.0
    is_active = Column(Boolean, default=True)
    mapped_by = Column(String(32))
    mapped_at = Column(DateTime, server_default=func.now())


# ============================================================================
class EventCalendar(Base):
    __tablename__ = "event_calendar"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(48), unique=True, nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"))
    # holiday / concert / exhibition / sport / school / self / other
    event_type = Column(String(32))
    event_name = Column(String(128))
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    distance_km = Column(Numeric(5, 2))
    intensity = Column(String(8))  # 弱 / 中 / 强 / 爆
    heat_score = Column(Numeric(5, 2))  # 事件热度分 0-100（可运营覆盖）
    price_uplift_max = Column(Numeric(5, 2), default=1.00)  # 活动因子硬上限，默认 +100%
    source = Column(String(32), default="manual")
    source_ref = Column(String(64))
    venue_address = Column(String(255))  # 活动地点（手工）
    venue_lat = Column(Numeric(10, 6))
    venue_lng = Column(Numeric(10, 6))
    note = Column(String(255))
    is_active = Column(Boolean, default=True)  # 是否纳入定价影响


# ============================================================================
class ParityAlert(Base):
    __tablename__ = "parity_alert"
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(48), unique=True, nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel_a = Column(String(32), nullable=False)
    channel_b = Column(String(32), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    stay_date = Column(Date, nullable=False)
    price_a = Column(Numeric(10, 2))
    price_b = Column(Numeric(10, 2))
    delta_pct = Column(Numeric(5, 2))
    duration_hours = Column(Integer)
    # red / yellow / blue
    severity = Column(String(8))
    # open / resolved / ignored
    status = Column(String(16), default="open")
    alert_type = Column(String(32), default="parity")
    title = Column(String(255))
    detail = Column(Text)
    suggested_action = Column(Text)
    detected_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PaceSnapshot(Base):
    __tablename__ = "pace_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pace_id = Column(String(64), unique=True, nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    stay_date = Column(Date, nullable=False)
    booked = Column(Integer)
    expected = Column(Integer)
    pace_ratio = Column(Numeric(5, 2))
    captured_at = Column(DateTime, server_default=func.now())


# ============================================================================
class InventoryAllocation(Base):
    __tablename__ = "inventory_allocation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    allotment = Column(Integer, default=0)
    sold = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("hotel_id", "room_type_id", "channel_id", "biz_date", name="uq_allocation"),)
