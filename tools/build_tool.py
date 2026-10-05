#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""房满乐离线构建工具 · 命令行入口（在 PowerShell 中运行）。

功能（单一命令搞定）：
  0) 清理物料包目录（STEP 1，带确认——该目录位于源码根之下，防误删；--no-clean 跳过，--yes 非交互直删）
  1) 读取源码根目录（配置文件指定）
  2) 构建应用镜像（python 调 docker build）
  3) 构建物料包：复制仓库内已提交的样例数据 SQL（零 SQLite 依赖，无需导出）
  4) 打包离线目录（调 deploy/offline/pack.ps1）
  5) 检查产出目录结构（复选框标注文件是否存在）
  6) 按模式生成 docker-compose.yml（volume 挂载；差异在是否加载样例数据）
  7) 生成完整物料包目录 + install.sh / install.ps1（跨平台）

环境要求（无需 venv）：
  - 直接用系统 Python 运行，例如（按你实际环境替换路径）：
        E:/Dev/Python/python314/python.exe build_tool.py ...
  - 依赖只有 PyYAML。
    若运行时报 ModuleNotFoundError，用「你运行的那个 python 对应的 pip」安装一次即可：
        E:/Dev/Python/python314/python.exe -m pip install -r requirements.txt
  - 本工具不会创建虚拟环境，所有依赖装在你的系统 Python 里。

用法：
  E:/Dev/Python/python314/python.exe build_tool.py --config build_config.yaml --mode demo
  E:/Dev/Python/python314/python.exe build_tool.py --mode hotel
  E:/Dev/Python/python314/python.exe build_tool.py --mode demo --skip-build --skip-pack   # 仅生成 compose/install 并检查
  .\run.ps1 -Mode demo            # PowerShell 一键入口（run.ps1 内已固定 python 路径）

选项：
  --config PATH    配置文件（默认 build_config.yaml）
  --mode MODE      demo | hotel（覆盖配置中的 mode）
  --skip-build     跳过 docker build
  --skip-pack      跳过 pack.ps1（直接写入已有物料包目录）
  --skip-images    跳过 docker save 导出镜像 tar
  --yes, -y        非交互：跳过 STEP 1 的清理确认，直接删除物料包目录（CI/脚本使用，需明确知晓风险）
  --no-clean       跳过物料包目录清理（保留现有文件，可能含陈旧数据）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fml_build.config import BuildConfig, ConfigError, load_config
from fml_build.runner import BuildOptions, BuildRunner


def _check_deps() -> int | None:
    """依赖自检：缺 yaml 时给出明确安装提示，避免 ModuleNotFoundError 不知所措。"""
    missing: list[str] = []
    for mod in ("yaml",):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"[依赖缺失] 未安装: {', '.join(missing)}", file=sys.stderr)
        print("请用「你运行的那个 python 对应的 pip」安装一次：", file=sys.stderr)
        print("    <你的 python> -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="build_tool", description="房满乐 PMS 离线构建工具")
    ap.add_argument("--config", default="build_config.yaml", help="配置文件路径（YAML/JSON）")
    ap.add_argument("--mode", choices=["demo", "hotel"], default=None, help="覆盖配置中的 mode")
    ap.add_argument("--skip-build", action="store_true", help="跳过 docker build")
    ap.add_argument("--skip-pack", action="store_true", help="跳过 pack.ps1（直接写入已有物料包目录）")
    ap.add_argument("--skip-images", action="store_true", help="跳过 docker save 导出镜像 tar")
    ap.add_argument(
        "--yes", "-y", action="store_true", help="非交互：跳过清理确认直接删除物料包目录（CI/脚本用，需明确知晓风险）"
    )
    ap.add_argument("--no-clean", action="store_true", help="跳过物料包目录清理（保留现有文件，可能含陈旧数据）")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rc = _check_deps()
    if rc is not None:
        return rc
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"[配置错误] {e}", file=sys.stderr)
        return 2

    mode = args.mode or cfg.mode
    opts = BuildOptions(
        skip_build=args.skip_build,
        skip_pack=args.skip_pack,
        skip_images=args.skip_images,
        yes=args.yes,
        no_clean=args.no_clean,
    )

    runner = BuildRunner(cfg, mode)
    try:
        runner.run(opts)
    except Exception as e:
        print(f"\n[构建中断] {e}", file=sys.stderr)
        # 仍尝试写报告（含失败步骤）
        try:
            pkg = cfg.package_dir(mode)
            runner._write_report(pkg, None)
            print(f"[报告] 已写部分报告: {pkg / cfg.output.get('report', 'build_report.md')}", file=sys.stderr)
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
