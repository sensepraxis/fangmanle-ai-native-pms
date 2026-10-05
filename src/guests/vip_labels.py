# SPDX-License-Identifier: Apache-2.0
"""会员等级展示（与企微无关）。"""

from __future__ import annotations

from infra.i18n import t

VIP_LABEL_CN: dict[str, str] = {
    "normal": "普通会员",
    "silver": "白银会员",
    "gold": "黄金会员",
    "platinum": "铂金会员",
    "普通": "普通会员",
}


def vip_label(level: str | None) -> str:
    raw = (level or "normal").strip().lower()
    return t(VIP_LABEL_CN.get(raw, raw or "普通会员"))
