# SPDX-License-Identifier: Apache-2.0
"""应收应付中心：建表 + 从订单/挂账明细同步（不灌假应付）。"""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from models import ApInvoice, ArApLog, ArInvoice, Base, OtaSettlement


def ensure_ar_ap_schema(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    need = []
    for model in (OtaSettlement, ArInvoice, ApInvoice, ArApLog):
        if model.__tablename__ not in tables:
            need.append(model.__table__)
    if need:
        Base.metadata.create_all(engine, tables=need)


def bootstrap_ar_ap(db: Session, hotel_id: int = 1):
    """启动时：校正协议单支付态 + 清除非真实 AR/AP + 从订单同步。"""
    from finance.ar_ap_service import normalize_agreement_orders, purge_non_real_ar_ap, sync_ar_ap_from_orders

    norm = normalize_agreement_orders(db, hotel_id)
    purged = purge_non_real_ar_ap(db, hotel_id)
    synced = sync_ar_ap_from_orders(db, hotel_id)
    db.flush()
    return {**norm, **purged, **synced}
