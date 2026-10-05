# SPDX-License-Identifier: Apache-2.0
"""
房满乐 PMS —— 假数据种子（用，真实可替换）。
生成 1 家酒店 + 全模块示例数据。运行: python seed.py [--reset]
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import random
from datetime import date, datetime, timedelta

from bootstrap.ensure_assets import ensure_asset_schema
from bootstrap.ensure_supplies import ensure_supplies_schema
from bootstrap.migrations.alter_to_single_hotel import ensure_local_users, ensure_single_hotel_schema
from database import SessionLocal, engine
from infra.auth_local import hash_password
from models import (
    AiCommand,
    Asset,
    AssetAlert,
    AssetAuditItem,
    AssetEvent,
    AssetInsight,
    AssetMaintenance,
    Base,
    Campaign,
    Channel,
    ChannelAttribution,
    ChannelContract,
    DamageTicket,
    DemandForecast,
    FinanceReport,
    Guest,
    GuestIdentity,
    GuestTag,
    Hotel,
    HousekeepingTask,
    InventoryAllocation,
    Invoice,
    LedgerEntry,
    Linen,
    LinenSnapshot,
    NightAuditException,
    NightAuditLog,
    Order,
    OrderItem,
    Payment,
    PriceSuggestion,
    ProfitInsight,
    RateStrategy,
    ReconBatch,
    ReconItem,
    Reservation,
    RestockItem,
    RestockOrder,
    RevenueAnomaly,
    Review,
    RiskAlert,
    Role,
    Room,
    RoomInspection,
    RoomIotMetric,
    RoomStatusLog,
    RoomType,
    Segment,
    SegmentMember,
    ServiceRequest,
    StaffShift,
    StaffShiftRequest,
    StockMovement,
    Supply,
    SupplyAlert,
    SupplyCategory,
    SupplyInsight,
    SupplyRequisition,
    TagDefinition,
    TaxFiling,
    User,
    Venue,
    VenueBooking,
)

random.seed(20260812)
TODAY = date.today()

from seed import _common as _seed_common


def enrich_housekeeping_demo(db, hotels):
    """房务作业台数据：刷新房态分布、清扫任务、客需、当日排班与保洁员（可反复执行）。"""
    from seed.locale_pack import get_pack

    pack = get_pack()
    HK_NAMES = list(pack.HK_NAMES)
    roles = {r.code: r for r in db.query(Role).all()}
    if "hk" not in roles:
        r = Role(code="hk", name=pack.HK_ROLE_NAME)
        db.add(r)
        db.flush()
        roles["hk"] = r
    for h in hotels:
        staff_users = []
        for suffix, fn in HK_NAMES:
            uname = f"{suffix}-h{h.id}"
            u = db.query(User).filter_by(username=uname).first()
            if not u:
                u = User(
                    hotel_id=h.id, role_id=roles["hk"].id, username=uname, full_name=fn, phone=_seed_common.phone()
                )
                db.add(u)
                db.flush()
            else:
                u.full_name = fn
                u.hotel_id = h.id
            staff_users.append(u)
        rooms = db.query(Room).filter_by(hotel_id=h.id).order_by(Room.room_no).all()
        if not rooms:
            continue
        for i, rm in enumerate(rooms[:44]):
            if i < 20:
                rm.status = "dirty"
            elif i < 32:
                rm.status = "cleaning"
            elif i < 40:
                rm.status = "vacant"
            else:
                rm.status = "ooo"
        db.query(HousekeepingTask).filter_by(hotel_id=h.id).delete()
        dirty_like = [r for r in rooms if r.status in ("dirty", "cleaning", "vacant", "ooo")]
        task_pool = dirty_like[:28] if dirty_like else rooms[:28]
        for i, rm in enumerate(task_pool):
            if rm.status == "ooo":
                tt = "inspect"
            elif rm.status == "vacant":
                tt = "inspect"
            elif rm.status == "cleaning":
                tt = "clean"
            else:
                tt = "clean"
            st = (
                "in_progress"
                if rm.status == "cleaning"
                else "done"
                if i % 7 == 0
                else random.choice(["open", "assigned", "in_progress"])
            )
            created = datetime.now() - timedelta(minutes=random.randint(20, 180))
            done_at = created + timedelta(minutes=random.randint(25, 45)) if st == "done" else None
            db.add(
                HousekeepingTask(
                    hotel_id=h.id,
                    room_id=rm.id,
                    task_type=tt,
                    assignee_id=staff_users[i % len(staff_users)].id,
                    priority=1 if i < 4 else random.randint(2, 5),
                    status=st,
                    due_at=datetime.now() + timedelta(hours=random.randint(1, 4)),
                    created_at=created,
                    done_at=done_at,
                )
            )
        db.query(ServiceRequest).filter_by(hotel_id=h.id).delete()
        week0 = TODAY - timedelta(days=TODAY.weekday())
        week1 = week0 + timedelta(days=6)
        db.query(StaffShift).filter(
            StaffShift.hotel_id == h.id, StaffShift.shift_date >= week0, StaffShift.shift_date <= week1
        ).delete(synchronize_session=False)
        shifts_cycle = ["morning", "morning", "afternoon", "afternoon", "night", "off", "morning"]
        for i, u in enumerate(staff_users):
            for d_off in range(7):
                d = week0 + timedelta(days=d_off)
                sh = shifts_cycle[(i + d_off) % len(shifts_cycle)]
                if d.weekday() >= 5 and sh == "night":
                    sh = "off" if i % 2 == 0 else "morning"
                db.add(StaffShift(hotel_id=h.id, user_id=u.id, shift_date=d, shift=sh, handover_note=None))
        db.query(StaffShiftRequest).filter_by(hotel_id=h.id).delete(synchronize_session=False)
        if staff_users:
            tomorrow = date.today() + timedelta(days=1)
            friday = week0 + timedelta(days=4)
            db.add(
                StaffShiftRequest(
                    hotel_id=h.id,
                    user_id=staff_users[-1].id,
                    kind="leave",
                    shift_date=tomorrow,
                    from_shift="morning",
                    to_shift="off",
                    status="pending",
                    note="请假申请",
                )
            )
            if len(staff_users) >= 2:
                db.add(
                    StaffShiftRequest(
                        hotel_id=h.id,
                        user_id=staff_users[0].id,
                        kind="swap",
                        shift_date=friday,
                        from_shift="morning",
                        to_shift="afternoon",
                        swap_user_id=staff_users[1].id,
                        status="pending",
                        note=f"与{staff_users[1].full_name}对调周五班次",
                    )
                )
    db.commit()
    print("Housekeeping workbench refreshed (room status / tasks / guest requests / weekly roster).")
    enrich_room_inspections(db, hotels)


def enrich_room_inspections(db, hotels):
    """AI 视觉质检记录：仅用结构化检测项标签，不写死叙事话术。"""
    import json

    CHECK_LABELS = ["床品", "毛巾", "地面", "垃圾桶", "镜面", "遥控器", "窗帘", "迷你吧"]
    inspectors = ["王阿姨", "李姐", "张师傅", "赵保洁", "陈大姐"]
    for h in hotels:
        db.query(RoomInspection).filter_by(hotel_id=h.id).delete()
        rooms = db.query(Room).filter_by(hotel_id=h.id).order_by(Room.room_no).all()
        if not rooms:
            continue
        for i, rm in enumerate(rooms[:12]):
            fail = i % 3 == 1
            findings = []
            for j, lab in enumerate(CHECK_LABELS[:4]):
                ok_item = not (fail and j == 1)
                findings.append(
                    {
                        "label": lab,
                        "desc": "合格" if ok_item else "不合格",
                        "ok": ok_item,
                        "confidence": 70 + i % 20,
                        "box": {"t": f"{20 + j * 12}%", "l": f"{15 + j * 10}%", "w": "28%", "h": "18%"},
                    }
                )
            db.add(
                RoomInspection(
                    hotel_id=h.id,
                    room_id=rm.id,
                    room_no=rm.room_no,
                    inspector=inspectors[i % len(inspectors)],
                    status="failed" if fail else "passed",
                    score=68 if fail else 92,
                    findings_json=json.dumps(findings, ensure_ascii=False),
                    summary="需返工" if fail else "通过",
                    inspected_at=datetime.now() - timedelta(hours=i),
                )
            )
    db.commit()
    print("Housekeeping visual QA refreshed (no narrative copy).")
