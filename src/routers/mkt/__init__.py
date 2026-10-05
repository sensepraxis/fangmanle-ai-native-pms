# SPDX-License-Identifier: Apache-2.0
"""mkt domain routers (split by subdomain)."""

from __future__ import annotations

from fastapi import APIRouter

from routers.mkt.acquisition import router as _acquisition
from routers.mkt.ai import router as _ai
from routers.mkt.auto_rules import router as _auto_rules
from routers.mkt.campaigns import router as _campaigns
from routers.mkt.core import router as _core
from routers.mkt.coupons import router as _coupons
from routers.mkt.member import router as _member

router = APIRouter(tags=["mkt"])
router.include_router(_acquisition)
router.include_router(_ai)
router.include_router(_auto_rules)
router.include_router(_campaigns)
router.include_router(_core)
router.include_router(_coupons)
router.include_router(_member)
