# ==============================================================================
# SITA Platform - Run Both Backend & Frontend
# ==============================================================================
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting SITA Platform: Backend (:8000) & Frontend (:3000)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend in new process / background
Write-Host "Launching Backend API on http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendJob = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ScriptDir\run-backend.ps1" -PassThru

# Wait 2 seconds for backend to initialize
Start-Sleep -Seconds 2

# Start frontend in current or separate process
Write-Host "Launching Frontend UI on http://localhost:3000..." -ForegroundColor Yellow
$FrontendJob = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$ScriptDir\run-frontend.ps1" -PassThru

Write-Host "Both processes launched!" -ForegroundColor Green
Write-Host "  - Backend PID:  $($BackendJob.Id)" -ForegroundColor Green
Write-Host "  - Frontend PID: $($FrontendJob.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  - Web App:   http://localhost:3000" -ForegroundColor White
Write-Host "  - Swagger:   http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  - OpenAPI:   http://127.0.0.1:8000/openapi.json" -ForegroundColor White
