# SPDX-License-Identifier: Apache-2.0
"""CRM 扩展分群 / 标签默认 + 增强规则匹配。

从原 `bootstrap.ensure_crm_extended` 抽离；ensure_*_schema / ensure_extended_tags /
ensure_extra_segments / ensure_crm_extended 仍在 `bootstrap.ensure_crm_extended` 里。
"""

from __future__ import annotations

EXTRA_SEGMENTS = [
    ("高意向未转化", "high_intent", "growth"),
]

EXTRA_TAGS = [
    ("pref_quiet_high_floor", "偏好高层安静房", "画像", "review:quiet AND pref:high_floor"),
    ("active_90d", "近90天高活跃", "行为", "stays>=2 AND ltv>3000 AND days<=90"),
    ("iot_anomaly", "IoT异常信号", "风险", "event:iot_anomaly"),
]


def match_rule_extended(guest, tag_codes: set[str], rule: str) -> bool:
    """在 `match_rule` 之上覆盖 CRM 扩展规则。基础规则先在 `bootstrap.seed_member_crm.match_rule` 处理。"""
    from bootstrap.ensure_member_crm import match_rule

    if match_rule(guest, tag_codes, rule):
        return True
    r = (rule or "").strip().lower().replace(" ", "")
    ltv = float(guest.ltv or 0)
    churn = float(guest.churn_risk or 0)
    if "ltv>3000" in r and ("stays>=2" in r or "repeat" in r):
        return ltv > 3000 and ("repeat" in tag_codes or "active_90d" in tag_codes)
    if "high_intent" in r:
        return ltv > 2000 and churn < 0.55
    if "iot" in r or "anomaly" in r:
        return "iot_anomaly" in tag_codes
    return False
