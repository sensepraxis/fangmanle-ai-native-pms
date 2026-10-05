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

"""orders 域 ORM 模型。"""
from domain.checkin_status import (
    CheckinStatus as _CheckinStatus,
)  # noqa: E402
from domain.checkin_status import (
    can_transition as _checkin_can_transition,
)
from domain.group_line_status import (
    GroupLineStatus as _GroupLineStatus,
)  # noqa: E402
from domain.group_line_status import (
    can_transition as _group_line_can_transition,
)

# 行为方法（State 模式 + 充血模型）—— 见类内部 can_xxx / xxx() 方法。
# 依赖 OrderStatus enum 必须在 Order 类定义之前 import。
from domain.order_status import (
    OrderStatus as _OrderStatus,
)  # noqa: E402
from domain.order_status import (
    can_transition as _order_can_transition,
)
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


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), nullable=False, unique=True)
    name = Column(String(80), nullable=False)
    type = Column(String(30))
    commission_rate = Column(Numeric(5, 4), default=0)
    is_active = Column(Boolean, default=True)
    # OTA 佣金配置扩展（系统设置 · 渠道档案）
    settle_cycle = Column(String(16))  # T+1 / T+7 / 月结 / 实时
    note = Column(String(255))
    owner_role = Column(String(32), default="老板/财务")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(32))


# ============================================================================
class ChannelContract(Base):
    __tablename__ = "channel_contracts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False)
    contract_price = Column(Numeric(10, 2))
    valid_from = Column(Date)
    valid_to = Column(Date)
    __table_args__ = (UniqueConstraint("hotel_id", "channel_id", "room_type_id", name="uq_channel_contract"),)


# ============================================================================
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_no = Column(String(40), nullable=False, unique=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="SET NULL"))
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    # —— 设计文档扩展 ——
    order_type = Column(SmallInteger, default=1)  # 1散客 2OTA 3协议 4长住 5团队
    agreement_id = Column(Integer, ForeignKey("corp_accounts.id", ondelete="SET NULL"))
    rate_strategy = Column(String(20), default="daily")  # daily / monthly / agreement
    one_id = Column(String(64))  # 冗余 OneID，便于列表检索
    guest_phone = Column(String(20))  # 冗余手机号
    deposit_amount = Column(Numeric(12, 2), default=0)
    allow_on_account = Column(Boolean, default=False)
    credit_occupy = Column(Numeric(12, 2), default=0)  # 占用协议授信
    # 长住专属
    longstay_cycle = Column(String(20))  # monthly / quarterly / yearly
    monthly_rent = Column(Numeric(12, 2))
    longstay_start = Column(Date)
    longstay_end = Column(Date)
    skip_daily_room_charge = Column(Boolean, default=False)  # 长住：夜审不跑日房费
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    nights = Column(SmallInteger)
    rooms = Column(SmallInteger, default=1)
    adults = Column(SmallInteger, default=1)
    children = Column(SmallInteger, default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    status = Column(String(20), nullable=False, default="pending")
    payment_status = Column(String(20), default="unpaid")
    # 预计/实际到店时刻，如 "14:30"（与日历按日联动，时刻供前台接待）
    arrival_time = Column(String(5))
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    note = Column(Text)
    external_order_no = Column(String(80))
    voucher_code = Column(String(80))
    channel_prepaid = Column(Boolean, default=False)  # OTA 渠道已预付房费
    group_name = Column(String(120))  # 团体名称（order_type=5）
    group_type = Column(String(40))  # 旅游团 / 企业团 / 会议 / 其他
    settle_mode = Column(String(40), default="unified")  # unified=统一结账
    settle_party = Column(String(120))  # 结算单位
    sales_name = Column(String(80))  # 销售
    other_amount = Column(Numeric(12, 2), default=0)  # 餐饮/会议等
    created_at = Column(DateTime, server_default=func.now())

    # ----------------------------------------------------------------
    # 充血模型：业务规则与方法不再散落在 service 函数体里。
    # ----------------------------------------------------------------

    @property
    def _status(self) -> "_OrderStatus":
        try:
            return _OrderStatus(self.status or "pending")
        except ValueError:
            return _OrderStatus.PENDING

    def can_transition_to(self, dst: str) -> bool:
        """判断 self → dst 是否在 ALLOWED_TRANSITIONS 内。"""
        try:
            dst_st = _OrderStatus(dst)
        except ValueError:
            return False
        return _order_can_transition(self._status, dst_st)

    def can_checkin(self) -> bool:
        """pending / confirmed 状态可办理入住。"""
        return self._status in (_OrderStatus.PENDING, _OrderStatus.CONFIRMED)

    def can_confirm(self) -> bool:
        """仅 pending 可确认（已 confirmed 视为可幂等）。"""
        return self._status in (_OrderStatus.PENDING, _OrderStatus.CONFIRMED)

    def can_cancel(self) -> bool:
        """在住 / 终态不可取消。"""
        return self._status not in (
            _OrderStatus.CHECKED_IN,
            _OrderStatus.CHECKED_OUT,
            _OrderStatus.CANCELLED,
            _OrderStatus.NO_SHOW,
        )

    def can_checkout(self) -> bool:
        """仅 checked_in 可退房。"""
        return self._status == _OrderStatus.CHECKED_IN

    def can_mark_no_show(self) -> bool:
        """仅预抵（pending/confirmed）可标 No-show。"""
        return self._status in (_OrderStatus.PENDING, _OrderStatus.CONFIRMED)

    def can_assign_room(self) -> bool:
        """未取消 / 未退房 / 未 No-show 的单可预分房。"""
        return self._status not in (
            _OrderStatus.CHECKED_OUT,
            _OrderStatus.CANCELLED,
            _OrderStatus.NO_SHOW,
        )

    def transition_to(self, dst: str, *, reason: str = "") -> None:
        """通用状态转移；非法跳变抛 InvalidStateError；同状态幂等。"""
        try:
            dst_st = _OrderStatus(dst)
        except ValueError as e:
            raise InvalidStateError(f"未知订单状态「{dst}」") from e
        if self._status == dst_st:
            self.status = dst_st.value
            return
        if not _order_can_transition(self._status, dst_st):
            raise InvalidStateError(f"订单状态不可从「{self.status}」变为「{dst_st.value}」")
        self.status = dst_st.value

    def confirm(self) -> None:
        """pending → confirmed；已 confirmed 幂等。"""
        if self._status == _OrderStatus.CONFIRMED:
            return
        if self._status != _OrderStatus.PENDING:
            raise InvalidStateError(f"当前状态「{self.status}」不可确认")
        self.transition_to(_OrderStatus.CONFIRMED.value)

    def checkin(self) -> None:
        """pending/confirmed → checked_in；已入住幂等。"""
        if self._status == _OrderStatus.CHECKED_IN:
            return
        if not self.can_checkin():
            raise InvalidStateError(f"当前状态「{self.status}」不可办理入住")
        self.transition_to(_OrderStatus.CHECKED_IN.value)

    def checkout(self) -> None:
        """checked_in → checked_out；已退房幂等。"""
        if self._status == _OrderStatus.CHECKED_OUT:
            return
        if not self.can_checkout():
            raise InvalidStateError("仅在住订单可退房")
        self.transition_to(_OrderStatus.CHECKED_OUT.value)

    def mark_no_show(self, reason: str = "") -> None:
        """pending/confirmed → no_show；已 no_show 幂等。"""
        if self._status == _OrderStatus.NO_SHOW:
            return
        if not self.can_mark_no_show():
            raise InvalidStateError("仅预抵订单可标记 No-show")
        self.transition_to(_OrderStatus.NO_SHOW.value)
        if reason:
            self.note = ((self.note or "") + f"\nNo-show：{reason}")[-500:]

    def cancel(self, reason: str = "") -> None:
        """取消订单；幂等（已 cancelled 直接返回）；终态抛 400。"""
        if self._status == _OrderStatus.CANCELLED:
            return
        if not self.can_cancel():
            raise InvalidStateError(f"当前状态「{self.status}」不可取消")
        self.transition_to(_OrderStatus.CANCELLED.value)
        if reason:
            self.note = ((self.note or "") + f" · 取消：{reason}").strip(" ·")


# ============================================================================
class PmsGroupRoomBlock(Base):
    """团体房量块：按房型汇总数量与单价。"""

    __tablename__ = "pms_group_room_blocks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    qty = Column(SmallInteger, default=1)
    unit_price = Column(Numeric(10, 2), default=0)  # 单价/间/晚
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PmsGroupRoomLine(Base):
    """团体分房清单：一间一行，支持预分房 / 逐间入住。"""

    __tablename__ = "pms_group_room_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    line_no = Column(SmallInteger, default=1)
    room_type_id = Column(Integer, ForeignKey("room_types.id", ondelete="SET NULL"))
    guest_name = Column(String(80))
    guest_phone = Column(String(30))
    id_last4 = Column(String(8))  # 证件后四位（用，非完整证件）
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    checkin_id = Column(Integer, ForeignKey("pms_checkins.id", ondelete="SET NULL"))
    stay_check_in = Column(Date)  # 可覆盖主单入离
    stay_check_out = Column(Date)
    # held=待分房 assigned=已预分 checked_in=在住 checked_out=已退 cancelled=取消
    status = Column(String(20), default="held")
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())

    @property
    def _status(self) -> "_GroupLineStatus":
        try:
            return _GroupLineStatus(self.status or "held")
        except ValueError:
            return _GroupLineStatus.HELD

    def can_transition_to(self, dst: str) -> bool:
        try:
            return _group_line_can_transition(self._status, _GroupLineStatus(dst))
        except ValueError:
            return False

    def can_assign(self) -> bool:
        return self._status in (_GroupLineStatus.HELD, _GroupLineStatus.ASSIGNED)

    def can_checkin(self) -> bool:
        return self._status in (_GroupLineStatus.HELD, _GroupLineStatus.ASSIGNED)

    def can_checkout(self) -> bool:
        return self._status == _GroupLineStatus.CHECKED_IN

    def can_cancel(self) -> bool:
        return self._status not in (
            _GroupLineStatus.CHECKED_OUT,
            _GroupLineStatus.CANCELLED,
        )

    def transition_to(self, dst: str) -> None:
        try:
            dst_st = _GroupLineStatus(dst)
        except ValueError as e:
            raise InvalidStateError(f"未知团体行状态「{dst}」") from e
        if self._status == dst_st:
            self.status = dst_st.value
            return
        if not _group_line_can_transition(self._status, dst_st):
            raise InvalidStateError(f"团体行状态不可从「{self.status}」变为「{dst_st.value}」")
        self.status = dst_st.value

    def assign(self) -> None:
        if self._status == _GroupLineStatus.ASSIGNED:
            return
        if not self.can_assign():
            raise InvalidStateError(f"团体行状态「{self.status}」不可预分房")
        self.transition_to(_GroupLineStatus.ASSIGNED.value)

    def checkin(self) -> None:
        if self._status == _GroupLineStatus.CHECKED_IN:
            return
        if not self.can_checkin():
            raise InvalidStateError(f"团体行状态「{self.status}」不可入住")
        self.transition_to(_GroupLineStatus.CHECKED_IN.value)

    def checkout(self) -> None:
        if self._status == _GroupLineStatus.CHECKED_OUT:
            return
        if not self.can_checkout():
            raise InvalidStateError(f"团体行状态「{self.status}」不可退房")
        self.transition_to(_GroupLineStatus.CHECKED_OUT.value)

    def cancel(self) -> None:
        if self._status == _GroupLineStatus.CANCELLED:
            return
        if self._status == _GroupLineStatus.CHECKED_OUT:
            return  # 已退房行取消视为 noop
        self.transition_to(_GroupLineStatus.CANCELLED.value)


# ============================================================================
class OrderItem(Base):
    """预订行项目（报价快照）；真实账务以 pms_folio_entries 为准。"""

    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(30))
    description = Column(String(120))
    qty = Column(Numeric(8, 2), default=1)
    unit_price = Column(Numeric(10, 2))
    amount = Column(Numeric(12, 2))


# ============================================================================
class Reservation(Base):
    """预分房占房（订单侧可空）；权威实体房在 pms_checkins。"""

    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PmsRoomAssignment(Base):
    """分房/换房审计历史：预分、入住分房、换房、释放。"""

    __tablename__ = "pms_room_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    checkin_id = Column(Integer, ForeignKey("pms_checkins.id", ondelete="SET NULL"))
    from_room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    to_room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    # pre_assign | checkin | change | release
    assign_type = Column(String(20), nullable=False, default="pre_assign")
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reason = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PmsCheckin(Base):
    """入住登记表 pms_checkin：订单转入住后生成；支持换房/续住/联房。

    证件号只存本表（不进 orders）：密文 + 脱敏掩码 + 哈希；不存人像。
    """

    __tablename__ = "pms_checkins"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="SET NULL"))
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    guest_name = Column(String(80))  # 本次入住人姓名快照（可与订单主客不同）
    status = Column(String(20), default="inhouse")  # inhouse / checked_out / transferred
    actual_checkin_at = Column(DateTime)
    actual_checkout_at = Column(DateTime)
    id_doc_type = Column(String(20))  # id_card / passport / other
    id_doc_cipher = Column(Text)  # 字段级加密密文
    id_doc_mask = Column(String(40))  # 列表/导出默认脱敏
    id_doc_hash = Column(String(64))  # 查重用不可逆哈希
    id_doc_no = Column(String(40))  # 遗留明文列，migrate 后应清空
    face_registered = Column(Boolean, default=False)  # 仅标记，不存人像
    floor = Column(SmallInteger)
    room_no = Column(String(20))
    master_checkin_id = Column(Integer, ForeignKey("pms_checkins.id", ondelete="SET NULL"))  # 联房主
    created_at = Column(DateTime, server_default=func.now())

    @property
    def _status(self) -> "_CheckinStatus":
        try:
            return _CheckinStatus(self.status or "inhouse")
        except ValueError:
            return _CheckinStatus.INHOUSE

    def can_transition_to(self, dst: str) -> bool:
        try:
            return _checkin_can_transition(self._status, _CheckinStatus(dst))
        except ValueError:
            return False

    def can_checkout(self) -> bool:
        return self._status == _CheckinStatus.INHOUSE

    def transition_to(self, dst: str) -> None:
        try:
            dst_st = _CheckinStatus(dst)
        except ValueError as e:
            raise InvalidStateError(f"未知入住登记状态「{dst}」") from e
        if self._status == dst_st:
            self.status = dst_st.value
            return
        if not _checkin_can_transition(self._status, dst_st):
            raise InvalidStateError(f"入住登记状态不可从「{self.status}」变为「{dst_st.value}」")
        self.status = dst_st.value

    def checkout(self) -> None:
        """inhouse → checked_out；已退房幂等。"""
        if self._status == _CheckinStatus.CHECKED_OUT:
            return
        if not self.can_checkout():
            raise InvalidStateError(f"入住登记状态「{self.status}」不可退房")
        self.transition_to(_CheckinStatus.CHECKED_OUT.value)

    def transfer(self) -> None:
        """inhouse → transferred（换房转移）。"""
        if self._status == _CheckinStatus.TRANSFERRED:
            return
        if self._status != _CheckinStatus.INHOUSE:
            raise InvalidStateError(f"入住登记状态「{self.status}」不可转移")
        self.transition_to(_CheckinStatus.TRANSFERRED.value)


# ============================================================================
class PmsIdDocAudit(Base):
    """查看完整证件号的不可删审计日志（留存 ≥6 个月；不随入住登记级联删除）。"""

    __tablename__ = "pms_id_doc_audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    # SET NULL：入住记录清理后审计仍保留
    checkin_id = Column(Integer, ForeignKey("pms_checkins.id", ondelete="SET NULL"))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(40), default="reveal")  # reveal / export_blocked / purge
    reason = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PmsFolio(Base):
    """账单主表 pms_folio：每一条入住对应一个独立账本。"""

    __tablename__ = "pms_folios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    folio_no = Column(String(40), nullable=False, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    checkin_id = Column(Integer, ForeignKey("pms_checkins.id", ondelete="SET NULL"))
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    status = Column(String(20), default="open")  # open / partial / closed
    balance = Column(Numeric(12, 2), default=0)  # 应收余额（收费 - 已收）
    charge_total = Column(Numeric(12, 2), default=0)
    payment_total = Column(Numeric(12, 2), default=0)
    opened_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime)

    def open_folio(self) -> None:
        self.status = "open"
        self.closed_at = None

    def sync_status_from_totals(self) -> None:
        """按 charge/payment/balance 同步 open|partial|closed。"""
        from domain.folio_status import derive_status

        self.status = derive_status(balance=self.balance, payment_total=self.payment_total)
        if self.status == "closed" and self.closed_at is None:
            from datetime import datetime as _dt

            self.closed_at = _dt.now()
        if self.status != "closed":
            self.closed_at = None

    def close(self) -> None:
        from datetime import datetime as _dt

        self.status = "closed"
        self.closed_at = _dt.now()


# ============================================================================
class PmsFolioEntry(Base):
    """账单分录：房费 / 杂费 / 押金 / 退款 / 调账。"""

    __tablename__ = "pms_folio_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    folio_id = Column(Integer, ForeignKey("pms_folios.id", ondelete="CASCADE"), nullable=False)
    entry_type = Column(String(30), nullable=False)
    # room_charge / misc / deposit / refund / adjustment / ar_charge
    biz_date = Column(Date)
    description = Column(String(160))
    amount = Column(Numeric(12, 2), nullable=False, default=0)  # 正=应收，负=冲减/退
    qty = Column(Numeric(8, 2), default=1)
    unit_price = Column(Numeric(10, 2))
    source = Column(String(30), default="manual")  # night_audit / monthly / manual / system
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class PmsArLedger(Base):
    """AR 应收账表 pms_ar：协议单位挂账主档（一企业一账）。"""

    __tablename__ = "pms_ar_ledgers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    corp_id = Column(Integer, ForeignKey("corp_accounts.id", ondelete="CASCADE"), nullable=False)
    charged_total = Column(Numeric(14, 2), default=0)
    settled_total = Column(Numeric(14, 2), default=0)
    balance = Column(Numeric(14, 2), default=0)
    credit_limit = Column(Numeric(14, 2), default=0)
    credit_used = Column(Numeric(14, 2), default=0)
    settle_cycle = Column(String(20), default="monthly")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("hotel_id", "corp_id", name="uq_ar_hotel_corp"),)


# ============================================================================
class PmsArEntry(Base):
    """AR 明细：挂账 / 对公核销。"""

    __tablename__ = "pms_ar_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ar_ledger_id = Column(Integer, ForeignKey("pms_ar_ledgers.id", ondelete="CASCADE"), nullable=False)
    entry_type = Column(String(20), nullable=False)  # charge / settle / write_off
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    folio_id = Column(Integer, ForeignKey("pms_folios.id", ondelete="SET NULL"))
    amount = Column(Numeric(12, 2), nullable=False)
    ref_no = Column(String(80))  # 对公打款单号 / 内部参考
    note = Column(Text)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class ChannelAttribution(Base):
    __tablename__ = "channel_attribution"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    source = Column(String(30))
    attributed_rev = Column(Numeric(12, 2))
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class HotelChannelBinding(Base):
    """酒店 ↔ 外部渠道账户绑定（Webhook 路由、OAuth 等）。"""

    __tablename__ = "hotel_channel_bindings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30), default="xiaohongshu", nullable=False)
    label = Column(String(120))
    xhs_ad_account_id = Column(String(80))
    xhs_professional_id = Column(String(80))
    xhs_page_ids = Column(String(255))
    binding_token = Column(String(64), nullable=False, unique=True)
    webhook_secret = Column(String(128))
    status = Column(String(20), default="active")  # active / disabled
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
