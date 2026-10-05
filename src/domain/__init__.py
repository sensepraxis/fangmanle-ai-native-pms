# SPDX-License-Identifier: Apache-2.0
"""domain 包：跨域不变量与状态机。

集中放跨多个 router/service 的领域概念。当前有：
  - OrderStatus / HKStatus / RoomStatus 等状态机 enum
  - 业务异常类（exceptions.py）

后续可纳入业务规则（Specification）、不变量校验等。
"""

from domain.exceptions import (  # noqa: F401
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
