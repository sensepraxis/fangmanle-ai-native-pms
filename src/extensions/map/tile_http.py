# SPDX-License-Identifier: Apache-2.0
"""瓦片 HTTP 拉取（实现类共用，路由勿直接调用）。"""

from __future__ import annotations

import urllib.request


def fetch_bytes(url: str, *, referer: str = "", timeout: float = 12.0) -> tuple[bytes, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type") or "image/png"
    return body, ctype
