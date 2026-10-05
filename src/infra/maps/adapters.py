# SPDX-License-Identifier: Apache-2.0
"""兼容：正式实现在 extensions.map.impl。"""

from __future__ import annotations

from extensions.map.impl.gaode import GaodeMap as AmapMapProvider
from extensions.map.impl.tianditu import TiandituMap as TiandituMapProvider

__all__ = ["AmapMapProvider", "TiandituMapProvider"]
