# SPDX-License-Identifier: Apache-2.0
"""Facade module for assets domain.

生成器可产出上方透传包装；文末 ``# --- orchestrated ---`` 为手写编排，勿覆盖。

职责：
  - 调 service 函数 + 透传 BusinessError
  - 写路径编排：事务边界（commit）在此层
"""

from __future__ import annotations

# 业务异常（透传用）
from domain import (  # noqa: F401
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from infra.commercial_pack import bind as _cbind

_generate_asset_next_action = _cbind("commercial.assets.asset_ai", "generate_asset_next_action")
_stream_asset_next_action = _cbind("commercial.assets.asset_ai", "stream_asset_next_action")

from assets.asset_board_service import (
    build_assets_board as _build_assets_board,
)
from assets.asset_board_service import (
    get_asset_maintenance_detail as _get_asset_maintenance_detail,
)
from assets.asset_board_service import (
    list_asset_maintenance as _list_asset_maintenance,
)
from assets.asset_board_service import (
    register_asset as _register_asset,
)

_generate_loss_attribution = _cbind("commercial.assets.asset_loss_ai", "generate_loss_attribution")
_stream_loss_attribution = _cbind("commercial.assets.asset_loss_ai", "stream_loss_attribution")
_load_loss_attribution_context = _cbind("commercial.assets.asset_loss_ai", "load_loss_attribution_context")
_loss_context_fingerprint = _cbind("commercial.assets.asset_loss_ai", "context_fingerprint")
_lookup_attribution_cache = _cbind("commercial.assets.asset_loss_ai", "lookup_attribution_cache")

from assets.supplies_service import (
    approve_restock_order as _approve_restock_order,
)
from assets.supplies_service import (
    build_supplies_board as _build_supplies_board,
)
from assets.supplies_service import (
    create_damage_ticket as _create_damage_ticket,
)
from assets.supplies_service import (
    list_supplies as _list_supplies,
)
from assets.supplies_service import (
    resolve_damage_ticket as _resolve_damage_ticket,
)


def generate_asset_next_action(*args, **kwargs):
    return _generate_asset_next_action(*args, **kwargs)


def stream_asset_next_action(*args, **kwargs):
    return _stream_asset_next_action(*args, **kwargs)


def build_assets_board(*args, **kwargs):
    return _build_assets_board(*args, **kwargs)


def get_asset_maintenance_detail(*args, **kwargs):
    return _get_asset_maintenance_detail(*args, **kwargs)


def list_asset_maintenance(*args, **kwargs):
    return _list_asset_maintenance(*args, **kwargs)


def register_asset(*args, **kwargs):
    return _register_asset(*args, **kwargs)


def generate_loss_attribution(*args, **kwargs):
    return _generate_loss_attribution(*args, **kwargs)


def stream_loss_attribution(*args, **kwargs):
    return _stream_loss_attribution(*args, **kwargs)


def loss_attribution_cache(db, hotel_id, period):
    ctx = _load_loss_attribution_context(db, hotel_id, period)
    fp = _loss_context_fingerprint(ctx)
    cached = _lookup_attribution_cache(db, hotel_id, period, ctx)
    return {"hit": cached is not None, "fingerprint": fp, "data": cached}


def build_supplies_board(*args, **kwargs):
    return _build_supplies_board(*args, **kwargs)


def create_damage_ticket(*args, **kwargs):
    return _create_damage_ticket(*args, **kwargs)


# --- orchestrated ---
from sqlalchemy.orm import Session


def list_supplies(db: Session, hotel_id: int):
    return _list_supplies(db, hotel_id)


def approve_restock_order(db: Session, oid: int) -> dict:
    try:
        out = _approve_restock_order(db, oid)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise


def resolve_damage_ticket(db: Session, tid: int) -> dict:
    try:
        out = _resolve_damage_ticket(db, tid)
        db.commit()
        return out
    except Exception:
        db.rollback()
        raise
