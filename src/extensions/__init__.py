# SPDX-License-Identifier: Apache-2.0
"""Extensions：可换厂商的能力域（防腐层 + Provider）。

与「系统参数」（财务/房型/房间/用户/RBAC）分离。
国情 YAML 的 ``vendors.map`` / ``vendors.messaging`` / ``vendors.llm`` 在此组装。

域：
- ``extensions.map`` —— 地图
- ``extensions.llm`` —— 大模型
- ``extensions.messaging`` —— 私域通道
"""

from __future__ import annotations

from extensions.bootstrap import ensure_extensions, reset_extensions

__all__ = ["ensure_extensions", "reset_extensions"]
