# tools/

CI gates, i18n checks, and the offline build toolchain. Product start is `deploy/dev` / `deploy/docker` only.

```bash
python tools/check_router_layer.py
python tools/ci_opencore_smoke.py
python tools/build_tool.py --mode demo
```

---

## Offline build

本目录也包含 OpenCore 仓配套的离线构建工具链：把仓库源码 + PostgreSQL 镜像打包成可离线部署的物料包。

> 本项目无任何商业 License 签发 / 校验逻辑。

## 功能（一次命令搞定）

```
清理物料包目录 → docker build → demo SQL 校验 → pack → 导出应用镜像 tar →
导出 PG 镜像 tar → 生成 docker-compose → 生成 install 脚本 → LF 规范化 → 检查产物结构
```

## 用法

```bash
# 一次性跑完所有步骤
python tools/build_tool.py --mode demo
python tools/build_tool.py --mode hotel

# 跳过 docker build（CI 用）
python tools/build_tool.py --mode demo --skip-build

# 跳过 pack（已有物料包时直接补全 compose/install）
python tools/build_tool.py --mode demo --skip-build --skip-pack

# 非交互（CI）
python tools/build_tool.py --mode demo --yes
```

PowerShell 一键入口：
```powershell
.\tools\run.ps1 -Mode demo            # 跑全流程
.\tools\run.ps1 -Mode demo -SkipBuild  # 仅生成 compose/install
```

## 输出物料包结构

物料包输出到 `deploy/offline-dist/<mode>/`，结构如下（demo/hotel 差异由 mode 决定）：

```
deploy/offline-dist/demo/
├── docker-compose.yml         # 编排
├── .env.example               # 环境变量模板
├── install.sh / install.ps1   # 跨平台一键安装
├── README.md                  # 物料包自带部署说明
├── db/                        # PG initdb 入口 + 01_ddl / 02_init / 03_demo
├── images/                    # 应用镜像 tar + PG 镜像 tar
├── build_report.md            # 构建报告（步骤记录）
└── build_manifest.json        # 机器可读产物清单
```

## 依赖

```bash
pip install -r tools/requirements.txt  # 仅 PyYAML
```

## 详细文档

- 构建步骤总览：`tools/build_tool.py --help`
- 物料包期望清单（`render_checklist` 输出）：见 `tools/fml_build/package_tree.py`
- DB 初始化脚本（PG init 时执行）：`db/postgres/docker-init.sh`
- 仓库根部署文档：[INSTALL.md](../INSTALL.md)（离线包中文手册：`docs/DEPLOY_zh.md`）
