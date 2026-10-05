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

"""hk 域 ORM 模型。"""
from hk.hk_status import TERMINAL as _HK_TERMINAL

# 行为方法（State 模式 + 充血模型）
from hk.hk_status import HKStatus as _HKStatus  # noqa: E402
from models._types import Base, Column, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func


class HousekeepingTask(Base):
    __tablename__ = "housekeeping_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"))
    task_type = Column(String(30))
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    priority = Column(SmallInteger, default=3)
    # open / assigned / in_progress / pending_inspect / rework / done / ignored
    status = Column(String(20), default="open")
    due_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    done_at = Column(DateTime)
    inspect_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    inspect_at = Column(DateTime)
    fail_reason = Column(String(200))
    fail_count = Column(SmallInteger, default=0)

    # ----------------------------------------------------------------
    # 充血模型：状态判定 + 行为方法不再散落在 service 函数体里。
    # ----------------------------------------------------------------

    @property
    def _status(self) -> "_HKStatus":
        return _HKStatus(self.status or "open")

    def can_start(self) -> bool:
        """open / assigned / rework 状态可被开始清洁。"""
        return self._status in (_HKStatus.OPEN, _HKStatus.ASSIGNED, _HKStatus.REWORK)

    def can_finish_clean(self) -> bool:
        """in_progress / assigned / open / rework 状态可标记清洁完成。"""
        return self._status in (
            _HKStatus.IN_PROGRESS,
            _HKStatus.ASSIGNED,
            _HKStatus.OPEN,
            _HKStatus.REWORK,
        )

    def can_inspect(self) -> bool:
        """pending_inspect / in_progress 可被查房验收。"""
        return self._status in (_HKStatus.PENDING_INSPECT, _HKStatus.IN_PROGRESS)

    def is_terminal(self) -> bool:
        return self._status in _HK_TERMINAL

    def can_transition_to(self, dst: str) -> bool:
        from hk.hk_status import can_transition as _can

        try:
            return _can(self._status, _HKStatus(dst))
        except ValueError:
            return False

    def transition_to(self, dst: str, *, force: bool = False) -> None:
        """唯一合法 HK 状态写入入口（对齐 Room/Order）。"""
        try:
            dest = _HKStatus(dst)
        except ValueError as e:
            raise InvalidStateError(f"未知工单状态「{dst}」") from e
        if self.status == dest.value and not force:
            return
        if not force and not self.can_transition_to(dest.value):
            raise InvalidStateError(
                f"工单不可从「{self.status}」变为「{dest.value}」",
            )
        self.status = dest.value

    def mark_assigned(self) -> None:
        if self.status == _HKStatus.ASSIGNED.value:
            return
        if self.status in (_HKStatus.OPEN.value, _HKStatus.REWORK.value):
            self.transition_to(_HKStatus.ASSIGNED.value)
        elif self._status not in (
            _HKStatus.ASSIGNED,
            _HKStatus.IN_PROGRESS,
            _HKStatus.PENDING_INSPECT,
        ):
            raise InvalidStateError(f"当前状态「{self.status}」不可改派为 assigned")

    def mark_ignored(self) -> None:
        self.transition_to(_HKStatus.IGNORED.value)

    def mark_done(self) -> None:
        self.transition_to(_HKStatus.DONE.value)

    def mark_rework(self) -> None:
        self.transition_to(_HKStatus.REWORK.value)

    def mark_in_progress(self) -> None:
        """开始清洁；状态进入 in_progress。终态拒绝。"""
        if self.is_terminal():
            raise InvalidStateError(f"当前状态「{self.status}」不可开始清洁")
        if not self.can_start():
            raise InvalidStateError(f"当前状态「{self.status}」不可开始清洁")
        self.transition_to(_HKStatus.IN_PROGRESS.value)

    def mark_pending_inspect(self) -> None:
        """清洁完成进入待查房。"""
        if not self.can_finish_clean():
            raise InvalidStateError(f"当前状态「{self.status}」不可完成清洁")
        self.transition_to(_HKStatus.PENDING_INSPECT.value)


# ============================================================================
class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"))
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="SET NULL"))
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"))
    content = Column(String(255))
    priority = Column(SmallInteger, default=3)
    status = Column(String(20), default="open")
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)

    def assign(self, assignee_id: int | None = None) -> None:
        if assignee_id is not None:
            self.assignee_id = assignee_id
        if self.status in ("open", "assigned", None, ""):
            self.status = "assigned" if self.assignee_id else "open"

    def resolve(self) -> None:
        from datetime import datetime as _dt

        if self.status in ("done", "closed", "resolved"):
            return
        self.status = "done"
        self.resolved_at = _dt.now()

    def reopen(self) -> None:
        self.status = "open"
        self.resolved_at = None


# ============================================================================
class StaffShift(Base):
    __tablename__ = "staff_shifts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shift_date = Column(Date, nullable=False)
    shift = Column(String(20))
    handover_note = Column(Text)
    # auto=系统铺班 / manual=主管手改 / ai=AI 建议写入（不覆盖 manual）
    source = Column(String(20), default="auto")
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class StaffRosterTemplate(Base):
    """周循环排班模板。payload: [{user_id, shifts: [7 codes]}]。"""

    __tablename__ = "staff_roster_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(80), default="默认周模板")
    payload_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ============================================================================
class StaffShiftRequest(Base):
    """请假 / 换班申请。排班页审批后写回 StaffShift。"""

    __tablename__ = "staff_shift_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), default="leave")  # leave / swap
    shift_date = Column(Date, nullable=False)
    from_shift = Column(String(20))
    to_shift = Column(String(20))
    swap_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(String(20), default="pending")  # pending / approved / rejected
    note = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
