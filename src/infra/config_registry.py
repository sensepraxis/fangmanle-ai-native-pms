# SPDX-License-Identifier: Apache-2.0
"""应用配置（AppSetting）通用加载/保存工具 + 注册表。

背景：``load_llm_config`` / ``load_map_config`` / ``load_wecom_config`` 三个 loader
分布在三个文件、各自实现"读 AppSetting.key → JSON.loads → merge default"。
代码重复度高，新增配置项时容易复制出错。

本模块提供：
- ``load_app_setting_json`` / ``save_app_setting_json`` —— 通用工具函数，
  3 个现 loader 可逐步迁移使用（本期不强制重写，0 风险）。
- ``CONFIG_REGISTRY`` —— 注册表模式（参考 ``LLM_PROVIDERS``），
  未来新增配置项只需 ``CONFIG_REGISTRY.register(...)``，无需写新 loader。

约定：
- 配置以 dict 形式存到 ``app_settings`` 表（key=配置名，value_json=JSON 字符串）。
- 默认值由 ``default_factory`` 提供（深拷贝避免共享）。
- ``merge_keys`` 指定哪些顶层 key 在用户存值后保持默认（防止空值覆盖）。
- ``mask_keys`` 指定哪些 key 在返回前需要 mask（防止 secret 泄露到日志）。

参考用法（未来添加新配置时）：
    from infra.config_registry import CONFIG_REGISTRY, AppSettingSpec

    DEFAULT_PRICING_CONFIG = {...}

    CONFIG_REGISTRY.register(AppSettingSpec(
        key="pricing",
        default_factory=lambda: deepcopy(DEFAULT_PRICING_CONFIG),
        mask_keys=("secret",),
    ))
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from sqlalchemy.orm import Session

from models import AppSetting


@dataclass(frozen=True)
class AppSettingSpec:
    """一项 AppSetting 配置的元数据。"""

    key: str
    default_factory: Callable[[], dict]
    description: str = ""
    mask_keys: tuple = ()
    # 这些 key 即便用户在库里存了空值，也保留 default（避免空覆盖）
    protect_keys: tuple = ()


class ConfigRegistry:
    """AppSetting 配置注册表（类似 ``LLM_PROVIDERS`` 的注册模式）。"""

    _specs: dict[str, AppSettingSpec] = {}

    @classmethod
    def register(cls, spec: AppSettingSpec) -> None:
        cls._specs[spec.key] = spec

    @classmethod
    def get(cls, key: str) -> Optional[AppSettingSpec]:
        return cls._specs.get(key)

    @classmethod
    def all_keys(cls) -> list[str]:
        return list(cls._specs.keys())


CONFIG_REGISTRY = ConfigRegistry()


def load_app_setting_json(
    db: Session,
    key: str,
    default_factory: Callable[[], dict],
    *,
    protect_keys: Iterable[str] = (),
    mask_keys: Iterable[str] = (),
) -> dict:
    """从 app_settings 表读 key 的 JSON 值，与 default_factory 合并。

    合并策略：
    - 若表中无记录 → 返回 deepcopy(default_factory())。
    - 若表中有记录 → JSON.loads 得 user_overrides，与 default 合并（user 覆盖 default）。
    - ``protect_keys``：即使用户存了 None 或空字符串，也保留 default 值。
    - ``mask_keys``：返回值前对指定 key 调用 ``_mask``（保留前 4 + 后 4）。
    """
    row = db.query(AppSetting).filter_by(key=key).first()
    merged = deepcopy(default_factory())
    if row and row.value_json:
        try:
            overrides = json.loads(row.value_json)
        except json.JSONDecodeError:
            overrides = {}
        if isinstance(overrides, dict):
            for k, v in overrides.items():
                if v in (None, "") and k in protect_keys:
                    continue  # 保留默认
                merged[k] = v
    for mk in mask_keys:
        if mk in merged and isinstance(merged[mk], str):
            merged[mk] = _mask(merged[mk])
    return merged


def save_app_setting_json(db: Session, key: str, value: dict) -> None:
    """把 dict 写到 app_settings.key=key 的 value_json 字段（不存在则新建）。"""
    row = db.query(AppSetting).filter_by(key=key).first()
    payload = json.dumps(value, ensure_ascii=False)
    if not row:
        row = AppSetting(key=key, value_json=payload)
        db.add(row)
    else:
        row.value_json = payload
    db.commit()


def _mask(secret: str) -> str:
    """保留前 4 + 后 4 位，中间 ****（避免 secret 全量进日志）。"""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "****"
    return secret[:4] + "****" + secret[-4:]


__all__ = [
    "AppSettingSpec",
    "ConfigRegistry",
    "CONFIG_REGISTRY",
    "load_app_setting_json",
    "save_app_setting_json",
]
