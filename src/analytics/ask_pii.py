# SPDX-License-Identifier: Apache-2.0
"""AI 问数 v1.3 · PiiGate 隐私脱敏闸（D7/D8）。"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any, Optional

# 店长/管理员（demo 角色码）；对齐规范 MANAGER/OWNER
PII_ALLOWED_ROLES = frozenset({"admin", "gm", "mgr", "MANAGER", "OWNER", "owner"})


def role_can_access_pii(role: Optional[str]) -> bool:
    return (role or "").strip() in PII_ALLOWED_ROLES


def hash_guest_code(guest_id: Any) -> str:
    raw = str(guest_id or "")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    return f"GUEST-{digest}"


def mask_name(name: Optional[str], gender: Optional[str] = None) -> str:
    from infra.i18n import get_locale, t

    n = (name or "").strip()
    en = str(get_locale() or "").lower().startswith("en")
    if not n:
        return t("客人") if not en else "Guest"
    g = (gender or "").lower()
    female = g in ("f", "female", "女")

    # 已是中文脱敏 → 按 Locale 转写
    if n.endswith(("先生", "女士", "小姐")) and len(n) <= 4:
        surname = n[0]
        if en:
            return f"Ms. {surname}" if (n.endswith(("女士", "小姐")) or female) else f"Mr. {surname}"
        return n
    # 已是英文脱敏
    if re.match(r"^(Mr|Ms|Mrs)\.\s+\S$", n, flags=re.I):
        return n

    surname = n[0]
    if en:
        # 拉丁姓用首字母；中文姓保留单字
        token = surname.upper() if surname.isascii() else surname
        return f"Ms. {token}" if female else f"Mr. {token}"
    if female:
        return f"{surname}女士"
    return f"{surname}先生"


def _mask_row(row: dict, *, keep_amount: bool = True) -> dict:
    out = dict(row)
    gid = out.get("guest_id") or out.get("id")
    out["guest_id_masked"] = hash_guest_code(gid)
    out["guest_name"] = mask_name(out.get("guest_name") or out.get("name"), out.get("gender"))
    out["name"] = out["guest_name"]
    out["label"] = out["guest_name"]
    out["phone"] = "***"
    out.pop("phone_mask", None)
    # 不回传明文 id 到前端预览（保留内部 _guest_id）
    if "guest_id" in out:
        out["_guest_id"] = out["guest_id"]
        out["guest_id"] = out["guest_id_masked"]
    if not keep_amount and "value" in out:
        out["value"] = out["value"]  # 金额可展示
    return out


def apply_pii_gate(
    result: dict[str, Any],
    pii_level: str,
    *,
    role: Optional[str] = None,
    unlocked: bool = False,
) -> dict[str, Any]:
    """
    pii_level:
      none    — 原样
      mask    — 脱敏后返回
      confirm — 未解锁时脱敏预览 + need_pii_ack；解锁后仍脱敏姓名/手机，仅放行明细展示
    """
    level = (pii_level or "none").lower()
    out = deepcopy(result) if result else {"rows": [], "empty": True}
    out["pii_level"] = level
    if level == "none":
        out["need_pii_ack"] = False
        out["pii_mask"] = False
        return out

    if not role_can_access_pii(role):
        return {
            "title": out.get("title") or "客户数据",
            "unit": out.get("unit") or "",
            "rows": [],
            "metrics": {},
            "empty": True,
            "pii_level": level,
            "pii_denied": True,
            "need_pii_ack": False,
            "pii_mask": True,
            "message": "当前账号无权限查看客户个人数据（需店长/管理员）。",
        }

    rows = out.get("rows") or []
    masked_rows = [_mask_row(r if isinstance(r, dict) else {"label": str(r)}) for r in rows]
    out["rows"] = masked_rows
    # series 同步用脱敏名
    if out.get("series"):
        out["series"] = [
            {"name": r.get("guest_name") or r.get("label"), "value": r.get("value")}
            for r in masked_rows
            if isinstance(r.get("value"), (int, float))
        ]
    out["pii_mask"] = True
    if level == "confirm" and not unlocked:
        out["need_pii_ack"] = True
        out["pii_preview"] = True
    else:
        out["need_pii_ack"] = False
        out["pii_unlocked"] = bool(unlocked) if level == "confirm" else False
    return out


def strip_internal_ids(result: dict) -> dict:
    """返回前端前去掉内部 _guest_id。"""
    out = deepcopy(result) if result else {}
    for r in out.get("rows") or []:
        if isinstance(r, dict):
            r.pop("_guest_id", None)
    return out


def sanitize_answer_text(text: str) -> str:
    """粗略屏蔽可能出现的手机号。"""
    if not text:
        return text
    return re.sub(r"1\d{10}", "***", text)
