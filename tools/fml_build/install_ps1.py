# SPDX-License-Identifier: Apache-2.0
"""生成 install.ps1（Windows PowerShell 安装入口，步骤 7 的跨平台补充）。

逻辑与 install.sh 完全等价：
1) 缺 .env 则复制 .env.example 并自动生成强随机密码 / JWT 密钥
2) 逐个 docker load images/*.tar
3) 启动服务：使用目标服务器的 Docker Compose V2（docker compose 子命令 / docker-compose-plugin）。
   本产品只支持 V2；V1（docker-compose 1.x）在新 Engine 上会崩溃，已不再兼容，也不自带二进制。

所有文本一律 LF（由写入方以 newline="\\n" 落盘），原生 PowerShell 可直接执行。
"""

from __future__ import annotations

_INSTALL_PS1_TPL = """\
# 房满乐 PMS · 一键安装（Windows PowerShell，由 fangmanle-docker-build-tool 生成，模式: __MODE__）
# 运行（在物料包目录内）：
#   powershell -ExecutionPolicy Bypass -File install.ps1
# 或先 Set-ExecutionPolicy RemoteSigned，再 .\\install.ps1
$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $ScriptDir

if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host '✅ 已生成 .env 并自动填入强随机密码 / JWT 密钥（无需手动修改）。'
  function New-RandStr($n) {
    $b = New-Object byte[] $n
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    $s = [Convert]::ToBase64String($b) -replace '[^a-zA-Z0-9]', ''
    return $s.Substring(0, [Math]::Min($n, $s.Length))
  }
  $pw = New-RandStr 24
  $jwt = New-RandStr 48
  $txt = [System.IO.File]::ReadAllText("$ScriptDir/.env")
  $txt = $txt -replace '(?m)^POSTGRES_PASSWORD=.*', "POSTGRES_PASSWORD=$pw"
  $txt = $txt -replace '(?m)^FML_JWT_SECRET=.*', "FML_JWT_SECRET=$jwt"
  [System.IO.File]::WriteAllText("$ScriptDir/.env", $txt, [System.Text.Encoding]::UTF8)
  Write-Host '   如需查看：Select-String -Path .env -Pattern "POSTGRES_PASSWORD|FML_JWT_SECRET"'
}

foreach ($f in @(Get-ChildItem 'images/*.tar' -ErrorAction SilentlyContinue)) {
  if (-not $f) { continue }
  Write-Host "docker load -i $($f.FullName)"
  docker load -i "$($f.FullName)"
}

# ── Compose 检测（仅支持 V2）─────────────────────────────
# 本产品只支持 Docker Compose V2（docker compose 子命令 / docker-compose-plugin）。
# V1（docker-compose 1.x）在新 Docker Engine 上读镜像元数据字段会崩溃，已不再兼容。
# 直接使用目标服务器系统安装的 V2 插件；不自带二进制、不在线下载。
$DC = $null

# 系统 docker compose (V2 插件)
docker compose version 2>$null
if ($LASTEXITCODE -eq 0) {
  $DC = 'docker compose'
  Write-Host '[compose] 使用系统 docker compose (V2 插件)'
}

if (-not $DC) {
  Write-Host ''
  Write-Host '============================================'
  Write-Host '  错误：未找到 Docker Compose V2'
  Write-Host '============================================'
  Write-Host ''
  Write-Host '本产品要求 Docker Compose V2（docker compose 子命令）。'
  Write-Host '请在目标服务器安装 V2 插件后重试：'
  Write-Host ''
  Write-Host '  A. Windows：安装 Docker Desktop（内含 Compose V2 插件）'
  Write-Host '     https://www.docker.com/products/docker-desktop/'
  Write-Host ''
  Write-Host '  B. Linux 参考官方文档：https://docs.docker.com/compose/install/'
  Write-Host ''
  exit 1
}

# ── 预清理（幂等自愈）─────────────────────────────
# 启动前先停掉本项目上一次部署，避免端口占用、陈旧网络、以及 PG 数据卷残留旧密码。
#   demo 模式：down -v 一并删除数据卷，PG 会用 .env 当前密码重新初始化。
#   hotel/生产：仅 down（不加 -v），保留数据卷不丢业务数据。
Write-Host '[compose] 预清理旧部署：docker compose down --remove-orphans__DOWN_EXTRA__'
& $DC down --remove-orphans__DOWN_EXTRA__ 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host '  (无旧资源或可忽略)' }

Write-Host '[compose] 启动服务 ...'
& $DC up -d
& $DC ps
Write-Host ''
Write-Host '✅ 完成。默认端口见 .env 中 PMS_PORT（一般为 __APP_PORT__）'
"""


def generate_install_ps1(*, mode: str, app_port: int = 8000) -> str:
    # 注意：不能用 .format()，PowerShell 脚本里的 { } 会被当成占位符导致 KeyError。
    # 改用不含 { } 的占位符 __MODE__ / __APP_PORT__ / __DOWN_EXTRA__ 做 replace。
    # demo 模式清数据卷（重新初始化，解决旧密码不匹配）；其它模式保留数据卷。
    extra_down = " -v" if mode.lower() == "demo" else ""
    return (
        _INSTALL_PS1_TPL.replace("__MODE__", mode.lower())
        .replace("__APP_PORT__", str(app_port))
        .replace("__DOWN_EXTRA__", extra_down)
    )
