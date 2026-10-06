@echo off
cd /d "%~dp0"
start "今日脉络服务" /min node app.js
timeout /t 1 /nobreak >nul
start "" http://127.0.0.1:17891
