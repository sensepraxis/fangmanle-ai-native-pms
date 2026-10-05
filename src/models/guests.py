# SPDX-License-Identifier: Apache-2.0
"""guests 域 ORM 模型。"""

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


class Guest(Base):
    __tablename__ = "guests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    one_id = Column(String(40), nullable=False, unique=True)
    name = Column(String(80), nullable=False)
    phone = Column(String(20))  # 默认只存脱敏或空；明文不落地
    phone_cipher = Column(Text)  # 字段级加密密文
    phone_mask = Column(String(20))  # 列表/导出默认脱敏
    phone_hash = Column(String(64))  # 查重/归并用不可逆哈希
    gender = Column(String(10))
    birthday = Column(Date)
    vip_level = Column(String(20), default="normal")
    city = Column(String(60))
    ltv = Column(Numeric(12, 2), default=0)
    churn_risk = Column(Numeric(3, 2))
    merged_into_guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class GuestAlias(Base):
    """客人曾用名 / 其他名字（同号归并、渠道昵称等）。"""

    __tablename__ = "guest_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    alias_name = Column(String(80), nullable=False)
    source = Column(String(40), default="merge")  # merge / ota / wecom / manual
    merged_from_guest_id = Column(Integer)
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("guest_id", "alias_name", name="uq_guest_alias"),)


# ============================================================================
class GuestIdentity(Base):
    __tablename__ = "guest_identities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(30), nullable=False)
    external_id = Column(String(120))
    confidence = Column(Numeric(3, 2))
    linked_at = Column(DateTime, server_default=func.now())
    is_primary = Column(Boolean, default=False)
    merge_method = Column(String(30))
    matched_by = Column(String(60))
    __table_args__ = (UniqueConstraint("guest_id", "source", "external_id", name="uq_guest_identity"),)


# ============================================================================
class OneIdMergeEvent(Base):
    __tablename__ = "oneid_merge_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(30), nullable=False)
    source = Column(String(30))
    external_id = Column(String(120))
    confidence = Column(Numeric(3, 2))
    merge_method = Column(String(30))
    operator = Column(String(60))
    note = Column(Text)
    occurred_at = Column(DateTime, nullable=False)


# ============================================================================
class TagDefinition(Base):
    __tablename__ = "tag_definitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(40), nullable=False, unique=True)
    name = Column(String(80), nullable=False)
    category = Column(String(40))
    rule_expr = Column(Text)
    is_active = Column(Boolean, default=True)


# ============================================================================
class GuestTag(Base):
    __tablename__ = "guest_tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tag_definitions.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Numeric(3, 2))
    source = Column(String(30))
    assigned_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("guest_id", "tag_id", name="uq_guest_tag"),)


# ============================================================================
class CrmTask(Base):
    """客户运营任务：召回 / 关怀 / 发券占位。"""

    __tablename__ = "crm_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    segment_id = Column(Integer, ForeignKey("segments.id", ondelete="SET NULL"))
    task_type = Column(String(30), default="recall")
    status = Column(String(20), default="open")
    title = Column(String(200))
    payload_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    done_at = Column(DateTime)


# ============================================================================
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"))
    rating = Column(Numeric(2, 1))
    content = Column(Text)
    replied = Column(Boolean, default=False)
    reply_content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class OneIdPhoneConflict(Base):
    """H5 手机号归集冲突：全号重复或多后六位命中时待人工裁定。"""

    __tablename__ = "oneid_phone_conflicts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")  # pending / resolved / dismissed
    phone_submitted = Column(String(30), nullable=False)
    phone_last4 = Column(String(6), nullable=False)  # 实际存储手机后六位，用于 OneID 归集匹配
    match_type = Column(String(40), default="phone_last6_multi")  # phone_exact_multi / phone_last6_multi
    external_userid = Column(String(120), nullable=False)
    nickname = Column(String(80))
    follow_userid = Column(String(80))
    bind_ticket_id = Column(Integer, ForeignKey("wecom_bind_tickets.id", ondelete="SET NULL"))
    candidate_guest_ids_json = Column(Text, nullable=False)  # JSON list[int]
    resolved_guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    resolved_by = Column(String(60))
    note = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
