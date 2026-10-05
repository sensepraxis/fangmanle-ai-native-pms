# SPDX-License-Identifier: Apache-2.0
"""Auto-split domain router from api.py — thin HTTP layer."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_common import hotel_scope, ok, row_to_dict
from database import engine, get_db
from infra.auth_local import (
    AppContext,
    assert_hotel_access,
    authenticate_user,
    get_current_user,
    get_hotel_id,
    issue_token,
)

router = APIRouter(tags=["misc"])


@router.get("/reviews")
def list_reviews(hotel_id: int = Depends(hotel_scope), db: Session = Depends(get_db)):
    from application.guests import list_reviews as list_reviews_uc

    return ok(list_reviews_uc(db, hotel_id))


class ReviewReplyPayload(BaseModel):
    replied: bool = True
    reply_content: Optional[str] = None


@router.patch("/reviews/{review_id}")
def patch_review(
    review_id: int,
    payload: ReviewReplyPayload,
    hotel_id: int = Depends(hotel_scope),
    db: Session = Depends(get_db),
):
    from application.guests import patch_review as patch_review_uc

    return ok(
        patch_review_uc(
            db,
            hotel_id,
            review_id,
            replied=payload.replied,
            reply_content=payload.reply_content,
        )
    )
