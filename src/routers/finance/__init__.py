# SPDX-License-Identifier: Apache-2.0
"""finance domain routers (split by subdomain)."""

from __future__ import annotations

from fastapi import APIRouter

from routers.finance.core import router as _core
from routers.finance.deposits import router as _deposits
from routers.finance.night_audit import router as _night_audit
from routers.finance.ops import router as _ops
from routers.finance.refund_adjust import router as _refund_adjust
from routers.finance.reports import router as _reports
from routers.finance.shift import router as _shift

router = APIRouter(tags=["finance"])
router.include_router(_core)
router.include_router(_deposits)
router.include_router(_night_audit)
router.include_router(_ops)
router.include_router(_refund_adjust)
router.include_router(_reports)
router.include_router(_shift)
