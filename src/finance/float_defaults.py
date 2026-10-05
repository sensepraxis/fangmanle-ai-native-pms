# SPDX-License-Identifier: Apache-2.0
"""门店备用金默认值。

从原 `bootstrap.ensure_finance_float_carry` 抽离；ensure_*_schema / seed_* 仍在
`bootstrap.ensure_finance_float_carry` 里。
"""

from __future__ import annotations

DEFAULT_AMOUNT = 2000.0
DEFAULT_CURRENCY = "CNY"

DEFAULT_DENOM_RATIOS = [
    {"denom": 100, "ratio": 0.50, "label": "100 元"},
    {"denom": 50, "ratio": 0.25, "label": "50 元"},
    {"denom": 20, "ratio": 0.15, "label": "20 元"},
    {"denom": 10, "ratio": 0.05, "label": "10 元"},
    {"denom": 5, "ratio": 0.025, "label": "5 元"},
    {"denom": 1, "ratio": 0.025, "label": "1 元"},
    {"denom": 0.5, "ratio": 0.004, "label": "5 角"},
    {"denom": 0.1, "ratio": 0.004, "label": "1 角"},
]
