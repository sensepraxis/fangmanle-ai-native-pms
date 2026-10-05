# SPDX-License-Identifier: BUSL-1.1
"""数据洞察 · AI 问数（意图识别 + 澄清确认 + 确定性查数 + 多轮追问）。

流水线：Tier0 规则预筛 →（可选）Tier1 LLM 消歧 → 澄清闸门 → 确认后执行查询 → LLM/模板总结。
确认前绝不查库。SQL 永不由模型生成。
多轮：session turns + 指代消解 + followup_* + playbook。

本模块为 strangler 门面：公共 API 自子模块再导出，保持既有 import 路径稳定。
"""

from __future__ import annotations

from commercial.analytics.ai_ask_answering import (  # noqa: F401
    ASK_LLM_OPTS,
    catalog_payload,
    intent_looks_like_freeform_tips,
)
from commercial.analytics.ai_ask_execution import (  # noqa: F401
    ack_pii,
    apply_clarify_choice,
    confirm_and_execute,
    stream_confirm_and_execute,
)
from commercial.analytics.ai_ask_routing import (  # noqa: F401
    detect_followup_intent,
    has_pronoun_reference,
    missing_slot,
    route_question,
    rule_resolve_question,
    tier0_candidates,
)
from commercial.analytics.ai_ask_session import (  # noqa: F401
    MAX_CLARIFY_ROUNDS,
    MAX_HISTORY_TURNS,
    load_session_turns,
)

__all__ = [
    "ASK_LLM_OPTS",
    "MAX_CLARIFY_ROUNDS",
    "MAX_HISTORY_TURNS",
    "ack_pii",
    "apply_clarify_choice",
    "catalog_payload",
    "confirm_and_execute",
    "detect_followup_intent",
    "has_pronoun_reference",
    "intent_looks_like_freeform_tips",
    "load_session_turns",
    "missing_slot",
    "route_question",
    "rule_resolve_question",
    "stream_confirm_and_execute",
    "tier0_candidates",
]
