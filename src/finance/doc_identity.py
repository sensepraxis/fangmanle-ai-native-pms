# SPDX-License-Identifier: Apache-2.0
"""AR/AP 单据身份：库内存稳定 token，展示层再按 Locale 拼 label。

Identity tokens（写入 doc_label 列）::
    order:{order_no}
    corp
    note:{user_text}
    ota:{period}:{ch_code}:{n}
    commission:{period}

读路径兼容历史中文/英文整句。协议单位名、用户备注不当 msgid 翻译。
"""

from __future__ import annotations

import re
from typing import Optional

from infra.i18n import t

_ORDER_CN = re.compile(r"^挂账\s*·\s*订单\s+(.+)$")
_ORDER_EN = re.compile(r"^On account\s*·\s*order\s+(.+)$", re.I)
_OTA_CN = re.compile(r"^(\d{1,2})\s*月\s*·\s*(.+?)\s*·\s*(\d+)\s*单$")
_COMM_CN = re.compile(r"^(\d{1,2})\s*月佣金$")
_COMM_EN = re.compile(r"^(\d{1,2})\s+commission$", re.I)

_PARTY_MSGIDS = frozenset({"协议客户", "渠道"})
_NOTE_MSGIDS = frozenset({"结算时扣减", "已结算"})
_CORP_ALIASES = frozenset({"企业挂账", "手工企业挂账"})

DIFF_TYPE_KEY = {
    "long": "finance.shift.overage",
    "short": "finance.shift.shortage",
    "flat": "finance.shift.balanced",
}


def encode_order_doc(order_no: str) -> str:
    return f"order:{str(order_no).strip()}"


def encode_corp_doc() -> str:
    return "corp"


def encode_note_doc(note: Optional[str]) -> str:
    n = str(note or "").strip()
    if not n or n in _CORP_ALIASES:
        return encode_corp_doc()
    if n.startswith(("order:", "ota:", "commission:", "note:", "corp")):
        return n
    return f"note:{n}"


def encode_ota_doc(period: str, ch_code: str, n: int) -> str:
    return f"ota:{period}:{ch_code}:{int(n)}"


def encode_commission_doc(period: str) -> str:
    return f"commission:{period}"


def present_party_name(raw: Optional[str]) -> str:
    """单位名/渠道名：用户数据原样；仅兜底 msgid 才翻译。"""
    s = str(raw or "").strip()
    if not s:
        return s
    if s in _PARTY_MSGIDS:
        return t(s)
    return s


def present_diff_type_label(code: Optional[str]) -> str:
    key = DIFF_TYPE_KEY.get(str(code or "").strip(), "")
    return t(key) if key else str(code or "")


def present_sys_note(raw: Optional[str]) -> Optional[str]:
    s = str(raw or "").strip()
    if not s:
        return None
    if s in _NOTE_MSGIDS:
        return t(s)
    return s


def present_doc_label(raw: Optional[str], *, channel_name: Optional[str] = None) -> str:
    s = str(raw or "").strip()
    if not s:
        return s

    if s == "corp":
        return t("finance.ar.doc_corp")
    if s.startswith("order:"):
        return t("finance.ar.doc_order", order_no=s[6:])
    if s.startswith("note:"):
        return s[5:]
    if s.startswith("commission:"):
        period = s.split(":", 1)[-1]
        month = period[-2:] if period else period
        return t("finance.ar.doc_commission", month=month)
    if s.startswith("ota:"):
        parts = s.split(":")
        # ota:{period}:{ch_code}:{n}  — period 含 '-' 故从右切
        if len(parts) >= 4:
            n = parts[-1]
            ch_code = parts[-2]
            period = ":".join(parts[1:-2])
            month = period[-2:] if period else period
            ch = present_party_name(channel_name) or ch_code
            return t("finance.ar.doc_ota", month=month, ch=ch, n=n)

    m = _ORDER_CN.match(s) or _ORDER_EN.match(s)
    if m:
        return t("finance.ar.doc_order", order_no=m.group(1).strip())
    m = _COMM_CN.match(s) or _COMM_EN.match(s)
    if m:
        return t("finance.ar.doc_commission", month=m.group(1))
    m = _OTA_CN.match(s)
    if m:
        ch = present_party_name(channel_name) or m.group(2)
        return t("finance.ar.doc_ota", month=m.group(1), ch=ch, n=m.group(3))
    if s in _CORP_ALIASES:
        return t("finance.ar.doc_corp")
    return s
