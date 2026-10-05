# SPDX-License-Identifier: Apache-2.0
"""订单类型推断 / 通用种子 helper。

从原 `bootstrap.migrations.alter_pms_core_plaintext` 抽离；backfill_pms_core / ensure_pms_core_schema /
migrate_plaintext_phones / purge_expired_id_docs 仍在 `bootstrap.ensure_pms_core` 里。
"""

from __future__ import annotations


def _infer_order_type(channel_code: str | None, source_group: str, nights: int) -> int:
    """订单类型编号（业务常量 1/2/3/4 含义见 schema）。"""
    if source_group == "agreement" or channel_code == "agreement":
        return 3
    if source_group == "longstay" or channel_code == "longstay" or nights >= 28:
        return 4
    if source_group == "ota" or channel_code in ("ota", "ctrip", "meituan", "fliggy"):
        return 2
    if source_group == "voucher":
        return 1
    return 1
