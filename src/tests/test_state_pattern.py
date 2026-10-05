# SPDX-License-Identifier: Apache-2.0
"""State 模式 + 充血模型：enum + 模型 can_xxx / xxx() 方法的纯单测。

运行: pytest src/tests/test_state_pattern.py -v

用例清单
--------
  ST-S01  OrderStatus enum 6 个状态 + 值字符串
  ST-S02  OrderStatus ALLOWED_TRANSITIONS 闭合（终态无出边）
  ST-S03  Order.can_checkin / can_cancel / can_checkout / can_assign_room 判定
  ST-S04  Order.cancel(reason) 修改 status；终态抛 400；已 cancelled 幂等
  ST-S04b Order.confirm / checkin / checkout / mark_no_show + transition_to
  ST-S05  HKStatus enum 7 个状态 + TERMINAL 集合
  ST-S06  HKStatus ALLOWED_TRANSITIONS 闭合
  ST-S07  HKTask.can_start / can_finish_clean / can_inspect / is_terminal
  ST-S08  HKTask.mark_in_progress / mark_pending_inspect 终态拒绝
  ST-S09  RoomStatus enum 7 个状态 + LEGACY_MAP 覆盖
  ST-S10  Room.normalize 对枚举值 / 大写 / 老字符串都归一
  ST-S11  Room.can_transition_to：OCC → OOO 拒绝；OCC → VD 允许
  ST-S12  Room.transition_to 就地改 status；非法跳变抛 400
"""

from __future__ import annotations

import sys
import unittest

from domain import BusinessError  # noqa: F401
from domain.order_status import ALLOWED_TRANSITIONS, OrderStatus, all_statuses
from hk.hk_status import (
    ALLOWED_TRANSITIONS as HK_ALLOWED,
)
from hk.hk_status import (
    HK_OPENISH,
    HK_OPENISH_ACTIVE,
    HKStatus,
)
from hk.hk_status import (
    TERMINAL as HK_TERMINAL,
)
from rooms.room_status_machine import (
    ALLOWED_TRANSITIONS as ROOM_ALLOWED,
)
from rooms.room_status_machine import (
    CHECKIN_OK,
    LEGACY_MAP,
    SELLABLE,
    STATUS_CN,
    RoomStatus,
    can_transition,
    label,
    normalize,
)
from rooms.room_status_machine import (
    can_checkin as _can_checkin_status,
)
from rooms.room_status_machine import (
    is_sellable as _is_sellable_status,
)


class OrderStatePatternTests(unittest.TestCase):
    """OrderStatus enum + Order model 充血方法。"""

    def test_s01_enum_six_statuses(self):
        """ST-S01：OrderStatus 6 个标准状态。"""
        self.assertEqual(len(OrderStatus), 6)
        self.assertEqual(all_statuses(), ["pending", "confirmed", "checked_in", "checked_out", "cancelled", "no_show"])

    def test_s02_terminal_states(self):
        """ST-S02：终态（checked_out/cancelled/no_show）无出边。"""
        terminal = {OrderStatus.CHECKED_OUT, OrderStatus.CANCELLED, OrderStatus.NO_SHOW}
        for st in terminal:
            self.assertEqual(ALLOWED_TRANSITIONS[st], frozenset())
        # 非终态必须能走出去
        self.assertGreater(len(ALLOWED_TRANSITIONS[OrderStatus.PENDING]), 0)

    def test_s03_can_xxx_judgement(self):
        """ST-S03：Order.can_xxx 判定（不依赖 DB，纯 in-memory 模型）。"""
        from models import Order

        o = Order(status="pending")
        self.assertTrue(o.can_checkin())
        self.assertTrue(o.can_cancel())
        self.assertFalse(o.can_checkout())
        self.assertTrue(o.can_assign_room())

        o.status = "confirmed"
        self.assertTrue(o.can_checkin())
        self.assertFalse(o.can_checkout())

        o.status = "checked_in"
        self.assertFalse(o.can_checkin())
        self.assertTrue(o.can_checkout())
        self.assertFalse(o.can_cancel())
        self.assertTrue(o.can_assign_room())

        o.status = "checked_out"
        self.assertFalse(o.can_cancel())
        self.assertFalse(o.can_assign_room())
        self.assertFalse(o.can_checkout())

        o.status = "cancelled"
        self.assertFalse(o.can_cancel())
        self.assertFalse(o.can_assign_room())

        o_ns = Order(status="no_show")
        self.assertFalse(o_ns.can_cancel())
        self.assertFalse(o_ns.can_assign_room())
        self.assertFalse(o_ns.can_mark_no_show())

        # 旧值兼容：DB 里可能存"VAC"/"vacant"等——_status property 兜底
        o_none = Order(status=None)
        self.assertTrue(o_none.can_checkin())  # 视作 pending

    def test_s04_cancel_method(self):
        """ST-S04：Order.cancel 修改 status；终态抛 400；已 cancelled 幂等。"""
        from models import Order

        o = Order(status="pending", note="VIP")
        o.cancel(reason="客户来电")
        self.assertEqual(o.status, "cancelled")
        self.assertIn("取消：客户来电", o.note)

        # 幂等：再次 cancel 不报错
        o.cancel(reason="再调一次")
        self.assertEqual(o.status, "cancelled")

        # 终态拒绝
        o_ci = Order(status="checked_in")
        with self.assertRaises(BusinessError) as ctx:
            o_ci.cancel(reason="强行取消")
        self.assertEqual(ctx.exception.http_status, 400)

    def test_s04b_transition_helpers(self):
        """ST-S04b：confirm / checkin / checkout / mark_no_show + 非法跳变。"""
        from models import Order

        o = Order(status="pending")
        o.confirm()
        self.assertEqual(o.status, "confirmed")
        o.confirm()  # 幂等
        self.assertEqual(o.status, "confirmed")

        o.checkin()
        self.assertEqual(o.status, "checked_in")
        o.checkin()  # 幂等
        self.assertEqual(o.status, "checked_in")

        o.checkout()
        self.assertEqual(o.status, "checked_out")
        with self.assertRaises(BusinessError) as ctx:
            o.cancel()
        self.assertEqual(ctx.exception.http_status, 400)

        o2 = Order(status="pending")
        o2.mark_no_show(reason="未到店")
        self.assertEqual(o2.status, "no_show")
        self.assertIn("No-show：未到店", o2.note or "")
        o2.mark_no_show()  # 幂等

        o3 = Order(status="checked_in")
        with self.assertRaises(BusinessError):
            o3.transition_to("cancelled")
        with self.assertRaises(BusinessError):
            o3.confirm()
        with self.assertRaises(BusinessError):
            o3.mark_no_show()


class GroupLineAndCheckinStateTests(unittest.TestCase):
    """PmsGroupRoomLine / PmsCheckin 状态机。"""

    def test_group_line_transitions(self):
        from models import PmsGroupRoomLine

        line = PmsGroupRoomLine(status="held")
        self.assertTrue(line.can_assign())
        line.assign()
        self.assertEqual(line.status, "assigned")
        line.checkin()
        self.assertEqual(line.status, "checked_in")
        line.checkout()
        self.assertEqual(line.status, "checked_out")
        line.cancel()  # noop
        self.assertEqual(line.status, "checked_out")

        line2 = PmsGroupRoomLine(status="held")
        line2.cancel()
        self.assertEqual(line2.status, "cancelled")
        with self.assertRaises(BusinessError):
            line2.assign()

    def test_checkin_checkout(self):
        from models import PmsCheckin

        ci = PmsCheckin(status="inhouse")
        self.assertTrue(ci.can_checkout())
        ci.checkout()
        self.assertEqual(ci.status, "checked_out")
        ci.checkout()  # 幂等
        with self.assertRaises(BusinessError):
            ci.transfer()

        ci2 = PmsCheckin(status="inhouse")
        ci2.transfer()
        self.assertEqual(ci2.status, "transferred")


class HKStatePatternTests(unittest.TestCase):
    """HKStatus enum + HKTask model 充血方法。"""

    def test_s05_enum_seven_statuses(self):
        """ST-S05：HKStatus 7 个状态 + TERMINAL = {done, ignored}。"""
        self.assertEqual(len(HKStatus), 7)
        self.assertEqual(HK_TERMINAL, frozenset({HKStatus.DONE, HKStatus.IGNORED}))

    def test_s06_terminal_closed(self):
        """ST-S06：终态无出边。"""
        for st in HK_TERMINAL:
            self.assertEqual(HK_ALLOWED[st], frozenset())

    def test_s07_can_xxx_judgement(self):
        """ST-S07：HKTask.can_xxx 判定。"""
        from models import HousekeepingTask

        for st, expected_can_start in (
            ("open", True),
            ("assigned", True),
            ("in_progress", False),  # can_start 要求 open/assigned/rework
            ("pending_inspect", False),
            ("rework", True),
            ("done", False),
            ("ignored", False),
        ):
            t = HousekeepingTask(status=st)
            self.assertEqual(t.can_start(), expected_can_start, f"status={st}")

        # can_finish_clean: in_progress/assigned/open/rework
        for st, expected in (
            ("open", True),
            ("assigned", True),
            ("in_progress", True),
            ("rework", True),
            ("pending_inspect", False),
            ("done", False),
        ):
            t = HousekeepingTask(status=st)
            self.assertEqual(t.can_finish_clean(), expected, f"can_finish_clean status={st}")

        # can_inspect: pending_inspect / in_progress
        for st, expected in (
            ("pending_inspect", True),
            ("in_progress", True),
            ("open", False),
            ("done", False),
            ("ignored", False),
        ):
            t = HousekeepingTask(status=st)
            self.assertEqual(t.can_inspect(), expected, f"can_inspect status={st}")

        # is_terminal: done / ignored
        self.assertTrue(HousekeepingTask(status="done").is_terminal())
        self.assertTrue(HousekeepingTask(status="ignored").is_terminal())
        self.assertFalse(HousekeepingTask(status="open").is_terminal())

    def test_s08_mark_methods(self):
        """ST-S08：HKTask.mark_in_progress / mark_pending_inspect 终态拒绝。"""
        from fastapi import HTTPException

        from models import HousekeepingTask

        # 正常路径
        t = HousekeepingTask(status="open")
        t.mark_in_progress()
        self.assertEqual(t.status, "in_progress")

        t2 = HousekeepingTask(status="in_progress")
        t2.mark_pending_inspect()
        self.assertEqual(t2.status, "pending_inspect")

        # 终态拒绝
        t_done = HousekeepingTask(status="done")
        with self.assertRaises(BusinessError) as ctx:
            t_done.mark_in_progress()
        self.assertEqual(ctx.exception.http_status, 400)

        # 非法状态拒绝
        t_pending = HousekeepingTask(status="pending_inspect")
        with self.assertRaises(BusinessError) as ctx:
            t_pending.mark_in_progress()
        self.assertEqual(ctx.exception.http_status, 400)


class RoomStatePatternTests(unittest.TestCase):
    """RoomStatus enum + Room model 充血方法。"""

    def test_s09_enum_seven_and_legacy_map(self):
        """ST-S09：RoomStatus 7 个状态 + LEGACY_MAP 覆盖。"""
        self.assertEqual(len(RoomStatus), 7)
        # LEGACY_MAP 应覆盖旧值（含大小写变体）
        for old, std in [("vacant", "VC"), ("dirty", "VD"), ("VAC", "VC"), ("ooo", "OOO")]:
            self.assertEqual(LEGACY_MAP.get(old), std, f"LEGACY_MAP[{old}]")

    def test_s10_normalize_all_forms(self):
        """ST-S10：normalize 对枚举值 / 大写 / 老字符串 / None 都归一。"""
        # 枚举值
        self.assertEqual(normalize("VC"), "VC")
        self.assertEqual(normalize("VD"), "VD")
        # 老字符串（小写）
        self.assertEqual(normalize("vacant"), "VC")
        self.assertEqual(normalize("dirty"), "VD")
        self.assertEqual(normalize("occupied"), "OCC")
        # 大写变体
        self.assertEqual(normalize("VAC"), "VC")
        self.assertEqual(normalize("OCC"), "OCC")
        # None / 空
        self.assertEqual(normalize(None), "VC")
        self.assertEqual(normalize(""), "VC")

    def test_s11_can_transition_to(self):
        """ST-S11：OCC → OOO 拒绝；OCC → VD 允许。"""
        from models import Room

        r_vc = Room(status="VC")
        self.assertTrue(r_vc.can_transition_to("VD"))
        self.assertTrue(r_vc.can_transition_to("OCC"))
        self.assertTrue(r_vc.can_transition_to("OOO"))

        r_occ = Room(status="OCC")
        self.assertFalse(r_occ.can_transition_to("OOO"), "OCC 不可直跳 OOO")
        self.assertTrue(r_occ.can_transition_to("VD"))
        self.assertTrue(r_occ.can_transition_to("DO"))

        r_done = Room(status="DO")
        self.assertTrue(r_done.can_transition_to("VD"))
        self.assertFalse(r_done.can_transition_to("OOO"))

        # can_checkin / is_sellable
        r_vc2 = Room(status="VC")
        self.assertTrue(r_vc2.can_checkin())
        self.assertTrue(r_vc2.is_sellable())

        r_ea = Room(status="EA")
        self.assertTrue(r_ea.can_checkin())
        self.assertFalse(r_ea.is_sellable())

        r_occ2 = Room(status="OCC")
        self.assertFalse(r_occ2.can_checkin())
        self.assertFalse(r_occ2.is_sellable())

    def test_s12_transition_to(self):
        """ST-S12：Room.transition_to 就地改 status；非法跳变抛 400。"""
        from fastapi import HTTPException

        from models import Room

        r = Room(status="VC")
        r.transition_to("VD", reason="清洁完成")
        self.assertEqual(r.status, "VD")

        # 非法跳变
        r_occ = Room(status="OCC")
        with self.assertRaises(BusinessError) as ctx:
            r_occ.transition_to("OOO")
        self.assertEqual(ctx.exception.http_status, 400)

        # 同状态 noop（顺带纠正大小写）
        r_vc = Room(status="vacant")
        r_vc.transition_to("VC")
        self.assertEqual(r_vc.status, "VC")


class HKOpenishConsistencyTests(unittest.TestCase):
    """HK_OPENISH / HK_OPENISH_ACTIVE 两个集合的语义区分。"""

    def test_openish_includes_ignored(self):
        """HK_OPENISH 用于"房间是否有未完成工单"，含 ignored。"""
        self.assertIn(HKStatus.IGNORED, HK_OPENISH)

    def test_openish_active_excludes_ignored(self):
        """HK_OPENISH_ACTIVE 用于"班次未完成"，排除 ignored。"""
        self.assertNotIn(HKStatus.IGNORED, HK_OPENISH_ACTIVE)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(OrderStatePatternTests))
    suite.addTests(loader.loadTestsFromTestCase(HKStatePatternTests))
    suite.addTests(loader.loadTestsFromTestCase(RoomStatePatternTests))
    suite.addTests(loader.loadTestsFromTestCase(HKOpenishConsistencyTests))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("\n" + "=" * 60)
    print(
        f"合计: {result.testsRun}  "
        f"通过: {result.testsRun - len(result.failures) - len(result.errors)}  "
        f"失败: {len(result.failures)}  "
        f"跳过: {len(result.skipped)}"
    )
    print("=" * 60)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
