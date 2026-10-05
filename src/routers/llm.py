# SPDX-License-Identifier: Apache-2.0
"""LLM 配置 / 探测 / 试聊 — 只走 application.llm。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api_common import ok
from database import get_db

router = APIRouter(tags=["llm"])


@router.get("/llm/providers")
def llm_providers():
    from application.llm import localized_llm_providers

    return ok(localized_llm_providers())


@router.get("/llm/config")
def get_llm_config(db: Session = Depends(get_db)):
    from application.llm import load_llm_config, mask_llm_config

    return ok(mask_llm_config(load_llm_config(db)))


@router.put("/llm/config")
def put_llm_config(payload: dict, db: Session = Depends(get_db)):
    from application.llm import mask_llm_config, save_llm_config

    return ok(mask_llm_config(save_llm_config(db, payload)))


@router.post("/llm/config/test")
def post_llm_config_test(db: Session = Depends(get_db)):
    from application.llm import load_llm_config, test_llm_connection

    return ok(test_llm_connection(load_llm_config(db)))


class LlmChatPayload(BaseModel):
    messages: list[dict] = []
    system_hint: Optional[str] = None


@router.post("/llm/chat")
def post_llm_chat(payload: LlmChatPayload, db: Session = Depends(get_db)):
    from application.llm import chat

    return ok(chat(db, payload.messages, payload.system_hint))
