# SPDX-License-Identifier: Apache-2.0
"""配置加载与校验（YAML 优先，缺失 pyyaml 时回退 JSON）。

配置以本文件所在工具的「配置文件路径」为基准解析相对路径，
但也兼容以工具根目录为基准。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    pass


def _load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            # 没有 pyyaml 时尝试按 JSON 解析（仅当文件确实是 JSON）
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                raise ConfigError("未安装 pyyaml，且配置文件不是合法 JSON。请 `pip install pyyaml` 或改用 .json 配置。")
        return yaml.safe_load(text) or {}
    # .json 或其它
    return json.loads(text)


class BuildConfig:
    def __init__(self, raw: dict[str, Any], config_path: Path):
        self.config_path = config_path
        self.tool_root = config_path.resolve().parent
        self.raw = raw

    # ---- 便捷读取 ----
    @property
    def project(self) -> dict[str, Any]:
        return self.raw.get("project", {}) or {}

    @property
    def source_root(self) -> Path:
        v = self.project.get("source_root")
        if not v:
            raise ConfigError("project.source_root 不能为空")
        p = Path(v)
        if not p.is_absolute():
            # 先按相对配置文件，再按相对工具根
            cand = self.config_path.parent / p
            if cand.exists():
                p = cand
            else:
                p = self.tool_root / p
        return p.resolve()

    @property
    def image_name(self) -> str:
        return self.project.get("image_name", "fangmanle-pms")

    @property
    def image_tag(self) -> str:
        return str(self.project.get("image_tag", "1.0.0"))

    @property
    def image_ref(self) -> str:
        return f"{self.image_name}:{self.image_tag}"

    @property
    def postgres_image(self) -> str:
        return self.project.get("postgres_image", "postgres:16-alpine")

    @property
    def mode(self) -> str:
        m = (self.raw.get("mode") or "demo").lower()
        if m not in ("demo", "hotel"):
            raise ConfigError(f"mode 必须为 demo 或 hotel，收到: {m}")
        return m

    @property
    def pack(self) -> dict[str, Any]:
        return self.raw.get("pack", {}) or {}

    @property
    def use_pack_ps1(self) -> bool:
        return bool(self.pack.get("use_pack_ps1", True))

    @property
    def export_images(self) -> bool:
        return bool(self.pack.get("export_images", True))

    @property
    def output(self) -> dict[str, Any]:
        return self.raw.get("output", {}) or {}

    @property
    def deploy(self) -> dict[str, Any]:
        return self.raw.get("deploy", {}) or {}

    @property
    def deploy_target(self) -> str:
        """安装入口脚本目标平台：auto（同时生成 sh+ps1）/ linux（仅 sh）/ windows（仅 ps1）。"""
        t = (self.deploy.get("target") or "auto").lower()
        if t not in ("auto", "linux", "windows"):
            raise ConfigError(f"deploy.target 必须为 auto/linux/windows，收到: {t}")
        return t

    def package_dir(self, mode: str | None = None) -> Path:
        """最终物料包目录。"""
        m = mode or self.mode
        out_dir = self.output.get("dir")
        if out_dir:
            p = Path(out_dir)
            if not p.is_absolute():
                p = (self.config_path.parent / p).resolve()
            return (p / m).resolve()
        # 默认使用 pack.ps1 产出位置（deploy 已迁移至构建工具仓库自身目录）
        return (self.tool_root / "deploy" / "offline-dist" / m).resolve()

    def pack_ps1_path(self) -> Path:
        # deploy 已迁移至构建工具仓库（与配置文件同根）
        return (self.tool_root / "deploy" / "offline" / "pack.ps1").resolve()

    def validate(self) -> None:
        if not self.source_root.exists():
            raise ConfigError(f"源码根目录不存在: {self.source_root}")
        if not self.pack_ps1_path().exists() and self.use_pack_ps1:
            raise ConfigError(f"pack.ps1 不存在: {self.pack_ps1_path()}")


def load_config(path: str | Path) -> BuildConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"配置文件不存在: {p}")
    raw = _load_raw(p)
    cfg = BuildConfig(raw, p)
    cfg.validate()
    return cfg
