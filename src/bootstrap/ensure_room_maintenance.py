# SPDX-License-Identifier: Apache-2.0
"""房间维保数据：按档案房号（如 0304）对齐 assets / asset_maintenance / alerts。

房号规范化与单房维保视图 helper 已抽到 `rooms.maintenance_bundle`；本文件仅保留
种子函数 `seed_room_maintenance_demo`。
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models import Asset, AssetAlert, AssetMaintenance, Room
from rooms.maintenance_bundle import _norm_room_no, list_room_maintenance_bundle

TODAY = date.today()


def seed_room_maintenance_demo(db: Session, hotel_id: int = 1, max_rooms: int = 40) -> dict:
    """
    为物理房间补齐客房设备 + 维修记录 + 少量开放告警（幂等：按 room_no+name 复用资产）。
    解决历史种子房号「302」与档案「0302」不一致导致日志空白的问题。
    """
    rooms = (
        db.query(Room)
        .filter(Room.hotel_id == hotel_id)
        .order_by(Room.floor.asc(), Room.room_no.asc())
        .limit(max_rooms)
        .all()
    )
    if not rooms:
        return {"rooms": 0, "assets": 0, "maintenance": 0, "alerts": 0}

    owners = ["张师傅", "李工", "王工", "工程外包", "前台报修"]
    n_assets = n_maint = n_alerts = 0

    # 先把旧台账房号规范化到 4 位，便于匹配
    for a in db.query(Asset).filter(Asset.hotel_id == hotel_id, Asset.room_no.isnot(None)).all():
        nn = _norm_room_no(a.room_no)
        if nn and a.room_no != nn:
            a.room_no = nn

    for idx, room in enumerate(rooms):
        rno = _norm_room_no(room.room_no) or room.room_no
        floor_lab = f"{room.floor}F" if room.floor is not None else "—"
        lock_id = (room.lock_id or f"LOCK-{rno}").strip()

        specs = [
            (
                f"{rno}智能门锁",
                "门锁安防",
                lock_id,
                "Yale YDM4109",
                1280,
                55 + (idx % 40),
                "门锁电池与固件需纳入巡检",
            ),
            (
                f"{rno}分体空调",
                "空调暖通",
                f"AC-{rno}",
                "格力 KFR-35",
                3200,
                60 + (idx % 35),
                "滤网与排水需季节性保养",
            ),
            (
                f"{rno}淋浴套件",
                "卫浴设备",
                f"BT-{rno}",
                "TOTO 淋浴",
                2100,
                70 + (idx % 25),
                "花洒水压与密封圈例行检查",
            ),
        ]

        room_assets: list[Asset] = []
        for name, cat, asset_no, model, pv, score, insight in specs:
            a = db.query(Asset).filter(Asset.hotel_id == hotel_id, Asset.room_no == rno, Asset.name == name).first()
            if not a:
                a = db.query(Asset).filter(Asset.hotel_id == hotel_id, Asset.asset_no == asset_no).first()
            if a:
                a.room_no = rno
                a.location = floor_lab
                a.category = cat
                a.asset_no = a.asset_no or asset_no
                a.brand_model = a.brand_model or model
                a.health_score = a.health_score or score
                a.insight = a.insight or insight
                a.next_maintain_date = a.next_maintain_date or (TODAY + timedelta(days=7 + idx % 14))
                a.dept = a.dept or "工程维保部"
            else:
                a = Asset(
                    hotel_id=hotel_id,
                    name=name,
                    category=cat,
                    location=floor_lab,
                    room_no=rno,
                    asset_no=asset_no,
                    sn=f"SN-{asset_no}",
                    brand_model=model,
                    purchase_date=date(2021 + (idx % 3), (idx % 12) + 1, 8),
                    purchase_value=pv,
                    current_value=round(pv * 0.55, 2),
                    repair_cost_total=round(pv * 0.08, 2),
                    health_score=score,
                    insight=insight,
                    next_maintain_date=TODAY + timedelta(days=7 + idx % 14),
                    supplier="工程总包",
                    dept="工程维保部",
                    status="active" if score >= 60 else "maintenance",
                )
                db.add(a)
                db.flush()
                n_assets += 1
            room_assets.append(a)

        for a in room_assets:
            exists = (
                db.query(AssetMaintenance)
                .filter(AssetMaintenance.hotel_id == hotel_id, AssetMaintenance.asset_id == a.id)
                .count()
            )
            if exists >= 2:
                continue
            # 历史已完成
            db.add(
                AssetMaintenance(
                    hotel_id=hotel_id,
                    asset_id=a.id,
                    task_type="历史维修",
                    due_date=TODAY - timedelta(days=40 + idx % 90),
                    status="done",
                    cost=round(random.uniform(80, 680), 2),
                    note=f"{a.name}：客诉/巡检后已修复归档",
                    owner=random.choice(owners),
                    completed_at=datetime.now() - timedelta(days=30 + idx % 60),
                )
            )
            # 计划/进行中
            st = "doing" if a.health_score and a.health_score < 65 else "scheduled"
            ttype = "紧急检修" if st == "doing" else "预防性保养"
            db.add(
                AssetMaintenance(
                    hotel_id=hotel_id,
                    asset_id=a.id,
                    task_type=ttype,
                    due_date=a.next_maintain_date or (TODAY + timedelta(days=5)),
                    status=st,
                    cost=round(random.uniform(100, 900), 2),
                    note=a.insight or "按计划维保",
                    owner=random.choice(owners),
                )
            )
            n_maint += 2

        # 每 4 间放一条开放告警，丰富「当前故障」
        if idx % 4 == 0 and room_assets:
            target = room_assets[0]
            dup = (
                db.query(AssetAlert)
                .filter(
                    AssetAlert.hotel_id == hotel_id,
                    AssetAlert.room_no == rno,
                    AssetAlert.status == "open",
                    AssetAlert.asset_id == target.id,
                )
                .first()
            )
            if not dup:
                db.add(
                    AssetAlert(
                        hotel_id=hotel_id,
                        biz_date=TODAY,
                        asset_id=target.id,
                        room_no=rno,
                        floor=floor_lab,
                        asset_name=target.name,
                        alert_type="health" if "空调" in target.name else "iot",
                        severity="high" if (target.health_score or 100) < 60 else "mid",
                        message=target.insight or f"{target.name} 需关注",
                        status="open",
                    )
                )
                n_alerts += 1

    db.commit()
    return {"rooms": len(rooms), "assets": n_assets, "maintenance": n_maint, "alerts": n_alerts}
