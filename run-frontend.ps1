# ==============================================================================
# SITA Platform - Frontend Startup Script
# ==============================================================================
Write-Host "Starting SITA Platform Frontend (Vite / React)..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path "$ScriptDir\frontend"

Write-Host "Running Vite Dev Server on http://localhost:3000..." -ForegroundColor Green
npm run dev
