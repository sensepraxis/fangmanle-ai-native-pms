# SPDX-License-Identifier: Apache-2.0
"""启动期建表与种子数据（原 migrations/）。

本包是程序启动/路由入口时幂等调用的"启动期建表"与"演示种子"工具集，
**不是** alembic 那种"按顺序执行的版本迁移"。没有版本号、没有升降级方向，
每个函数要么 `ensure_*_schema()` 幂等建表、要么 `seed_*()` 幂等灌种子。

新增增量请优先登记到 ``infra.schema_migrate.MIGRATIONS``（版本账本），
再在 migration 内调用或逐步替换对应 ``ensure_*``。

约定：
- ``ensure_*.py`` —— 启动期 idempotent 建表 + 字段保活（主入口：``ensure_xxx_schema()``）。
- ``seed_*.py`` —— 演示/默认种子数据灌入（如 ``seed_compact_floors``）。
- ``migrations/alter_*.py`` —— 真 ALTER / 历史数据回填（一次性，慎用）。

业务模块也常 import 这些模块的辅助常量/纯函数（如 ``bootstrap.ensure_finance_float_carry``
里的 ``bootstrap_finance_float_carry``），并不限于启动期使用。

新增模块请按上述前缀命名，并在模块顶部 docstring 简述用途。
"""
