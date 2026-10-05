# 房满乐离线构建工具 · PowerShell 一键入口
# 直接调用系统 Python 运行（不使用 venv）。
#
#   .\tools\run.ps1 -Mode demo           # 等价于 python tools/build_tool.py --config tools/build_config.yaml --mode demo
#   .\tools\run.ps1 -Mode hotel
#   .\tools\run.ps1 -Mode demo -Yes     # 非交互
#   .\tools\run.ps1 -SkipBuild -SkipImages   # 仅 compose/install

# Python 解释器：默认使用系统 python；如需指定，改为绝对路径
# 例如：C:\Python312\python.exe
$Python = "python"

param(
  [string]$Mode = "",
  [string]$Config = "build_config.yaml",
  [switch]$Yes,
  [switch]$NoClean,
  [switch]$SkipBuild,
  [switch]$SkipPack,
  [switch]$SkipImages,
)

# 关键：从脚本自身路径推出仓库根，并把 Config 路径解析为相对仓库根
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
$ConfigAbs = if ([System.IO.Path]::IsPathRooted($Config)) {
    $Config
} else {
    Join-Path $RepoRoot "tools\$Config"
}
$PyScript = Join-Path $ScriptDir "build_tool.py"

if (-not (Test-Path $Python)) {
    Write-Error "未找到 Python: $Python  —— 请在 tools/run.ps1 顶部把 `$Python 改成你的 Python 绝对路径"
    exit 1
}
$PythonVersion = & $Python --version 2>&1
Write-Host "Python: $PythonVersion"

if (-not (Test-Path $PyScript)) {
    Write-Error "未找到入口脚本: $PyScript"
    exit 1
}

# 显式映射为 Python argparse 期望的双横杠参数（PowerShell 的 -Mode 不等同于 --mode）
$pyArgs = @("--config", $ConfigAbs)
if ($Mode)        { $pyArgs += "--mode";       $pyArgs += $Mode }
if ($Yes)         { $pyArgs += "--yes" }
if ($NoClean)     { $pyArgs += "--no-clean" }
if ($SkipBuild)   { $pyArgs += "--skip-build" }
if ($SkipPack)    { $pyArgs += "--skip-pack" }
if ($SkipImages)  { $pyArgs += "--skip-images" }

& $Python $PyScript @pyArgs
exit $LASTEXITCODE
