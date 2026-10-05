# SPDX-License-Identifier: Apache-2.0
"""房型 amenities 字段解析 / 推导 + 房型默认值 helper。

从原 `bootstrap.ensure_room_types` 抽离；ensure / backfill 仍在
`bootstrap.ensure_room_types` 里。
"""

from __future__ import annotations

import json


def _derive_area(rt) -> int:
    return int(28 + (rt.capacity or 2) * 6 + (10 if "套" in (rt.name or "") else 0))


def _derive_amenities(rt) -> list:
    tags = []
    if rt.breakfast_included:
        tags.append("含早")
    if (rt.capacity or 0) >= 3:
        tags.append("可加床")
    if "窗" in (rt.name or "") or "景" in (rt.name or ""):
        tags.append("景观")
    if "套" in (rt.name or ""):
        tags.append("会客厅")
    tags.append("淋浴" if "套" not in (rt.name or "") else "浴缸")
    return tags or ["标准配置"]


def parse_amenities(raw) -> list:
    """房型 amenities 字段宽松解析：JSON 数组 / 逗号串 / 列表都接。"""
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    s = str(raw).strip()
    if s.startswith("["):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
        except Exception:
            pass
    return [x.strip() for x in s.replace("，", ",").split(",") if x.strip()]


def dump_amenities(tags) -> str:
    """系列化为 JSON 字符串，方便入库；空值序列化为 "[]"。"""
    return json.dumps(parse_amenities(tags), ensure_ascii=False)
