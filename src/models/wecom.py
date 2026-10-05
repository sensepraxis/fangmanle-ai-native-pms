# SPDX-License-Identifier: Apache-2.0
"""wecom 域 ORM 模型。"""

from models._types import Base, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func


class WecomMsgTask(Base):
    """企微一对一消息任务：PMS 创建 → 员工企微确认 → 客人微信收到。"""

    __tablename__ = "wecom_msg_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    external_userid = Column(String(120), nullable=False)
    sender_userid = Column(String(80), nullable=False)
    content = Column(Text, nullable=False)
    msgid = Column(String(120))
    fail_list_json = Column(Text)
    status = Column(String(30), default="pending_confirm")  # pending_confirm / submitted / failed
    error_message = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class WecomBindTicket(Base):
    """扫码加好友后的绑定票据：欢迎语链接 → 客人填手机 → OneID 归集。"""

    __tablename__ = "wecom_bind_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    external_userid = Column(String(120), nullable=False)
    follow_userid = Column(String(80))
    nickname = Column(String(80))
    state = Column(String(64))  # lobby / g:123 …
    status = Column(String(20), default="pending")  # pending / bound / expired
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    phone_submitted = Column(String(30))
    welcome_sent = Column(Boolean, default=False)
    welcome_mode = Column(String(30))  # welcome_code / msg_template / link_only
    error_message = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    bound_at = Column(DateTime)
    expires_at = Column(DateTime)


# ============================================================================
class WecomCallbackEvent(Base):
    """企微回调收件箱：先落库再异步处理，避免回调超时/高并发阻塞。"""

    __tablename__ = "wecom_callback_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(String(60))
    external_userid = Column(String(120))
    follow_userid = Column(String(80))
    state = Column(String(64))
    welcome_code = Column(String(128))
    raw_json = Column(Text)
    status = Column(String(20), default="pending")  # pending / processing / done / failed
    error_message = Column(String(255))
    is_deleted = Column(Boolean, default=False)  # 处理完成后逻辑删除，保留审计
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime)


# ============================================================================
class WxLandingPage(Base):
    """领券落地页 / 会员中心页（装修器输出）。"""

    __tablename__ = "wx_landing_pages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    page_key = Column(String(64), nullable=False)
    title = Column(String(128))
    template_id = Column(String(48))
    page_role = Column(String(16), default="claim")  # claim | member | returning
    blocks_json = Column(Text)  # 编辑区工作稿
    # 线上快照：仅「发布 / 更新发布」时写入；客人 H5 读这套
    published_blocks_json = Column(Text)
    published_title = Column(String(128))
    published_coupon_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="SET NULL"))
    coupon_id = Column(Integer, ForeignKey("mkt_coupons.id", ondelete="SET NULL"))
    status = Column(String(16), default="draft")  # draft/published
    published_url = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(32))
    __table_args__ = (UniqueConstraint("hotel_id", "page_key", name="uk_wx_landing_key"),)


# ============================================================================
class WxLandingTemplate(Base):
    """落地页系统模板。"""

    __tablename__ = "wx_landing_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_key = Column(String(48), unique=True, nullable=False)
    name = Column(String(64), nullable=False)
    category = Column(String(32))
    thumbnail = Column(String(255))
    blocks_json = Column(Text)
    is_system = Column(Boolean, default=True)
