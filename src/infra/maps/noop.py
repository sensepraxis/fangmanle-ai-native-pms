# SPDX-License-Identifier: Apache-2.0
"""兼容：正式实现为 extensions.map.impl.noop.NoopMap。"""

from __future__ import annotations

from extensions.map.impl.noop import NoopMap as NoopMapProvider

NoopMap = NoopMapProvider

__all__ = ["NoopMap", "NoopMapProvider"]
