# SPDX-License-Identifier: Apache-2.0
"""房间维保相关 helper：房号规范化 + 单房维保视图。

从原 `bootstrap.ensure_room_maintenance` 抽离；种子函数
`seed_room_maintenance_demo` 仍在 `bootstrap.ensure_room_maintenance` 里。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import Asset, AssetAlert, AssetMaintenance, Room


def _norm_room_no(no: str | None) -> str:
    """房号规范化：去非数字、补齐到 4 位。例 '302' → '0302'、'10012' → '10012'。"""
    s = "".join(ch for ch in str(no or "") if ch.isdigit())
    if not s:
        return ""
    return s.zfill(4) if len(s) <= 4 else s


def list_room_maintenance_bundle(db: Session, hotel_id: int, room: Room) -> dict:
    """某房的资产 / 开放告警 / 维保时间线（房号规范化匹配）。"""
    from sqlalchemy import inspect as sa_inspect

    def _d(o):
        return {c.key: getattr(o, c.key) for c in sa_inspect(o).mapper.column_attrs}

    rno = _norm_room_no(room.room_no) or room.room_no
    bare = rno.lstrip("0") or rno
    nos = {rno, bare, room.room_no, str(room.room_no or "")}
    nos = {x for x in nos if x}

    assets = db.query(Asset).filter(Asset.hotel_id == hotel_id, Asset.room_no.in_(list(nos))).all()
    by_id = {a.id: a for a in assets}
    asset_ids = list(by_id.keys())

    alert_q = db.query(AssetAlert).filter(
        AssetAlert.hotel_id == hotel_id,
        AssetAlert.status == "open",
    )
    if asset_ids:
        alert_q = alert_q.filter((AssetAlert.room_no.in_(list(nos))) | (AssetAlert.asset_id.in_(asset_ids)))
    else:
        alert_q = alert_q.filter(AssetAlert.room_no.in_(list(nos)))
    alerts = alert_q.order_by(AssetAlert.id.desc()).limit(10).all()

    if asset_ids:
        maint = (
            db.query(AssetMaintenance)
            .filter(
                AssetMaintenance.hotel_id == hotel_id,
                AssetMaintenance.asset_id.in_(asset_ids),
            )
            .order_by(AssetMaintenance.id.desc())
            .limit(30)
            .all()
        )
    else:
        maint = []

    logs = []
    for m in maint:
        a = by_id.get(m.asset_id)
        logs.append(
            {
                **_d(m),
                "asset_name": a.name if a else None,
                "room_no": rno,
                "title": m.task_type or (a.name if a else "维保"),
                "date": str(m.due_date or (m.completed_at.date() if m.completed_at else None) or "—"),
                "done": (
                    "已解决"
                    if m.status == "done"
                    else "已逾期"
                    if m.status == "overdue"
                    else "跟进中"
                    if m.status == "doing"
                    else "已排期"
                ),
            }
        )

    current_fault = None
    if alerts:
        hit = alerts[0]
        current_fault = {
            "title": hit.asset_name or (hit.message or "")[:24],
            "time": str(hit.biz_date or "—"),
            "desc": hit.message or "",
            "eta": "建议今日处理" if hit.severity == "high" else "纳入本周维保",
            "owner": "工程部",
        }
    elif assets:
        low = sorted(assets, key=lambda x: x.health_score or 100)[0]
        if (low.health_score or 100) < 75:
            current_fault = {
                "title": low.name,
                "time": str(low.next_maintain_date or "—"),
                "desc": low.insight or f"健康分 {low.health_score}",
                "eta": f"计划维保 {low.next_maintain_date}" if low.next_maintain_date else "待排期",
                "owner": "工程部",
            }

    return {
        "room_no": rno,
        "assets": [_d(a) for a in assets],
        "alerts": [_d(a) for a in alerts],
        "maintenance": logs,
        "current_fault": current_fault,
    }
