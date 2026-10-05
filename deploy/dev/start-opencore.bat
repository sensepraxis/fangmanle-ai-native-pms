@echo off
chcp 65001 >nul
REM OpenCore-only dev start: forces commercial off (no need to remember the env var).
REM Same usage as start.bat:
REM   deploy\dev\start-opencore.bat demo-sg
REM   deploy\dev\start-opencore.bat demo-cn

set "FML_COMMERCIAL=0"
call "%~dp0start.bat" %*
