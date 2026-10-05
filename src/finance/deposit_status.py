# SPDX-License-Identifier: Apache-2.0
"""押金状态机（从 deposit_service 绞杀抽出）。

Service 层只编排金额/流水；合法跳变以本模块 + Deposit.apply_event 为准。
展示文案经 i18n（中文 msgid）。
"""

from __future__ import annotations

from typing import Optional

from infra.i18n import TranslatingMap, t

FORMS = TranslatingMap(
    {
        "PREAUTH_CARD": "银行卡预授权",
        "WECHAT_DEPOSIT": "微信押金",
        "ALIPAY_DEPOSIT": "支付宝押金",
        "CASH": "现金",
        "AR": "企业挂账",
    }
)

STATUS_LABEL = TranslatingMap(
    {
        "CREATED": "待收押",
        "FROZEN": "在押",
        "PARTIAL_CAPTURE": "扣减中",
        "EXPIRED": "失效",
        "DISPUTED": "争议",
        "RELEASED": "已释放",
        "RELEASED_AFTER_CAPTURE": "扣减后释放",
        "CAPTURED": "全额扣减",
    }
)

IN_HOLD = frozenset({"FROZEN", "PARTIAL_CAPTURE", "EXPIRED", "DISPUTED"})
TERMINAL = frozenset({"RELEASED", "RELEASED_AFTER_CAPTURE", "CAPTURED"})
ABNORMAL = frozenset({"EXPIRED", "DISPUTED"})

# (from_status, event) -> to_status
TRANSITIONS: dict[tuple[str, str], str] = {
    ("CREATED", "COLLECT"): "FROZEN",
    ("FROZEN", "CAPTURE"): "PARTIAL_CAPTURE",
    ("FROZEN", "EXPIRE"): "EXPIRED",
    ("FROZEN", "DISPUTE"): "DISPUTED",
    ("FROZEN", "RELEASE"): "RELEASED",
    ("PARTIAL_CAPTURE", "RELEASE"): "RELEASED_AFTER_CAPTURE",
    ("PARTIAL_CAPTURE", "CAPTURE"): "CAPTURED",
    ("EXPIRED", "REAUTHORIZE"): "FROZEN",
    ("DISPUTED", "REAUTHORIZE"): "FROZEN",
    ("DISPUTED", "SETTLE"): "RELEASED",
    ("DISPUTED", "RELEASE"): "RELEASED",
}


def next_status(from_status: str, event: str, *, full_capture: Optional[bool] = None) -> str:
    """计算下一状态；CAPTURE 可按是否足额覆盖。"""
    key = (from_status, event)
    if event == "CAPTURE":
        if from_status == "FROZEN":
            return "CAPTURED" if full_capture else "PARTIAL_CAPTURE"
        if from_status == "PARTIAL_CAPTURE":
            return "CAPTURED" if full_capture else "PARTIAL_CAPTURE"
    to = TRANSITIONS.get(key)
    if not to:
        from domain import InvalidStateError

        raise InvalidStateError(t("状态 {status} 不允许事件 {event}", status=from_status, event=event))
    return to
