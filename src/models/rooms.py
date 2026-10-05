# SPDX-License-Identifier: Apache-2.0
from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)

"""rooms 域 ORM 模型。"""
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
from rooms.room_status_machine import (
    CHECKIN_OK as _CHECKIN_OK,
)
from rooms.room_status_machine import (
    SELLABLE as _SELLABLE,
)
from rooms.room_status_machine import (
    STATUS_CN as _STATUS_CN,
)

# 行为方法（State 模式 + 充血模型）
from rooms.room_status_machine import (  # noqa: E402
    RoomStatus as _RoomStatus,
)
from rooms.room_status_machine import (
    can_transition as _can_transition,
)
from rooms.room_status_machine import (
    normalize as _normalize,
)


class RoomType(Base):
    __tablename__ = "room_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(40), nullable=False)
    name = Column(String(80), nullable=False)
    bed_type = Column(String(30))
    capacity = Column(SmallInteger)
    area = Column(Integer)  # 面积 m²
    amenities = Column(Text)  # JSON 数组，如 ["含早","淋浴"]
    base_price = Column(Numeric(10, 2), nullable=False, default=0)
    breakfast_included = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text)  # 卖点文案
    image_url = Column(String(500))  # 房型图 URL
    has_window = Column(Boolean, default=True)  # 是否有窗
    orientation = Column(String(40))  # 朝向，如南向
    __table_args__ = (UniqueConstraint("hotel_id", "code", name="uq_roomtype_hotel_code"),)


# ============================================================================
class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    room_no = Column(String(20), nullable=False)
    building = Column(String(20))
    floor = Column(SmallInteger)
    status = Column(String(20), nullable=False, default="vacant")
    status_note = Column(String(200))  # 维修/锁房原因
    status_until = Column(Date)  # 预计修复/解锁日期
    smoking = Column(Boolean, default=False)  # True=可吸烟；False=无烟
    features = Column(String(200))  # 特征标签，逗号分隔：加床/景观等
    lock_id = Column(String(60))  # 门锁设备 ID（预留对接智能门锁）
    # 物理可用性：normal=正常 maintenance=维修 oos=停用（与当日房态 status 分离）
    physical_status = Column(String(20), default="normal")
    __table_args__ = (UniqueConstraint("hotel_id", "room_no", name="uq_room_hotel_no"),)

    # ----------------------------------------------------------------
    # 充血模型：房态判定与转换方法不再散落在 rooms/room_status.py 函数体里。
    # ----------------------------------------------------------------

    @property
    def _status(self) -> "_RoomStatus":
        """标准化的房态；外部任意写法（vacant/dirty/VC）都映射到标准码。"""
        return _RoomStatus(_normalize(self.status))

    def can_transition_to(self, dst: str) -> bool:
        """判断 self → dst 转换是否合法（带旧值映射）。"""
        return _can_transition(self._status, _RoomStatus(_normalize(dst)))

    def can_checkin(self) -> bool:
        return self._status in _CHECKIN_OK

    def is_sellable(self) -> bool:
        return self._status in _SELLABLE

    def status_label(self) -> str:
        from infra.i18n import t

        msgid = _STATUS_CN.get(self._status.value, str(self.status or "—"))
        return t(msgid) if msgid else "—"

    def transition_to(self, dst: str, *, reason: str = "", operator_id: int | None = None) -> None:
        """就地修改 self.status；非法跳变抛 400。

        同状态视为 noop（顺手把 status 标准化为 RoomStatus 的值）。
        调用方负责 commit + 写 RoomStatusLog。
        """

        dst_norm = _normalize(dst)
        # 同状态 noop（即便 current status 是 "vacant" / dst "VC"，目标都是 VC）
        if self._status.value == dst_norm:
            self.status = dst_norm  # 顺带纠正遗留大小写
            return
        if not self.can_transition_to(dst_norm):
            from infra.i18n import t

            dst_label = t(_STATUS_CN.get(dst_norm, dst))
            raise InvalidStateError(
                t(
                    "房态不可从 {src}({src_code}) 变为 {dst}({dst_code})",
                    src=self.status_label(),
                    src_code=self.status,
                    dst=dst_label,
                    dst_code=dst_norm,
                ),
            )
        self.status = dst_norm


# ============================================================================
class RoomStatusLog(Base):
    __tablename__ = "room_status_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(20))
    to_status = Column(String(20))
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reason = Column(String(120))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RoomTypeBaseRate(Base):
    __tablename__ = "room_type_base_rate"
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    base_rate = Column(Numeric(10, 2), nullable=False)
    bar_upper = Column(Numeric(10, 2), nullable=False)
    bar_lower = Column(Numeric(10, 2), nullable=False)
    n_floor = Column(Numeric(10, 2), nullable=False)
    seasonal_modifier = Column(Text)
    effective_from = Column(Date)
    effective_to = Column(Date)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================================
class RoomNightInventory(Base):
    """按日×房间库存快照：available / sold / blocked。"""

    __tablename__ = "room_night_inventory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    biz_date = Column(Date, nullable=False)
    # available=可售 sold=已售 blocked=停用/维修
    status = Column(String(20), nullable=False, default="available")
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    guest_name = Column(String(80))
    order_no = Column(String(40))
    check_in = Column(Date)
    check_out = Column(Date)
    # reservation | room_status | order_hold | ooo
    source = Column(String(30), default="derived")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "room_id", "biz_date", name="uq_room_night"),)


# ============================================================================
class RoomInspection(Base):
    """AI 视觉质检 / 移动查房记录。"""

    __tablename__ = "room_inspections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    room_no = Column(String(20))
    inspector = Column(String(80))
    status = Column(String(20), default="pending")  # pending / passed / failed
    score = Column(Integer, default=0)  # 0-100
    summary = Column(String(255))
    findings_json = Column(Text)  # [{label,desc,ok,confidence,box:{t,l,w,h}}]
    inspected_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class RoomIotMetric(Base):
    """客房楼层 IoT 时序指标（能耗 / 温度 / 湿度），供健康监测趋势图。"""

    __tablename__ = "room_iot_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    floor = Column(String(20), default="3F")
    recorded_at = Column(DateTime, nullable=False)
    energy_kw = Column(Numeric(10, 2))  # 瞬时功率 kW
    temp_c = Column(Numeric(6, 1))  # 温度 ℃
    humidity_pct = Column(Numeric(6, 1))  # 相对湿度 %
