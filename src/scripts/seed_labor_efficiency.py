# SPDX-License-Identifier: Apache-2.0
"""为人效复盘补近两周真实样本（幂等：先清 SEED_PERF 标记再写入）。

覆盖：已完成清扫任务、查房、排班、预离订单（含未来几天以便预测条有缺口）。
不执行 --reset，不碰其它数据。
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta

from database import SessionLocal
from models import (
    Channel,
    Guest,
    Hotel,
    HousekeepingTask,
    Order,
    Room,
    RoomInspection,
    RoomType,
    StaffShift,
    User,
)

SEED_TAG = "SEED_PERF"
STAFF_USERNAMES = ("hk-a", "hk-b", "hk-c", "hk-d", "hk-e")


def _staff(db, hotel_id: int) -> list[User]:
    rows = (
        db.query(User)
        .filter(User.hotel_id == hotel_id, User.username.in_(STAFF_USERNAMES))
        .order_by(User.username)
        .all()
    )
    if len(rows) >= 3:
        return rows
    # 兜底：任意本店员工
    return db.query(User).filter(User.hotel_id == hotel_id).order_by(User.id).limit(5).all()


def _purge(db, hotel_id: int) -> None:
    # 旧种子任务：fail_reason 标记
    (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.hotel_id == hotel_id,
            HousekeepingTask.fail_reason == SEED_TAG,
        )
        .delete(synchronize_session=False)
    )
    (
        db.query(RoomInspection)
        .filter(
            RoomInspection.hotel_id == hotel_id,
            RoomInspection.summary.like(f"%{SEED_TAG}%"),
        )
        .delete(synchronize_session=False)
    )
    (
        db.query(Order)
        .filter(
            Order.hotel_id == hotel_id,
            Order.order_no.like("ORD-PERF-%"),
        )
        .delete(synchronize_session=False)
    )
    # 排班：仅清 source=SEED_PERF 的格子（若无该 source 则按日期区间重铺时用 upsert）
    (
        db.query(StaffShift)
        .filter(
            StaffShift.hotel_id == hotel_id,
            StaffShift.handover_note == SEED_TAG,
        )
        .delete(synchronize_session=False)
    )


def _ensure_shift(db, hotel_id: int, user_id: int, d: date, shift: str) -> None:
    row = db.query(StaffShift).filter_by(hotel_id=hotel_id, user_id=user_id, shift_date=d).first()
    if row:
        # 不覆盖 manual
        if (row.source or "") == "manual":
            return
        row.shift = shift
        row.handover_note = SEED_TAG
        row.source = "auto"
    else:
        db.add(
            StaffShift(
                hotel_id=hotel_id,
                user_id=user_id,
                shift_date=d,
                shift=shift,
                handover_note=SEED_TAG,
                source="auto",
            )
        )


def main() -> None:
    random.seed(20260830)
    db = SessionLocal()
    try:
        hotel = db.query(Hotel).order_by(Hotel.id.asc()).first()
        if not hotel:
            print("无酒店，请先启动 demo 种子库。")
            return
        hotel_id = hotel.id
        staff = _staff(db, hotel_id)
        if not staff:
            print("无客房员工账号（hk-a~hk-e）。")
            return
        rooms = db.query(Room).filter_by(hotel_id=hotel_id).order_by(Room.room_no).all()
        if not rooms:
            print("无房间。")
            return
        rt = db.query(RoomType).filter_by(hotel_id=hotel_id).order_by(RoomType.id).first()
        ch = db.query(Channel).first()
        guest = db.query(Guest).order_by(Guest.id).first()

        _purge(db, hotel_id)
        today = date.today()
        # 过去 14 天 + 未来 5 天
        past_days = 14
        future_days = 5

        # —— 排班：过去 14 天全覆盖；赵保洁连续高负荷日仍上班 ——
        # staff 顺序预期：王阿姨 hk-a, 李姐 hk-b, 张师傅 hk-c, 赵保洁 hk-d, 陈大姐 hk-e
        for off in range(past_days):
            d = today - timedelta(days=past_days - 1 - off)
            for i, u in enumerate(staff):
                nm = u.full_name or u.username
                # 每人每周约 1 天休；赵保洁近 3 天不休（制造高负荷预警）
                rest = (i + off) % 6 == 0
                if nm == "赵保洁" and off >= past_days - 3:
                    rest = False
                # 周一/二部分人休，制造个别空样本日仍有人力
                if d.weekday() == 0 and i >= 3:
                    rest = True
                sh = "off" if rest else ("morning" if i % 2 == 0 else "afternoon")
                _ensure_shift(db, hotel_id, u.id, d, sh)

        # 未来几天：周二（若落在区间）少排，制造缺口
        for fut in range(1, future_days + 1):
            d = today + timedelta(days=fut)
            for i, u in enumerate(staff):
                # 缺口日：仅留 1～2 人早班
                if d.weekday() == 1:  # 周二
                    sh = "morning" if i < 2 else "off"
                elif d.weekday() == 5:
                    sh = "off" if i % 2 else "morning"
                else:
                    sh = "morning" if i % 2 == 0 else "afternoon"
                    if (i + fut) % 5 == 0:
                        sh = "off"
                _ensure_shift(db, hotel_id, u.id, d, sh)

        # —— 预离订单：过去/未来每日若干间 ——
        seq = int(datetime.now().timestamp()) % 100000
        for off in range(-(past_days - 1), future_days + 1):
            d = today + timedelta(days=off)
            # 工作日预离多，周末少；缺口日（未来周二）特别多
            if d.weekday() == 1 and off > 0:
                n_orders = 14
            elif d.weekday() >= 5:
                n_orders = 4 + (abs(off) % 2)
            else:
                n_orders = 8 + (abs(off) % 4)
            for j in range(n_orders):
                ci = d - timedelta(days=1 + (j % 2))
                order_no = f"ORD-PERF-{d.strftime('%Y%m%d')}-{seq + abs(off) * 20 + j:04d}"
                status = "checked_in" if off >= 0 else "checked_out"
                if off > 0:
                    status = "confirmed"
                db.add(
                    Order(
                        hotel_id=hotel_id,
                        order_no=order_no,
                        guest_id=guest.id if guest else None,
                        channel_id=ch.id if ch else None,
                        room_type_id=rt.id if rt else None,
                        check_in=ci,
                        check_out=d,
                        nights=max(1, (d - ci).days),
                        rooms=1,
                        adults=1,
                        total_amount=680,
                        status=status,
                        payment_status="paid" if status == "checked_out" else "unpaid",
                        note=SEED_TAG,
                    )
                )

        # —— 已完成清扫：按人设画像，跳过少量「无样本日」——
        # 近 7 天内：周一、周四故意少样本（体现趋势图空位）
        # 时长画像（分钟）
        duration_profile = {
            "王阿姨": (24, 30),
            "李姐": (28, 34),
            "张师傅": (27, 33),
            "赵保洁": (32, 42),
            "陈大姐": (29, 36),
        }
        volume_profile = {
            "王阿姨": 3,
            "李姐": 4,
            "张师傅": 6,  # 完成最多
            "赵保洁": 5,  # 高负荷
            "陈大姐": 3,
        }

        task_n = 0
        for off in range(past_days):
            d = today - timedelta(days=past_days - 1 - off)
            # 近 7 天内：周一、周四几乎无完成单
            in_last7 = (today - d).days <= 6
            sparse = in_last7 and d.weekday() in (0, 3)  # 一、四

            for i, u in enumerate(staff):
                nm = u.full_name or u.username
                lo, hi = duration_profile.get(nm, (28, 36))
                base_vol = volume_profile.get(nm, 3)
                if sparse:
                    # 仅张师傅偶发 1 单，其它人空
                    if nm != "张师傅" or off % 2:
                        continue
                    n_tasks = 1
                else:
                    n_tasks = base_vol
                    # 赵保洁近 3 天加量 → >3h
                    if nm == "赵保洁" and off >= past_days - 3:
                        n_tasks = 7
                    # 周末略少
                    if d.weekday() >= 5:
                        n_tasks = max(1, n_tasks - 1)

                for k in range(n_tasks):
                    mins = random.randint(lo, hi)
                    # 王阿姨偶尔更快
                    if nm == "王阿姨" and k == 0:
                        mins = random.randint(24, 28)
                    hour = 9 + (k % 6)
                    minute = (k * 7 + i * 3) % 50
                    done_at = datetime(d.year, d.month, d.day, hour, minute, 0)
                    created_at = done_at - timedelta(minutes=mins)
                    rm = rooms[(task_n + k) % len(rooms)]
                    db.add(
                        HousekeepingTask(
                            hotel_id=hotel_id,
                            room_id=rm.id,
                            task_type="clean",
                            assignee_id=u.id,
                            priority=2 + (k % 3),
                            status="done",
                            due_at=done_at + timedelta(hours=1),
                            created_at=created_at,
                            done_at=done_at,
                            fail_reason=SEED_TAG,
                        )
                    )
                    task_n += 1

        # —— 查房：李姐通过率最高；整体约 75%~92% ——
        inspectors = [u.full_name or u.username for u in staff]
        pass_bias = {
            "李姐": 0.95,
            "王阿姨": 0.85,
            "张师傅": 0.80,
            "陈大姐": 0.78,
            "赵保洁": 0.70,
        }
        insp_n = 0
        for off in range(past_days):
            d = today - timedelta(days=past_days - 1 - off)
            if (today - d).days <= 6 and d.weekday() in (0, 3):
                daily = 1  # 稀疏日少量
            else:
                daily = 4 + (off % 3)
            for j in range(daily):
                insp_name = inspectors[j % len(inspectors)]
                # 倾斜给李姐更多「通过」样本
                if j % 3 == 0 and "李姐" in inspectors:
                    insp_name = "李姐"
                rate = pass_bias.get(insp_name, 0.8)
                passed = random.random() < rate
                rm = rooms[(insp_n) % len(rooms)]
                findings = [
                    {
                        "label": "床品摆放",
                        "desc": "符合 SOP" if passed else "褶皱未达标",
                        "ok": passed,
                        "confidence": 90,
                    }
                ]
                db.add(
                    RoomInspection(
                        hotel_id=hotel_id,
                        room_id=rm.id,
                        room_no=rm.room_no,
                        inspector=insp_name,
                        status="passed" if passed else "failed",
                        score=94 if passed else 68,
                        summary=f"一次通过 · {SEED_TAG}" if passed else f"需返工 · {SEED_TAG}",
                        findings_json=json.dumps(findings, ensure_ascii=False),
                        inspected_at=datetime(d.year, d.month, d.day, 14 + (j % 4), 10 + j, 0),
                    )
                )
                insp_n += 1

        db.commit()
        print(
            f"人效复盘样本已写入 hotel_id={hotel_id}："
            f"完成任务≈{task_n}、查房≈{insp_n}、预离订单/排班已覆盖近 {past_days} 天+未来 {future_days} 天。"
        )
        print("请打开 房务报表 → 人效复盘，切换「近 7 天 / 本周 / 近 30 天」查看。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
