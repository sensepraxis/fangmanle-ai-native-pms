# SPDX-License-Identifier: Apache-2.0
"""构建编排 + 步骤记录 + 报告生成。

每步都有：序号、名称、命令、开始/结束时间、状态、输出摘要。
最终产出 build_report.md 与 build_manifest.json（写到物料包目录）。
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fml_build import compose_gen, docker_ops, install_gen, install_ps1, package_tree
from fml_build.config import BuildConfig


@dataclass
class Step:
    index: int
    name: str
    command: str
    started: str
    ended: str = ""
    status: str = "PENDING"  # OK / FAIL / SKIP
    output: str = ""
    error: str = ""


class BuildRunner:
    def __init__(self, cfg: BuildConfig, mode: str):
        self.cfg = cfg
        self.mode = mode.lower()
        self.steps: list[Step] = []
        self._idx = 0

    # ---- 步骤执行器 ----
    def step(self, name: str, command: str, fn: Callable[[], Any], *, optional: bool = False) -> Any:
        self._idx += 1
        idx = self._idx
        s = Step(index=idx, name=name, command=command, started=_now())
        self.steps.append(s)
        banner = f"──── STEP {idx}  {name} {'─' * max(2, 28 - len(name))}"
        print(f"\n{banner}")
        if command:
            print(f"$ {command}")
        try:
            result = fn()
            s.status = "OK"
            s.ended = _now()
            if isinstance(result, docker_ops.RunResult):
                s.output = result.output
                tail = result.output.strip().splitlines()[-12:]
                for line in tail:
                    print("   " + line)
                if not result.ok:
                    raise RuntimeError(f"命令返回非零退出码 {result.returncode}")
            print(f"[OK] {name} 完成（{s.ended}）")
            return result
        except Exception as e:
            s.status = "FAIL"
            s.error = str(e)
            s.ended = _now()
            print(f"[FAIL] {name}: {e}")
            if optional:
                return None
            raise

    def skip(self, name: str, reason: str) -> None:
        self._idx += 1
        s = Step(index=self._idx, name=name, command="(skipped)", started=_now(), ended=_now(), status="SKIP")
        s.output = reason
        self.steps.append(s)
        print(f"\n──── STEP {self._idx}  {name} ────\n[SKIP] {reason}")

    # ---- 编排 ----
    def run(self, opts: "BuildOptions") -> Path:
        cfg = self.cfg
        mode = self.mode
        pkg = cfg.package_dir(mode)
        print(f"\n=== 房满乐离线构建 · 模式={mode} · 镜像={cfg.image_ref} ===")
        print(f"源码根: {cfg.source_root}")
        print(f"物料包: {pkg}")

        # 1. 清理物料包目录（带确认，防止误删源码根目录）
        self._clean_package_step(pkg, cfg.source_root, mode, opts)

        # 2. 构建应用镜像
        if opts.skip_build:
            self.skip("构建应用镜像", "--skip-build 已指定")
        else:
            if not docker_ops.have_docker():
                raise RuntimeError("本机未检测到 docker，请先启动 Docker Desktop，或用 --skip-build 跳过")
            self.step(
                "构建应用镜像",
                f"docker build -t {cfg.image_ref} .",
                lambda: docker_ops.docker_build(
                    source_root=cfg.source_root, image_name=cfg.image_name, image_tag=cfg.image_tag
                ),
            )

        # 3. 校验样例数据 SQL（仅 demo；数据已随仓库提交，零 SQLite 依赖，无需导出）
        if mode == "hotel":
            self.skip("校验样例数据 SQL", "hotel 模式不含样例数据（仅 DDL + 初始化）")
        else:
            demo_sql = cfg.source_root / "db" / "postgres" / "03_demo" / "010_full_demo_data.sql"

            def _check_demo_sql():
                if not demo_sql.exists():
                    raise RuntimeError(
                        f"缺少样例数据 SQL: {demo_sql}\n"
                        "demo 数据现已由 PostgreSQL 原生生成并提交到仓库（零 SQLite 依赖）。\n"
                        "若需重新生成，见 db/postgres/03_demo/refresh_demo.sh"
                        "（基于本地 fml_seed 容器 pg_dump）。"
                    )
                return demo_sql

            self.step(
                "校验样例数据 SQL",
                f"check {demo_sql}",
                _check_demo_sql,
            )

        # 4. 打包离线目录（pack.ps1）
        if opts.skip_pack:
            self.skip("打包离线目录", "--skip-pack 已指定（将直接写入已有物料包目录）")
        else:
            if not docker_ops.have_docker() and cfg.export_images:
                raise RuntimeError(
                    "export_images=true 但本机无 docker，无法 docker save；请设 export_images=false 并依赖 pack.ps1，或用 --skip-pack"
                )
            self.step(
                "打包离线目录",
                f"pack.ps1 -Edition {mode} -Tag {cfg.image_tag}" + (" -SkipSave" if cfg.export_images else ""),
                lambda: docker_ops.pack_offline(
                    pack_ps1=cfg.pack_ps1_path(),
                    source_root=cfg.source_root,
                    mode=mode,
                    image_tag=cfg.image_tag,
                    skip_save=cfg.export_images,
                ),
            )

        # 5. 导出镜像 tar（工具自己 docker save）
        if cfg.export_images and not opts.skip_images:
            app_tar = pkg / "images" / f"{cfg.image_name}_{cfg.image_tag}.tar"
            pg_tar = pkg / "images" / (cfg.postgres_image.replace(":", "_") + ".tar")

            def _save_app():
                return docker_ops.ensure_and_save_image(image_ref=cfg.image_ref, tar_path=app_tar)

            def _save_pg():
                return docker_ops.ensure_and_save_image(image_ref=cfg.postgres_image, tar_path=pg_tar)

            self.step("导出应用镜像 tar", f"docker save -o {app_tar}", _save_app)
            self.step("导出 Postgres 镜像 tar", f"docker save -o {pg_tar}", _save_pg)
        elif opts.skip_images:
            self.skip("导出镜像 tar", "--skip-images 已指定")
        else:
            self.skip("导出镜像 tar", "export_images=false，已由 pack.ps1 负责")

        # 6. 生成 docker-compose.yml
        def _compose():
            content = compose_gen.generate_compose(
                mode=mode, image_name=cfg.image_name, image_tag=cfg.image_tag, postgres_image=cfg.postgres_image
            )
            (pkg / "docker-compose.yml").write_text(content, encoding="utf-8", newline="\n")
            return None

        self.step("生成 docker-compose.yml", f"write {pkg}/docker-compose.yml", _compose)

        # 7. 生成安装脚本（跨平台：install.sh / install.ps1）
        target = cfg.deploy_target

        def _install():
            generated: list[str] = []
            if target in ("auto", "linux"):
                (pkg / "install.sh").write_text(
                    install_gen.generate_install_sh(mode=mode), encoding="utf-8", newline="\n"
                )
                generated.append("install.sh")
            if target in ("auto", "windows"):
                (pkg / "install.ps1").write_text(
                    install_ps1.generate_install_ps1(mode=mode), encoding="utf-8", newline="\n"
                )
                generated.append("install.ps1")
            if target == "windows":
                # windows 模式不需要 bash 脚本，清理 pack 模板可能带入的 install.sh
                sh = pkg / "install.sh"
                if sh.exists():
                    sh.unlink()
            return generated

        install_files = self.step(
            "生成安装脚本",
            f"write {pkg}/install.{{sh,ps1}} (target={target})",
            _install,
        )

        # 7b. 全包换行符规范化（LF），覆盖 pack.ps1 复制来的 .env.example / db/*.sql 等
        def _normalize():
            return package_tree.normalize_line_endings(pkg)

        norm = self.step("全包换行符规范化(LF)", f"normalize {pkg}", _normalize)

        # 8. 检查目录结构
        def _check():
            lines = package_tree.render_checklist(
                pkg,
                mode=mode,
                image_name=cfg.image_name,
                image_tag=cfg.image_tag,
                postgres_image=cfg.postgres_image,
                target=cfg.deploy_target,
            )
            summary = package_tree.summarize(
                pkg,
                mode=mode,
                image_name=cfg.image_name,
                image_tag=cfg.image_tag,
                postgres_image=cfg.postgres_image,
                target=cfg.deploy_target,
            )
            for ln in lines:
                print("   " + ln)
            print(f"   必需项 {summary['required']} · 缺失 {summary['missing']}")
            return {"lines": lines, "summary": summary}

        chk = self.step("检查物料包目录结构", f"check {pkg}", _check)

        # 9. 写报告
        self._write_report(pkg, chk, install_files, norm)
        print(f"\n=== 完成。物料包目录：{pkg} ===")
        return pkg

    # ---- 物料包目录清理（带确认，安全护栏） ----
    def _safe_to_clean(self, pkg: Path, source_root: Path, mode: str) -> tuple[bool, str]:
        """多重安全检查：只删除「预期的离线包目录」，拒绝删除源码根目录或其上级目录。

        允许删除的范围：deploy/offline-dist/<mode>，或配置的 output.dir/<mode>。
        返回 (是否允许删除, 拒绝原因)。
        """
        pkg_abs = pkg.resolve()
        src_abs = source_root.resolve()

        if pkg_abs == src_abs:
            return False, "物料包目录与源码根目录完全相同"
        # pkg 是源码根的上级/祖先 -> 禁止（否则会删掉源码根甚至更上层）
        if pkg_abs in src_abs.parents:
            return False, "物料包目录位于源码根目录之上（是其祖先），禁止删除"
        # 末级名必须与模式一致，避免误删 offline-dist 下的其它版本目录
        if pkg_abs.name != mode:
            return False, f"物料包目录末级名({pkg_abs.name})与模式({mode})不符"
        # 必须位于预期的离线包基目录之下（构建工具/deploy/offline-dist 或配置的 output.dir）
        expected_base = self.cfg.tool_root / "deploy" / "offline-dist"
        out_dir = self.cfg.output.get("dir")
        if out_dir:
            ob = Path(out_dir)
            if not ob.is_absolute():
                ob = self.cfg.config_path.parent / ob
            ob = ob.resolve()
            if expected_base not in pkg_abs.parents and ob not in pkg_abs.parents:
                return False, "物料包目录不在 deploy/offline-dist 之下，也不在配置的 output.dir 之下"
        else:
            if expected_base not in pkg_abs.parents:
                return False, "物料包目录不在 deploy/offline-dist 之下（请检查 output.dir 配置）"
        return True, ""

    def _clean_package_step(self, pkg: Path, source_root: Path, mode: str, opts: "BuildOptions") -> None:
        """STEP 1：清理物料包目录。带确认；非交互用 --yes 跳过确认；--no-clean 完全跳过。"""
        self._idx += 1
        idx = self._idx
        s = Step(
            index=idx, name="清理物料包目录(带确认)", command="(rmtree if confirmed)", started=_now(), ended=_now()
        )
        self.steps.append(s)
        print(f"\n──── STEP {idx}  清理物料包目录(带确认) {'─' * 18}")

        if opts.no_clean:
            s.status = "SKIP"
            s.output = "--no-clean 已指定，保留现有物料包（可能含陈旧文件）"
            print(f"[SKIP] {s.output}")
            return

        if not pkg.exists():
            s.status = "SKIP"
            s.output = f"目录不存在，无需清理: {pkg}"
            print(f"[SKIP] {s.output}")
            return

        ok, reason = self._safe_to_clean(pkg, source_root, mode)
        if not ok:
            s.status = "FAIL"
            s.ended = _now()
            s.error = reason
            raise RuntimeError(
                f"拒绝清理物料包目录（安全检查未通过）：{reason}\n"
                f"路径: {pkg}\n"
                "这是保护措施，避免误删源码根目录。请检查 build_config.yaml 的 output.dir 与 project.source_root。"
            )

        if opts.yes:
            print(f"[确认] --yes 已指定（非交互），将直接删除：{pkg}")
            do_delete = True
        else:
            print("")
            print("  ⚠️  即将删除物料包目录（位于构建工具 deploy/offline-dist 之下，删除不可恢复）：")
            print(f"       {pkg}")
            print("  ⚠️  该目录是构建工具下的离线物料包，误删请确认不影响源码工程。")
            try:
                ans = input("  确认删除请输入 yes （其他任意输入将跳过清理并继续）：").strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = ""
            if ans != "yes":
                s.status = "SKIP"
                s.output = "用户未确认，跳过清理（保留现有物料包，可能含陈旧文件）"
                print(f"[SKIP] {s.output}")
                return
            do_delete = True

        if do_delete:
            shutil.rmtree(pkg)
            s.status = "OK"
            s.output = f"已清理: {pkg}"
            print(f"[OK] 已清理物料包目录: {pkg}")

    # ---- 报告 ----
    def _write_report(
        self, pkg: Path, chk: dict | None = None, install_files: list | None = None, norm: dict | None = None
    ) -> None:
        report_name = self.cfg.output.get("report", "build_report.md")
        manifest_name = self.cfg.output.get("manifest", "build_manifest.json")
        pkg.mkdir(parents=True, exist_ok=True)

        lines = ["# 房满乐离线构建报告", ""]
        lines.append(f"- 模式: **{self.mode}**")
        lines.append(f"- 镜像: `{self.cfg.image_ref}`")
        lines.append(f"- 时间: {_now()}")
        lines.append(f"- 物料包: `{pkg}`")
        lines.append(
            f"- 部署目标: `{self.cfg.deploy_target}`（安装脚本：{', '.join(install_files) if install_files else '无'}）"
        )
        if norm:
            lines.append(f"- 换行符规范化: 扫描 {norm.get('scanned')} 个文件，修正 CRLF {norm.get('fixed')} 个")
        lines.append("")
        lines.append("## 步骤记录")
        lines.append("")
        lines.append("| # | 步骤 | 状态 | 命令 |")
        lines.append("|---|------|------|------|")
        for s in self.steps:
            cmd = s.command if s.command != "(skipped)" else "—"
            lines.append(f"| {s.index} | {s.name} | {s.status} | `{cmd}` |")
        lines.append("")
        if chk:
            lines.append("## 物料包目录检查")
            lines.append("")
            for ln in chk.get("lines", []):
                lines.append("    " + ln)
            sm = chk.get("summary", {})
            lines.append("")
            lines.append(f"必需项 {sm.get('required')} · 缺失 {sm.get('missing')}")
            lines.append("")

        report_path = pkg / report_name
        report_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"[OK] 报告已写: {report_path}")

        manifest = {
            "mode": self.mode,
            "image_ref": self.cfg.image_ref,
            "package_dir": str(pkg),
            "generated_at": _now(),
            "steps": [
                {
                    "index": s.index,
                    "name": s.name,
                    "status": s.status,
                    "command": s.command,
                    "started": s.started,
                    "ended": s.ended,
                    "error": s.error,
                }
                for s in self.steps
            ],
            "checklist": chk.get("summary") if chk else None,
        }
        (pkg / manifest_name).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class BuildOptions:
    skip_build: bool = False
    skip_pack: bool = False
    skip_images: bool = False
    yes: bool = False  # 非交互：跳过清理确认直接删除
    no_clean: bool = False  # 跳过物料包目录清理
