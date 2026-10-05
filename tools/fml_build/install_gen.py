# SPDX-License-Identifier: Apache-2.0
"""生成 install.sh（步骤 7）。

逻辑与原 deploy/offline 模板一致：
1) 缺 .env 则复制 .env.example 并自动生成强随机密码 / JWT 密钥
2) 逐个 load images/*.tar
3) 启动服务：使用目标服务器的 Docker Compose V2（docker compose 子命令 / docker-compose-plugin）。
   本产品只支持 V2；V1（docker-compose 1.x）在新 Engine 上会崩溃，已不再兼容，也不自带二进制。
"""

from __future__ import annotations

_INSTALL_TPL = """\
#!/usr/bin/env bash
# 房满乐 PMS · 一键安装（由 fangmanle-docker-build-tool 生成，模式: {mode}）
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "✅ 已生成 .env 并自动填入强随机密码 / JWT 密钥（无需手动修改）。"
  if command -v python3 >/dev/null 2>&1; then
    _PW=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))" 2>/dev/null)
    _JWT=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))" 2>/dev/null)
  fi
  if [[ -z "${{_PW:-}}" ]] && command -v openssl >/dev/null 2>&1; then
    _PW=$(openssl rand -base64 24 2>/dev/null | tr -d '/+' | head -c 24)
  fi
  if [[ -z "${{_JWT:-}}" ]] && command -v openssl >/dev/null 2>&1; then
    _JWT=$(openssl rand -base64 48 2>/dev/null | tr -d '/+' | head -c 48)
  fi
  if [[ -z "${{_PW:-}}" ]]; then
    _PW=$(head -c 24 /dev/urandom | base64 | tr -d '/+')
  fi
  if [[ -z "${{_JWT:-}}" ]]; then
    _JWT=$(head -c 48 /dev/urandom | base64 | tr -d '/+')
  fi
  sed -i -E "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${{_PW}}|" .env
  sed -i -E "s|^FML_JWT_SECRET=.*|FML_JWT_SECRET=${{_JWT}}|" .env
  echo "   如需查看：grep -E 'POSTGRES_PASSWORD|FML_JWT_SECRET' .env"
fi

for f in images/*.tar; do
  [[ -e "$f" ]] || continue
  echo "docker load -i $f"
  docker load -i "$f"
done

# ── Docker Compose 检测（仅支持 V2）─────────────────────────────
# 本产品只支持 Docker Compose V2（docker compose 子命令 / docker-compose-plugin）。
# V1（docker-compose 1.x）在新 Docker Engine 上读镜像元数据字段会崩溃，已不再兼容。
# 直接使用目标服务器系统安装的 V2 插件；不自带二进制、不在线下载。

_DC=""
if docker compose version >/dev/null 2>&1; then
  _DC="docker compose"
  echo "[compose] 使用系统 docker compose (V2 插件)"
fi

if [[ -z "$_DC" ]]; then
  echo ""
  echo "============================================"
  echo "  错误：未找到 Docker Compose V2"
  echo "============================================"
  echo ""
  echo "本产品要求 Docker Compose V2（docker compose 子命令）。"
  echo "请在目标服务器安装 V2 插件后重跑："
  echo ""
  echo '  A. 官方 apt 源安装 docker-compose-plugin（推荐，Ubuntu）：'
  echo '     sudo install -m 0755 -d /etc/apt/keyrings'
  echo '     sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc'
  echo '     sudo chmod a+r /etc/apt/keyrings/docker.asc'
  echo '     echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
  echo '     sudo apt-get update && sudo apt-get install -y docker-compose-plugin'
  echo '     # 若 docker compose version 仍报 unknown command，软链插件到必扫目录：'
  echo '     sudo mkdir -p /usr/local/lib/docker/cli-plugins'
  echo '     sudo ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose'
  echo ""
  echo '  B. 其他平台参考官方文档：https://docs.docker.com/compose/install/'
  echo ""
  exit 1
fi

# ── 预清理（幂等自愈）─────────────────────────────
# 启动前先停掉本项目上一次部署，避免：端口占用(8000)、陈旧网络导致 db 解析失败、
# 以及 PostgreSQL 数据卷残留旧密码导致 password authentication failed。
#   demo 模式：down -v 一并删除数据卷，PG 会用 .env 当前密码重新初始化。
#   hotel/生产：仅 down（不加 -v），保留数据卷不丢业务数据。
echo "[compose] 预清理旧部署：docker compose down --remove-orphans{extra_down}"
$_DC down --remove-orphans{extra_down} || true

echo "[compose] 启动服务 ..."
$_DC up -d
$_DC ps
echo ""
echo "✅ 完成。默认端口见 .env 中 PMS_PORT（一般为 {app_port}）"
"""


def generate_install_sh(*, mode: str, app_port: int = 8000) -> str:
    # demo 模式清数据卷（重新初始化，解决旧密码不匹配）；其它模式保留数据卷。
    extra_down = " -v" if mode.lower() == "demo" else ""
    return _INSTALL_TPL.format(mode=mode.lower(), app_port=app_port, extra_down=extra_down)
