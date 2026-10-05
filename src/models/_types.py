# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy 字段类型（每个域子文件共用）。

为避免每个域子文件重复堆 import，这里集中导入一次；
每个域子文件 header 都会用这套 import，确保 Column/Integer/String 等
类型在所有模型定义中都可见。
"""

from sqlalchemy import (  # noqa: F401
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)

from models._base import Base  # noqa: F401
