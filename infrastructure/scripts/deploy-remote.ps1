# SITA Platform remote deployment (Windows target)
# Run in an elevated PowerShell on the deployment server.
$ErrorActionPreference = "Stop"
$DeployDir = "C:\sita-deploy"

function New-Secret([int]$len = 48) {
    $bytes = New-Object byte[] $len
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    -join ($bytes | ForEach-Object { '{0:x2}' -f $_ })
}

Write-Host "==> SITA Platform deployer" -ForegroundColor Cyan

# 1. Clone/pull the repo so compose files + init SQL are present
if (-not (Test-Path "$DeployDir\sita-platform")) {
    Write-Host "==> Cloning sita-platform repo..." -ForegroundColor Cyan
    git clone --depth 1 https://github.com/takawira-mazando/sita-consolidated-security-reporting.git "$DeployDir\sita-platform" 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
} else {
    Write-Host "==> Pulling latest sita-platform..." -ForegroundColor Cyan
    Push-Location "$DeployDir\sita-platform"
    git pull --ff-only 2>&1 | Out-Host
    Pop-Location
}

# 2. Ensure Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "==> Docker not found. Installing Docker Desktop (this needs WSL2)..." -ForegroundColor Yellow
    winget install --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements | Out-Host
    Write-Host "==> Docker Desktop installed. Starting it..." -ForegroundColor Cyan
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "Waiting for Docker engine..."
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep 5
        if (docker info *> $null) { $ready = $true; break }
    }
    if (-not $ready) { throw "Docker engine did not start in 5 min. Open Docker Desktop, ensure WSL2 backend, then rerun." }
} else {
    Write-Host "==> Docker found: $((docker --version).Trim())" -ForegroundColor Green
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> Docker engine not running. Starting Docker Desktop..." -ForegroundColor Yellow
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep 5
            if (docker info *> $null) { break }
        }
    }
}

# 3. Write .env with strong generated secrets
$envFile = "$DeployDir\sita-platform\infrastructure\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "==> Generating .env with strong secrets..." -ForegroundColor Cyan
    @"
DB_PASSWORD=$(New-Secret 32)
REDIS_PASSWORD=$(New-Secret 32)
JWT_SECRET=$(New-Secret 64)
BOOTSTRAP_ADMIN_EMAIL=admin@sita.local
BOOTSTRAP_ADMIN_PASSWORD=$(New-Secret 20)
SEED_DEMO_USERS_ENABLED=false
ENVIRONMENT=production
"@ | Set-Content -Path $envFile -Encoding ASCII
} else {
    Write-Host "==> .env already exists, keeping it." -ForegroundColor Yellow
}

# 4. Pull images
Push-Location "$DeployDir\sita-platform\infrastructure"
Write-Host "==> Pulling images..." -ForegroundColor Cyan
docker compose -f docker-compose.remote.yml --env-file .env pull
if ($LASTEXITCODE -ne 0) { throw "image pull failed" }

# 5. Start stack
Write-Host "==> Starting stack..." -ForegroundColor Cyan
docker compose -f docker-compose.remote.yml --env-file .env up -d
if ($LASTEXITCODE -ne 0) { throw "compose up failed" }

# 6. Wait for health
Write-Host "==> Waiting for backend health..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep 5
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:80/api/v1/public/summary" -TimeoutSec 4 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}
Pop-Location

if ($ok) {
    Write-Host "`n==> DEPLOY SUCCESS" -ForegroundColor Green
    Write-Host "    UI:  http://localhost:80"
    Write-Host "    API: http://localhost:80/api/v1"
    Write-Host "    Admin bootstrap: $(Select-String -Path $envFile -Pattern '^BOOTSTRAP_ADMIN_EMAIL=').Line.Split('=')[1]"
} else {
    Write-Host "`n==> Deploy started but health check failed. Inspect with:" -ForegroundColor Yellow
    Write-Host "    docker compose -f C:\sita-deploy\sita-platform\infrastructure\docker-compose.remote.yml logs --tail 100 backend"
}
