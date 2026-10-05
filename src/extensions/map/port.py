# SPDX-License-Identifier: Apache-2.0
"""地图防腐接口 IMap：业务（含价格助手）只依赖本 Protocol，不 import 任何图商 SDK。"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class IMap(Protocol):
    """
    通用地图能力：
    - geocode：地址 → 坐标
    - nearby_hotels：中心点周边检索
    - render_config：前端如何渲染底图
    - fetch_tile：同源瓦片代理（按图商实现；不需要则返回 None）
    - status：能力与密钥状态
    """

    name: str

    def status(self) -> dict[str, Any]:
        """前端底图与系统配置页用的能力/密钥状态。"""
        ...

    def geocode(self, address: str, city: Optional[str] = None) -> dict[str, Any]:
        """基于输入位置查看坐标（地理编码）。"""
        ...

    def nearby_hotels(self, lng: float, lat: float, radius_m: int = 3000, **kwargs: Any) -> dict[str, Any]:
        """周边酒店/POI，供竞品圈选。"""
        ...

    def render_config(self) -> dict[str, Any]:
        """
        渲染地图所需的前端配置：
        engine / js_enabled / js_key / security_js_code / script_url /
        tiles_url / tile_layers（同源代理时用）。
        """
        ...

    def fetch_tile(
        self,
        layer: str,
        z: int,
        y: int,
        x: int,
        *,
        referer: str = "",
    ) -> Optional[tuple[bytes, str]]:
        """
        同源瓦片代理。返回 (content_bytes, media_type)；
        本图商不需要/未实现代理时返回 None（前端改走官方 JS SDK 自带底图）。
        """
        ...


MapProvider = IMap

__all__ = ["IMap", "MapProvider"]
