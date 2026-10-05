# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy 单一 Base：所有 ORM 模型继承于此。

把 Base 从原 models.py 抽出至此，便于 models/ 子包按域拆分后
所有模型仍能正确注册到同一 metadata。
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

__all__ = ["Base"]
