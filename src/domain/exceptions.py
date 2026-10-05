# SPDX-License-Identifier: Apache-2.0
"""业务异常类 — 解耦业务层与 HTTP 层。

业务层 service 函数抛这些异常（不含 HTTP 概念）；
router / facade 层捕获并转换为 HTTPException 返回给前端。

设计要点：
- 业务异常继承自 Exception（不是 HTTPException）
- 每个异常带 http_status 类属性 → router 层用统一 handler 转 HTTP
- 业务异常带 message / detail → 调试和国际化用
- 子类按"业务语义"组织，不按 HTTP 状态码组织（状态码是 router 关心的事）
"""

from __future__ import annotations

from typing import Any, Optional


class BusinessError(Exception):
    """业务层异常基类。所有业务异常继承自此。

    与 HTTPException 的关键区别：
    - 业务异常不知道 HTTP（不 import fastapi）
    - 业务层可自由抛，router / facade 层统一翻译
    - 易于做单元测试（service 函数抛 NotFoundError，不依赖 HTTP 测试客户端）
    """

    http_status: int = 400  # 默认 400 Bad Request，子类覆盖
    code: str = "business_error"  # 业务错误码（前端可识别）

    def __init__(self, message: str, *, detail: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(BusinessError):
    """资源不存在（订单/酒店/客人/房间等）。"""

    http_status = 404
    code = "not_found"


class ConflictError(BusinessError):
    """资源冲突（如重复下单、状态机越界）。"""

    http_status = 409
    code = "conflict"


class InvalidStateError(BusinessError):
    """业务状态机越界（如 cancel 已 checkin 的订单）。"""

    http_status = 400
    code = "invalid_state"


class ValidationError(BusinessError):
    """参数校验失败（业务规则层）。"""

    http_status = 400
    code = "validation_error"


class AuthenticationError(BusinessError):
    """认证失败。"""

    http_status = 401
    code = "authentication_error"


class AuthorizationError(BusinessError):
    """权限不足。"""

    http_status = 403
    code = "authorization_error"


class RateLimitError(BusinessError):
    """频率限制。"""

    http_status = 429
    code = "rate_limit"
