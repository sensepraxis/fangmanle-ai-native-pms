@echo off
chcp 65001 >nul
REM Dev start (SQLite full demo). Default: commercial AI on (FML_COMMERCIAL=1).
REM OpenCore only: use start-opencore.bat in this folder (forces FML_COMMERCIAL=0).
REM Port: FML_PORT in this file (default 8081). Override via env. Do not put port in the filename.
REM
REM   deploy\dev\start.bat
REM   deploy\dev\start.bat demo-sg
REM   deploy\dev\start.bat abc-hotel.yaml
REM   deploy\dev\start.bat D:\cfg\my.yaml
REM Python: python / py on PATH, or set FML_PYTHON.

if not defined FML_PORT set "FML_PORT=8081"
REM Product default: commercial on. OpenCore entry sets FML_COMMERCIAL=0 before calling this script.
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
echo Hotel:      %FML_HOTEL%
if defined FML_HOTEL_YAML (
    echo Hotel config loaded from: %FML_HOTEL_YAML%
) else (
    echo Hotel config loaded from: %FML_HOTEL_FILE%
)
echo Locale:     %SEED_LOCALE%
echo Commercial: %FML_COMMERCIAL%  [1=on / 0=OpenCore only]
echo DB:         %DB_PATH%
echo ============================================
echo.

if /I "%SKIP_FE_BUILD%"=="1" (
    echo.
    echo [skip] Frontend build skipped [SKIP_FE_BUILD=1]
    goto AFTER_FE
)

echo.
echo [1/3] Sync locales -^> frontend\src\locales ...
if exist "%REPO_DIR%\locales\en.json" copy /Y "%REPO_DIR%\locales\en.json" "%FE_DIR%\src\locales\en.json" >nul
if exist "%REPO_DIR%\locales\zh-CN.json" copy /Y "%REPO_DIR%\locales\zh-CN.json" "%FE_DIR%\src\locales\zh-CN.json" >nul

echo.
echo [2/3] Building frontend [clean vite -^> frontend\dist] ...
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
echo      Open http://127.0.0.1:%FML_PORT%/  [Ctrl+C to stop]
echo.

cd /d "%SRC_DIR%"
"%PYTHON%" -m uvicorn api:app --host 127.0.0.1 --port %FML_PORT% --log-level info

echo.
echo uvicorn exited. Press any key to close.
pause >nul
