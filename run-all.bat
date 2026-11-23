@echo off
title SITA Platform Launcher
echo ==============================================================
echo   Launching SITA Platform Backend and Frontend
echo ==============================================================

start "SITA Backend API (:8000)" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0run-backend.ps1"
timeout /t 2 /nobreak >nul
start "SITA Frontend UI (:3000)" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0run-frontend.ps1"

echo.
echo Both services launched in separate windows!
echo   Frontend: http://localhost:3000
echo   Backend:  http://127.0.0.1:8000/docs
echo.
pause
