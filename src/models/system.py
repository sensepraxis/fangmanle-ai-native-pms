# SPDX-License-Identifier: Apache-2.0
"""system 域 ORM 模型。"""

from models._types import Base, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func


class WebhookEventLog(Base):
    """外部 Webhook 原始事件日志（对账、重放、排错）。"""

    __tablename__ = "webhook_event_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="SET NULL"))
    binding_id = Column(Integer, ForeignKey("hotel_channel_bindings.id", ondelete="SET NULL"))
    channel = Column(String(30), default="xiaohongshu")
    external_event_id = Column(String(120))
    payload_json = Column(Text)
    status = Column(String(20), default="received")  # received / processed / duplicate / unmapped / error
    error_message = Column(String(255))
    lead_id = Column(Integer, ForeignKey("acquisition_leads.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Venue(Base):
    __tablename__ = "venues"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    capacity = Column(Integer)
    hourly_rate = Column(Numeric(10, 2))


# ============================================================================
class VenueBooking(Base):
    __tablename__ = "venue_bookings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    event_name = Column(String(120))
    event_date = Column(Date)
    attendees = Column(Integer)
    amount = Column(Numeric(12, 2))
    status = Column(String(20), default="booked")


# ============================================================================
class AppSetting(Base):
    """系统级键值配置（JSON）。"""

    __tablename__ = "app_settings"
    key = Column(String(80), primary_key=True)
    value_json = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
