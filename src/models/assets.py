# SPDX-License-Identifier: Apache-2.0
"""assets 域 ORM 模型。"""

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


class SupplyCategory(Base):
    __tablename__ = "supply_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"))
    name = Column(String(80), nullable=False)
    parent_id = Column(Integer, ForeignKey("supply_categories.id", ondelete="SET NULL"))


# ============================================================================
class Supply(Base):
    __tablename__ = "supplies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("supply_categories.id", ondelete="SET NULL"))
    sku = Column(String(40))
    name = Column(String(120), nullable=False)
    unit = Column(String(20))
    safety_stock = Column(Numeric(10, 2), default=0)
    current_stock = Column(Numeric(10, 2), default=0)
    unit_cost = Column(Numeric(10, 2))
    __table_args__ = (UniqueConstraint("hotel_id", "sku", name="uq_supply_sku"),)


# ============================================================================
class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    supply_id = Column(Integer, ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    movement_type = Column(String(20))
    qty = Column(Numeric(10, 2))
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Linen(Base):
    __tablename__ = "linen"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    item_type = Column(String(40))
    status = Column(String(20), default="in_use")
    wash_count = Column(Integer, default=0)
    lifecycle_stage = Column(String(20))
    updated_at = Column(DateTime, server_default=func.now())


# ============================================================================
class Asset(Base):
    """设备设施台账（固定设备，非易耗物资）。"""

    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    asset_no = Column(String(40))  # 设备编号（店内唯一编码）
    category = Column(String(40))  # 暖通 / 客房设备 / 弱电 / 公区 / 电梯
    location = Column(String(80))
    room_no = Column(String(20))
    sn = Column(String(60))
    brand_model = Column(String(80))
    purchase_date = Column(Date)
    purchase_value = Column(Numeric(12, 2))
    current_value = Column(Numeric(12, 2))
    repair_cost_total = Column(Numeric(12, 2), default=0)
    health_score = Column(Integer)  # 0-100
    insight = Column(String(200))
    warranty_until = Column(Date)
    runtime_hours = Column(Integer)
    avg_power_w = Column(Numeric(10, 2))
    next_maintain_date = Column(Date)
    supplier = Column(String(80))
    dept = Column(String(40))
    status = Column(String(20), default="active")  # active / maintenance / retired / abnormal


# ============================================================================
class AssetMaintenance(Base):
    __tablename__ = "asset_maintenance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(40))
    due_date = Column(Date)
    status = Column(String(20), default="scheduled")  # scheduled / overdue / doing / done
    cost = Column(Numeric(10, 2))
    note = Column(String(200))
    owner = Column(String(40))
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AssetAlert(Base):
    """设备设施告警（健康/盘点/质保）。"""

    __tablename__ = "asset_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"))
    room_no = Column(String(20))
    floor = Column(String(20))
    asset_name = Column(String(120))
    alert_type = Column(String(20), default="health")  # health / audit / warranty / iot
    severity = Column(String(20), default="mid")  # low / mid / high
    message = Column(String(200))
    status = Column(String(20), default="open")  # open / ack / closed
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AssetInsight(Base):
    """设备设施 AI 洞察（维保/置换/ROI）。"""

    __tablename__ = "asset_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"))
    title = Column(String(120), nullable=False)
    recommendation = Column(String(300))
    impact_amount = Column(Numeric(12, 2), default=0)
    category = Column(String(20), default="maintain")  # maintain / replace / roi / health / audit
    status = Column(String(20), default="open")  # open / accepted / closed
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AssetEvent(Base):
    """单设备生命周期事件（采购/安装/维保/故障）。"""

    __tablename__ = "asset_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(40))  # purchase / install / maintain / repair / predict / retire
    title = Column(String(120), nullable=False)
    happened_at = Column(DateTime)
    note = Column(String(300))
    cost = Column(Numeric(10, 2))
    owner = Column(String(40))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class AssetAuditItem(Base):
    """设备/固定物品盘点差异行。"""

    __tablename__ = "asset_audit_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    name = Column(String(120), nullable=False)
    theoretical_qty = Column(Integer, default=0)
    actual_qty = Column(Integer, default=0)
    risk = Column(String(200))
    severity = Column(String(20), default="mid")
    status = Column(String(20), default="open")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class SupplyAlert(Base):
    """易耗/布草异常预警（楼层消耗、短缺）。"""

    __tablename__ = "supply_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    line = Column(String(20), default="amenity")  # linen / amenity
    room_no = Column(String(20))
    floor = Column(String(20))
    supply_name = Column(String(120))
    severity = Column(String(20), default="mid")  # low / mid / high
    message = Column(String(200))
    status = Column(String(20), default="open")  # open / ack / closed
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class LinenSnapshot(Base):
    """布草按日状态快照（周转看板）。"""

    __tablename__ = "linen_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    item_type = Column(String(40), nullable=False)
    in_room = Column(Integer, default=0)  # 在房
    pending_wash = Column(Integer, default=0)  # 待洗
    in_wash = Column(Integer, default=0)  # 洗涤中
    in_storage = Column(Integer, default=0)  # 仓储可用
    discarded = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("hotel_id", "biz_date", "item_type", name="uq_linen_snap"),)


# ============================================================================
class RestockOrder(Base):
    """易耗补货/采购单。"""

    __tablename__ = "restock_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_no = Column(String(40), unique=True)
    vendor = Column(String(80))
    status = Column(String(20), default="draft")  # draft / submitted / approved / received
    total_amount = Column(Numeric(12, 2), default=0)
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RestockItem(Base):
    __tablename__ = "restock_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("restock_orders.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    supply_id = Column(Integer, ForeignKey("supplies.id", ondelete="SET NULL"))
    name = Column(String(120))
    qty = Column(Numeric(10, 2), default=0)
    unit_cost = Column(Numeric(10, 2), default=0)
    amount = Column(Numeric(12, 2), default=0)
    urgency = Column(String(20), default="normal")  # normal / high / critical


# ============================================================================
class SupplyRequisition(Base):
    """易耗领用流水。"""

    __tablename__ = "supply_requisitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    supply_id = Column(Integer, ForeignKey("supplies.id", ondelete="SET NULL"))
    supply_name = Column(String(120))
    qty = Column(Numeric(10, 2), default=0)
    dept = Column(String(40))
    requester = Column(String(40))
    status = Column(String(20), default="issued")  # issued / returned / void
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class DamageTicket(Base):
    """报损单（布草寿命报废 / 易耗损坏 / 资产报损登记）。"""

    __tablename__ = "damage_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    line = Column(String(20), default="amenity")  # linen / amenity
    room_no = Column(String(20))
    item_name = Column(String(120))
    asset_category = Column(String(80))  # 家具/电器/布草/卫浴/五金…
    severity = Column(String(20), default="medium")  # low / medium / high
    description = Column(Text)  # 情况描述全文
    photos = Column(Text)  # JSON 数组，现场照片 URL
    ai_suggestion = Column(Text)
    ai_risk = Column(Text)
    ai_tags = Column(String(200))  # 逗号分隔标签
    fee = Column(Numeric(12, 2), default=0)
    status = Column(String(20), default="open")  # open / repairing / replaced / scrapped / closed
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)


# ============================================================================
class SupplyInsight(Base):
    """物资 AI 建议（布草周转 / 易耗补货 / 置换）。"""

    __tablename__ = "supply_insights"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    line = Column(String(20), default="linen")  # linen / amenity
    title = Column(String(120))
    recommendation = Column(Text)
    impact_amount = Column(Numeric(12, 2), default=0)
    category = Column(String(40))  # turnover / forecast / restock / loss / replace / rca
    status = Column(String(20), default="open")  # open / accepted / dismissed
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ShiftAssetCount(Base):
    """实物盘库：应有 vs 实盘。"""

    __tablename__ = "shift_asset_counts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    handover_id = Column(Integer, ForeignKey("shift_handovers.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(40), nullable=False)
    asset_name = Column(String(80), nullable=False)
    hint = Column(String(120))
    expected_qty = Column(Integer, default=0)
    actual_qty = Column(Integer)
    received_qty = Column(Integer)
    received_ack = Column(Boolean, default=False)
    diff_reason = Column(Text)
    supply_id = Column(Integer, ForeignKey("supplies.id", ondelete="SET NULL"))
    reorder_triggered = Column(Boolean, default=False)
