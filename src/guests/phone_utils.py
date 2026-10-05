# SPDX-License-Identifier: Apache-2.0
"""手机号归一与查询：与渠道无关的纯算法。

从历史 wecom 模块抽出的纯函数，现只依赖 guests/models。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models import Guest


def _digits(phone: str | None) -> str:
    return "".join(c for c in str(phone or "") if c.isdigit())


def _normalize_phone_storage(phone: str | None) -> str:
    """
    存储/比对用手机号规范化：
    - 去掉空格、括号、+ 号等非数字
    - 中国大陆兼容：(+86) / +86 / 86 / 0086 + 11 位 → 存为 11 位
    - 其它情况保留纯数字（后六位匹配仍可用尾号）
    """
    digits = _digits(phone)
    if not digits:
        return ""
    if digits.startswith("0086") and len(digits) >= 15:
        digits = digits[4:]
    elif digits.startswith("86") and len(digits) >= 13:
        digits = digits[2:]
    # 仍带多余前缀时，取末尾 11 位（1 开头的大陆号）
    if len(digits) > 11 and digits[-11:].startswith("1"):
        digits = digits[-11:]
    return digits


def _normalize_cn_mobile(phone: str | None) -> str:
    """归一化手机号（兼容 +86 等）；用于 H5 提交与档案存储。"""
    return _normalize_phone_storage(phone)


def _phone_last4(phone: str | None) -> str:
    """展示用语：手机尾号后四位。"""
    digits = _normalize_phone_storage(phone) or _digits(phone)
    return digits[-4:] if len(digits) >= 4 else "****"


def _phone_last6(phone: str | None) -> str:
    """归集匹配用语：手机号后六位（兼容 +86 / +65 等国码前缀）。"""
    digits = _normalize_phone_storage(phone) or _digits(phone)
    if len(digits) < 6:
        return ""
    return digits[-6:]


def find_guests_by_phone_exact(db: Session, phone: str) -> list[Guest]:
    """按完整手机号精确匹配（先归一化区号；中国大陆实名号可安全自动归集）。"""
    target = _normalize_phone_storage(phone)
    if len(target) < 8:
        return []
    matches: list[Guest] = []
    for g in db.query(Guest).all():
        gp = _normalize_phone_storage(g.phone)
        if gp and gp == target:
            matches.append(g)
    return matches


def find_guests_by_phone_last6(db: Session, phone: str) -> list[Guest]:
    """按手机号后六位匹配已有客人（兼容各国区号前缀）。"""
    suffix = _phone_last6(phone)
    if len(suffix) < 6:
        return []
    matches: list[Guest] = []
    for g in db.query(Guest).all():
        gp = _normalize_phone_storage(g.phone) or _digits(g.phone)
        if gp and len(gp) >= 6 and gp[-6:] == suffix:
            matches.append(g)
    return matches


def find_guests_by_phone_last4(db: Session, phone: str) -> list[Guest]:
    """兼容旧名：实际按后六位匹配。"""
    return find_guests_by_phone_last6(db, phone)
