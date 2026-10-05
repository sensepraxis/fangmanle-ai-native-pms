# SPDX-License-Identifier: Apache-2.0
"""finance.shift_handover_service 子模块 — auto-split by AST.

子模块: asset_service。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from domain import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)

# 同包 cross-import
from finance.shift_handover_service._common import _log
from models import (
    Channel,
    Deposit,
    DepositLedgerEntry,
    FinanceReport,
    Guest,
    GuestTag,
    Order,
    Payment,
    Reservation,
    Room,
    ServiceRequest,
    ShiftAssetCount,
    ShiftAuditLog,
    ShiftFloatCount,
    ShiftHandover,
    ShiftHandoverTask,
    Supply,
    TagDefinition,
    User,
)

LEGACY_ASSET_TYPES = frozenset({"room_card", "receipt_book", "invoice_book"})


def _build_asset_inventory(db: Session, hotel_id: int) -> list[dict]:
    """实物盘库：万能房卡（按房间数推算）+ 物资库存（supplies 表）。"""
    room_cnt = db.query(Room).filter_by(hotel_id=hotel_id).count()
    master_qty = min(4, max(1, room_cnt // 30)) if room_cnt else 0
    items: list[dict] = [
        {
            "asset_type": "master_key",
            "asset_name": "万能房卡",
            "hint": "丢失须换整层锁芯",
            "expected_qty": master_qty,
            "actual_qty": None,
            "supply_id": None,
        }
    ]
    supplies = db.query(Supply).filter_by(hotel_id=hotel_id).order_by(Supply.id.asc()).all()
    for s in supplies:
        cur = int(float(s.current_stock or 0))
        safe = int(float(s.safety_stock or 0))
        items.append(
            {
                "asset_type": "supply",
                "asset_name": s.name,
                "hint": f"库存单位 {s.unit or '件'} · 安全库存 {safe}",
                "expected_qty": cur,
                "actual_qty": None,
                "supply_id": s.id,
                "reorder_triggered": cur < safe,
            }
        )
    return items


def _sync_assets_from_inventory(db: Session, handover: ShiftHandover) -> None:
    """未确认盘库前，按当前库存刷新应有数量；不覆盖已录入实盘。"""
    if handover.assets_confirmed:
        return
    inv = _build_asset_inventory(db, handover.hotel_id)
    existing = {
        a.asset_type + ":" + a.asset_name: a for a in db.query(ShiftAssetCount).filter_by(handover_id=handover.id).all()
    }
    seen: set[str] = set()
    for item in inv:
        key = item["asset_type"] + ":" + item["asset_name"]
        seen.add(key)
        row = existing.get(key)
        if row:
            row.expected_qty = item["expected_qty"]
            row.hint = item.get("hint")
            if item.get("supply_id"):
                row.supply_id = item["supply_id"]
                row.reorder_triggered = item.get("reorder_triggered", False)
        else:
            db.add(
                ShiftAssetCount(
                    handover_id=handover.id,
                    asset_type=item["asset_type"],
                    asset_name=item["asset_name"],
                    hint=item.get("hint"),
                    expected_qty=item["expected_qty"],
                    actual_qty=None,
                    supply_id=item.get("supply_id"),
                    reorder_triggered=item.get("reorder_triggered", False),
                )
            )
    for key, row in existing.items():
        if key not in seen and row.asset_type != "supply":
            continue
        if key not in seen and row.asset_type == "supply":
            db.delete(row)


def _purge_legacy_assets(db: Session, handover: ShiftHandover) -> None:
    """移除历史硬编码实物行（收据本/发票本等），仅保留真实库存来源。"""
    if handover.assets_confirmed:
        return
    for row in db.query(ShiftAssetCount).filter_by(handover_id=handover.id).all():
        if row.asset_type in LEGACY_ASSET_TYPES or row.asset_name == "万能钥匙":
            db.delete(row)


def _normalize_unconfirmed_assets(db: Session, handover: ShiftHandover) -> None:
    """未确认盘库时清除历史预填实盘（旧版曾自动 actual=expected）。"""
    if handover.assets_confirmed:
        return
    for row in db.query(ShiftAssetCount).filter_by(handover_id=handover.id).all():
        row.actual_qty = None
        row.diff_reason = None


def save_asset_count(
    db: Session,
    hotel_id: int,
    handover_id: int,
    assets: list[dict],
    operator_id: int | None = None,
    operator_name: str = "",
) -> dict:
    row = db.get(ShiftHandover, handover_id)
    if not row or row.hotel_id != hotel_id:
        raise NotFoundError("交班记录不存在")
    by_id = {int(a["id"]): a for a in assets if a.get("id")}
    rows = db.query(ShiftAssetCount).filter_by(handover_id=handover_id).all()
    for r in rows:
        payload = by_id.get(r.id)
        if not payload:
            continue
        if payload.get("actual_qty") is None:
            raise InvalidStateError(f"{r.asset_name} 须录入实盘数量")
        r.actual_qty = int(payload.get("actual_qty"))
        diff = (r.actual_qty or 0) - (r.expected_qty or 0)
        reason = (payload.get("diff_reason") or "").strip()
        if diff != 0 and (not reason):
            raise InvalidStateError(f"{r.asset_name} 有差异时必须填写原因")
        r.diff_reason = reason or None
        if r.supply_id and r.actual_qty is not None:
            sup = db.get(Supply, r.supply_id)
            if sup:
                safe = int(float(sup.safety_stock or 0))
                r.reorder_triggered = int(r.actual_qty) < safe
    row.assets_confirmed = True
    _log(db, handover_id, hotel_id, "asset_count", operator_id, operator_name, {"count": len(assets)})
    db.commit()
    return {"ok": True}
