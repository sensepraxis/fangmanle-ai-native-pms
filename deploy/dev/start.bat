@echo off
chcp 65001 >nul
REM 常规开发启动（SQLite 完整 demo）· 默认启用商业 AI（FML_COMMERCIAL=1）。
REM 只要 OpenCore：请用同目录 start-opencore.bat（脚本内写死 FML_COMMERCIAL=0）。
REM 端口写在本文件 FML_PORT，不要写进文件名。可用环境变量覆盖。
REM
REM   deploy\dev\start.bat                 → config\hotels\demo-cn.yaml
REM   deploy\dev\start.bat demo-sg
REM   deploy\dev\start.bat abc-hotel.yaml
REM   deploy\dev\start.bat D:\cfg\my.yaml
REM Python：PATH 中的 python / py；可设 FML_PYTHON 覆盖。

if not defined FML_PORT set "FML_PORT=8081"
REM 产品默认：开商业包。OpenCore 入口会先设 FML_COMMERCIAL=0 再 call 本脚本。
if not defined FML_COMMERCIAL set "FML_COMMERCIAL=1"

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.."
set "REPO_DIR=%CD%"
popd
set "SRC_DIR=%REPO_DIR%\src"
set "FE_DIR=%REPO_DIR%\frontend"
if defined FML_PYTHON (
    set "PYTHON=%FML_PYTHON%"
) else (
    set "PYTHON=python"
    where python >nul 2>&1
    if errorlevel 1 set "PYTHON=py"
)
set FML_REPO_DIR=%REPO_DIR%
set PYTHONPATH=%SRC_DIR%

if not "%~1"=="" set "FML_HOTEL_FILE=%~1"
if "%FML_HOTEL_FILE%"=="" set "FML_HOTEL_FILE=demo-cn"
set "FML_DEPLOY_FILE=%FML_HOTEL_FILE%"

"%PYTHON%" "%REPO_DIR%\deploy\dev\print_deploy_env.py" > "%TEMP%\fml_deploy_env.cmd"
if errorlevel 1 (
    echo Failed to read hotel YAML: %FML_HOTEL_FILE%
    echo pip install pyyaml
    pause
    exit /b 1
)
call "%TEMP%\fml_deploy_env.cmd"

if "%FML_HOTEL%"=="" if not "%FML_PACKS%"=="" set FML_HOTEL=%FML_PACKS%
if "%FML_HOTEL%"=="" set FML_HOTEL=demo-cn
if "%FML_PACKS%"=="" set FML_PACKS=%FML_HOTEL%
if "%SEED_LOCALE%"=="" set SEED_LOCALE=en
if "%FML_DEFAULT_LOCALE%"=="" set FML_DEFAULT_LOCALE=%SEED_LOCALE%

if "%DB_PATH%"=="" set DB_PATH=C:\tmp\fml_demo_%FML_PORT%_%FML_HOTEL%.db
set DATABASE_URL=sqlite:///%DB_PATH%

title Fangmanle PMS %FML_PORT% [hotel=%FML_HOTEL% locale=%SEED_LOCALE%]

echo ============================================
echo Fangmanle PMS
echo Port:       %FML_PORT%
echo Hotel YAML: %FML_HOTEL_FILE%
echo Hotel:      %FML_HOTEL%
echo Locale:     %SEED_LOCALE%
echo Commercial: %FML_COMMERCIAL%  ^(1=on · 0=OpenCore only^)
echo DB:         %DB_PATH%
echo ============================================
echo.

if /I "%SKIP_FE_BUILD%"=="1" (
    echo.
    echo [skip] Frontend build skipped ^(SKIP_FE_BUILD=1^)
    goto AFTER_FE
)

echo.
echo [1/3] Sync locales -^> frontend\src\locales ...
if exist "%REPO_DIR%\locales\en.json" copy /Y "%REPO_DIR%\locales\en.json" "%FE_DIR%\src\locales\en.json" >nul
if exist "%REPO_DIR%\locales\zh-CN.json" copy /Y "%REPO_DIR%\locales\zh-CN.json" "%FE_DIR%\src\locales\zh-CN.json" >nul

echo.
echo [2/3] Building frontend ^(clean vite -^> frontend\dist^) ...
cd /d "%FE_DIR%"
if exist "%FE_DIR%\dist" (
    echo      Removing old dist...
    rmdir /s /q "%FE_DIR%\dist"
)
call npm run build
if errorlevel 1 (
    echo Frontend build FAILED
    pause
    exit /b 1
)

:AFTER_FE
echo.
echo [3/3] Bootstrap demo + uvicorn 127.0.0.1:%FML_PORT% ...
"%PYTHON%" "%REPO_DIR%\deploy\dev\bootstrap_demo.py"
if errorlevel 1 (
    echo Bootstrap FAILED
    pause
    exit /b 1
)

echo.
echo      Open http://127.0.0.1:%FML_PORT%/  ^(Ctrl+C to stop^)
echo.

cd /d "%SRC_DIR%"
"%PYTHON%" -m uvicorn api:app --host 127.0.0.1 --port %FML_PORT% --log-level info

echo.
echo uvicorn exited. Press any key to close.
pause >nul
