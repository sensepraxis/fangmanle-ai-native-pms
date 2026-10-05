# SPDX-License-Identifier: Apache-2.0
"""通过 Python 调用 docker / powershell / python 完成外部命令（步骤 2/3/4 与镜像导出）。

所有函数返回 RunResult(cmd, returncode, output)；失败时由调用方决定是否抛错。
统一把 stdout+stderr 合并捕获，便于写入步骤记录。
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    cmd: str
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _quote(args: list[str]) -> str:
    out = []
    for a in args:
        if " " in a or "\\" in a:
            out.append(f'"{a}"')
        else:
            out.append(a)
    return " ".join(out)


def run(cmd_args: list[str], cwd: Path | None = None, timeout: int = 1800) -> RunResult:
    """执行命令并返回合并输出。"""
    try:
        proc = subprocess.run(
            cmd_args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"命令超时（>{timeout}s）: {_quote(cmd_args)}") from e
    out = proc.stdout or ""
    return RunResult(cmd=_quote(cmd_args), returncode=proc.returncode, output=out)


def have_docker() -> bool:
    try:
        r = run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=30)
        return r.ok
    except Exception:
        return False


def docker_build(*, source_root: Path, image_name: str, image_tag: str, timeout: int = 1800) -> RunResult:
    return run(
        ["docker", "build", "-f", "deploy/docker/Dockerfile", "-t", f"{image_name}:{image_tag}", "."],
        cwd=source_root,
        timeout=timeout,
    )


def pack_offline(
    *,
    pack_ps1: Path,
    source_root: Path,
    mode: str,
    image_tag: str,
    skip_save: bool,
    timeout: int = 600,
) -> RunResult:
    # pack.ps1 现在位于构建工具 deploy/offline 下；db 源来自源码工程，
    # 必须显式传 -SourceRoot，否则打包进去的 db SQL 不是最新。
    args = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(pack_ps1),
        "-Edition",
        mode,
        "-Tag",
        image_tag,
        "-SourceRoot",
        str(source_root),
    ]
    if skip_save:
        args.append("-SkipSave")
    return run(args, timeout=timeout)


def docker_image_exists(image_ref: str) -> bool:
    r = run(["docker", "image", "inspect", image_ref], timeout=30)
    return r.ok


def docker_pull(image_ref: str, timeout: int = 600) -> RunResult:
    return run(["docker", "pull", image_ref], timeout=timeout)


def docker_save(*, image_ref: str, tar_path: Path, timeout: int = 600) -> RunResult:
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    return run(["docker", "save", "-o", str(tar_path), image_ref], timeout=timeout)


def ensure_and_save_image(*, image_ref: str, tar_path: Path, timeout: int = 600) -> RunResult:
    """确保镜像存在（不存在则 pull），再 docker save 到 tar。"""
    if not docker_image_exists(image_ref):
        pr = docker_pull(image_ref, timeout=timeout)
        if not pr.ok:
            return pr
    return docker_save(image_ref=image_ref, tar_path=tar_path, timeout=timeout)
