# SPDX-License-Identifier: Apache-2.0
"""物料包目录树定义与复选框清单渲染（步骤 5）。

期望结构依据 README-DEPLOY.md 的「产出目录」描述 + pack.ps1 实际产出。
每个条目渲染 [x]（存在）/ [ ]（缺失），命令行与报告一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _postgres_tar_name(postgres_image: str) -> str:
    return postgres_image.replace(":", "_") + ".tar"


def build_expected_items(
    *,
    mode: str,
    image_name: str,
    image_tag: str,
    postgres_image: str,
    target: str = "auto",
) -> list[dict[str, Any]]:
    """返回期望条目；每个条目含 rel(相对包根), kind, required, note, children(可选)。"""
    app_tar = f"{image_name}_{image_tag}.tar"
    pg_tar = _postgres_tar_name(postgres_image)
    demo = mode.lower() == "demo"

    items: list[dict[str, Any]] = [
        {"rel": "docker-compose.yml", "kind": "file", "required": True, "note": "编排文件（按模式生成）"},
        {"rel": ".env.example", "kind": "file", "required": True, "note": "环境变量模板"},
        {
            "rel": "install.sh",
            "kind": "file",
            "required": target in ("auto", "linux"),
            "note": "一键安装脚本(bash/Linux/WSL/Git-Bash)",
        },
        {
            "rel": "install.ps1",
            "kind": "file",
            "required": target in ("auto", "windows"),
            "note": "一键安装脚本(Windows PowerShell)",
        },
        {"rel": "README.md", "kind": "file", "required": True, "note": "部署说明"},
        {
            "rel": "db",
            "kind": "dir",
            "required": True,
            "note": "数据库初始化 SQL（volume 挂载）",
            "children": [
                {"rel": "db/docker-init.sh", "kind": "file", "required": True, "note": "initdb 执行脚本"},
                {"rel": "db/01_ddl", "kind": "dir-sql", "required": True, "note": "表结构 DDL"},
                {"rel": "db/02_init", "kind": "dir-sql", "required": True, "note": "角色/权限/渠道初始化"},
                {
                    "rel": "db/03_demo",
                    "kind": "dir-sql",
                    "required": demo,
                    "note": "样例业务数据（demo 必须有 SQL；hotel 仅占位，符合预期）",
                    "demo_expects_sql": demo,
                },
            ],
        },
        {
            "rel": "images",
            "kind": "dir",
            "required": True,
            "note": "离线镜像 tar",
            "children": [
                {"rel": f"images/{app_tar}", "kind": "file", "required": True, "note": "应用镜像"},
                {"rel": f"images/{pg_tar}", "kind": "file", "required": True, "note": "Postgres 镜像"},
            ],
        },
    ]
    return items


def _render_tree(package_dir: Path, items: list[dict[str, Any]], prefix: str = "") -> list[str]:
    lines: list[str] = []
    box = lambda ok: "[x]" if ok else "[ ]"
    for item in items:
        rel = item["rel"]
        p = package_dir / rel
        exists = p.exists()
        if item["kind"] == "dir":
            ok = exists if item.get("required", True) else True
            lines.append(f"{prefix}{box(ok)} {rel}/   # {item['note']}")
            for c in item.get("children", []):
                lines.extend(_render_node(package_dir, c, prefix + "    "))
        elif item["kind"] == "dir-sql":
            has_sql = exists and bool(list(p.glob("*.sql")))
            demo_expects = item.get("demo_expects_sql", False)
            if demo_expects:
                ok = exists and has_sql
                note = item["note"] + ("" if (exists and has_sql) else "  ⚠ 缺 .sql")
            else:
                ok = exists
                note = item["note"] + ("" if exists else "  ⚠ 目录缺失")
            lines.append(f"{prefix}{box(ok)} {rel}/   # {note}")
        else:
            ok = exists
            lines.append(f"{prefix}{box(ok)} {rel}   # {item['note']}")
    return lines


def _render_node(package_dir: Path, item: dict[str, Any], prefix: str) -> list[str]:
    lines: list[str] = []
    box = lambda ok: "[x]" if ok else "[ ]"
    rel = item["rel"]
    p = package_dir / rel
    exists = p.exists()
    if item["kind"] == "dir":
        ok = exists if item.get("required", True) else True
        lines.append(f"{prefix}{box(ok)} {rel}/   # {item['note']}")
        for c in item.get("children", []):
            lines.extend(_render_node(package_dir, c, prefix + "    "))
    elif item["kind"] == "dir-sql":
        has_sql = exists and bool(list(p.glob("*.sql")))
        demo_expects = item.get("demo_expects_sql", False)
        if demo_expects:
            ok = exists and has_sql
            note = item["note"] + ("" if (exists and has_sql) else "  ⚠ 缺 .sql")
        else:
            ok = exists
            note = item["note"] + ("" if exists else "  ⚠ 目录缺失")
        lines.append(f"{prefix}{box(ok)} {rel}/   # {note}")
    else:
        ok = exists
        lines.append(f"{prefix}{box(ok)} {rel}   # {item['note']}")
    return lines


def render_checklist(
    package_dir: Path, *, mode: str, image_name: str, image_tag: str, postgres_image: str, target: str = "auto"
) -> list[str]:
    items = build_expected_items(
        mode=mode, image_name=image_name, image_tag=image_tag, postgres_image=postgres_image, target=target
    )
    return _render_tree(package_dir, items)


def summarize(
    package_dir: Path, *, mode: str, image_name: str, image_tag: str, postgres_image: str, target: str = "auto"
) -> dict[str, int]:
    items = build_expected_items(
        mode=mode, image_name=image_name, image_tag=image_tag, postgres_image=postgres_image, target=target
    )
    # count required missing among leaf + dir-sql
    missing = 0
    required = 0

    def walk(nodes):
        nonlocal missing, required
        for it in nodes:
            if it["kind"] in ("file", "dir-sql"):
                required += 1
                p = package_dir / it["rel"]
                ok = p.exists()
                if it["kind"] == "dir-sql":
                    demo_expects = it.get("demo_expects_sql", False)
                    if demo_expects:
                        ok = ok and bool(list(p.glob("*.sql")))
                if it.get("required", True) and not ok:
                    missing += 1
            elif it["kind"] == "dir":
                required += 1
                if it.get("required", True) and not (package_dir / it["rel"]).exists():
                    missing += 1
                walk(it.get("children", []))

    walk(items)
    return {"required": required, "missing": missing}


# 视为二进制的扩展名：跳过，不做换行符规范化
_BINARY_EXTS = {
    ".tar",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".pdf",
    ".ico",
    ".woff",
    ".woff2",
}


def normalize_line_endings(package_dir: Path, *, sample: int = 65536) -> dict[str, int]:
    """把物料包内所有文本文件统一规范为 LF（去掉 CRLF / CR）。

    动机：install.sh / db/*.sql / db/docker-init.sh / .env.example 等可能由
    pack.ps1 从 Windows 上的源码复制而来带 CRLF，而 bash 对 CRLF 零容忍
    （如 `set -euo pipefail\\r` => invalid option name）。此处兜底统一转 LF。

    返回 {"scanned", "fixed"}。仅当文件含 \\r 才重写，不影响已是 LF 的文件。
    """
    scanned = 0
    fixed = 0
    for p in sorted(package_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() in _BINARY_EXTS:
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        scanned += 1
        # 含 NUL 视为二进制，跳过
        if b"\x00" in data[:sample]:
            continue
        if b"\r\n" in data or b"\r" in data:
            text = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            p.write_bytes(text)
            fixed += 1
    return {"scanned": scanned, "fixed": fixed}
