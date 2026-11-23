# ==============================================================================
# SITA Platform - Backend Startup Script
# ==============================================================================
Write-Host "Starting SITA Platform Backend (FastAPI / Uvicorn)..." -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1

if ($Listener) {
    $ExistingProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($Listener.OwningProcess)"
    $IsBackendProcess = $ExistingProcess.Name -match '^python(w)?\.exe$' -and $ExistingProcess.CommandLine -match 'uvicorn|app\.main:app'

    if ($IsBackendProcess) {
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 -ErrorAction Stop
        } catch {
            Write-Error "Uvicorn PID $($Listener.OwningProcess) owns port 8000, but its health check failed: $($_.Exception.Message)"
            exit 1
        }

        if ($Health.status -eq "ok") {
            Write-Host "Backend is already healthy on http://127.0.0.1:8000 (PID $($Listener.OwningProcess)); reusing it." -ForegroundColor Green
            exit 0
        }
    }

    $ProcessName = if ($ExistingProcess) { $ExistingProcess.Name } else { "unknown process" }
    Write-Error "Port 8000 is already occupied by PID $($Listener.OwningProcess) ($ProcessName). Refusing to start a duplicate backend."
    exit 1
}

Set-Location -Path "$ScriptDir\backend"

$VenvPython = "$ScriptDir\backend\.venv\Scripts\python.exe"

if (-Not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment python not found at $VenvPython. Using system python." -ForegroundColor Yellow
    $VenvPython = "python"
}

$env:PYTHONPATH = "$ScriptDir\backend"

Write-Host "Running Uvicorn on http://127.0.0.1:8000 (API docs at http://127.0.0.1:8000/docs)..." -ForegroundColor Green
& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
