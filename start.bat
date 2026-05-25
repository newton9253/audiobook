@echo off
title AI Sound Studio
echo ======================================
echo   AI Sound Studio v1.0.0
echo   http://localhost:8080
echo ======================================
echo.
echo 安装依赖: pip install -r requirements.txt
echo.

start http://localhost:8080

cd /d "%~dp0"

python -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level info

pause
