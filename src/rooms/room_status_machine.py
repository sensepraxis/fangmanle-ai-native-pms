# SPDX-License-Identifier: Apache-2.0
"""房态状态机（State 模式）。

把 rooms/room_status.py 里散落的 dict + helper 抽成 enum + 转换规则；
保留 rooms/room_status.py 现有 normalize/transition 函数作为兼容层（router
和既有代码依赖它们），新增 alias 让两边都收敛到这一个事实源。
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class RoomStatus(str, Enum):
    VC = "VC"  # 空净房
    VD = "VD"  # 空脏房
    OCC = "OCC"  # 已入住房
    EA = "EA"  # 预抵房
    DO = "DO"  # 预离房
    OOO = "OOO"  # 维修房
    BLK = "BLK"  # 锁房

    @property
    def cn(self) -> str:
        """中文标签（兼容 rooms/room_status.STATUS_CN）。"""
        return STATUS_CN[self.value]


# 旧值 → 标准码（保留外部兼容）
_LEGACY_BASE: dict[str, str] = {
    # 中文/老 schema
    "vacant": RoomStatus.VC.value,
    "clean": RoomStatus.VC.value,
    "inspected": RoomStatus.VC.value,
    "dirty": RoomStatus.VD.value,
    "cleaning": RoomStatus.VD.value,  # 过程态归 VD，工单表达进行中
    "occupied": RoomStatus.OCC.value,
    "ooo": RoomStatus.OOO.value,
    "maintenance": RoomStatus.OOO.value,
    "vac": RoomStatus.VC.value,
    "vd": RoomStatus.VD.value,
    "occ": RoomStatus.OCC.value,
    "ea": RoomStatus.EA.value,
    "do": RoomStatus.DO.value,
    "blk": RoomStatus.BLK.value,
    "block": RoomStatus.BLK.value,
}
# 同时提供大写键（"VAC"/"VD" 等），数据库里大小写都可能
LEGACY_MAP: dict[str, str] = {**_LEGACY_BASE, **{k.upper(): v for k, v in _LEGACY_BASE.items()}}
# 与 room_status.LEGACY_MAP 对齐的短码
LEGACY_MAP.setdefault("vc", RoomStatus.VC.value)
LEGACY_MAP.setdefault("VC", RoomStatus.VC.value)


STATUS_CN: dict[str, str] = {
    RoomStatus.VC.value: "空净房",
    RoomStatus.VD.value: "空脏房",
    RoomStatus.OCC.value: "已入住房",
    RoomStatus.EA.value: "预抵房",
    RoomStatus.DO.value: "预离房",
    RoomStatus.OOO.value: "维修房",
    RoomStatus.BLK.value: "锁房",
}


# 合法转换（在住不可直接进维修）
ALLOWED_TRANSITIONS: dict[RoomStatus, FrozenSet[RoomStatus]] = {
    RoomStatus.VC: frozenset({RoomStatus.EA, RoomStatus.OCC, RoomStatus.BLK, RoomStatus.OOO, RoomStatus.VD}),
    RoomStatus.EA: frozenset({RoomStatus.OCC, RoomStatus.VC}),
    RoomStatus.OCC: frozenset({RoomStatus.VD, RoomStatus.DO, RoomStatus.OCC}),  # 续住 OCC→OCC；禁止 OCC→OOO
    RoomStatus.DO: frozenset({RoomStatus.VD, RoomStatus.OCC}),
    RoomStatus.VD: frozenset({RoomStatus.VC, RoomStatus.OOO}),
    RoomStatus.OOO: frozenset({RoomStatus.VC, RoomStatus.VD}),
    RoomStatus.BLK: frozenset({RoomStatus.VC, RoomStatus.OOO}),
}


# 可售集合
SELLABLE = frozenset({RoomStatus.VC})
CHECKIN_OK = frozenset({RoomStatus.VC, RoomStatus.EA})


def normalize(raw):
    """把任意字符串（含老值 / 大小写变体）映射到标准码；空值 → VC。"""
    if not raw:
        return RoomStatus.VC.value
    s = str(raw).strip()
    # 1) 精确大小写
    try:
        return RoomStatus(s).value
    except ValueError:
        pass
    # 2) 标准化大写（数据库常存 "VAC"/"vacant" 等）
    up = s.upper()
    if up in {e.value for e in RoomStatus}:
        return up
    # 3) 旧值映射（大小写都查一次，DB 老 schema 既有 "vacant" 也有 "VACANT"）
    return LEGACY_MAP.get(s.lower(), LEGACY_MAP.get(up, up))


def can_transition(src: RoomStatus, dst: RoomStatus) -> bool:
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())


def can_checkin(raw_status) -> bool:
    return RoomStatus(normalize(raw_status)) in CHECKIN_OK


def is_sellable(raw_status) -> bool:
    return RoomStatus(normalize(raw_status)) in SELLABLE


def label(raw_status) -> str:
    from infra.i18n import t

    msgid = STATUS_CN.get(normalize(raw_status), str(raw_status or "—"))
    return t(msgid) if msgid else "—"


def all_statuses() -> list[str]:
    return [s.value for s in RoomStatus]
