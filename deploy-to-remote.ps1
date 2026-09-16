# SITA Platform - Remote Deployment Command (PowerShell)
# Run this from PowerShell (Admin) on Windows to deploy to 192.168.101.20
# Prerequisites: sshpass (install via: winget install sshpass OR choco install sshpass OR use Git Bash/WSL with the .sh script)

$ErrorActionPreference = "Stop"

$RemoteHost = "192.168.101.20"
$RemoteUser = "uni"
$RemotePass = "H051@pivot"
$DeployDir = "/opt/sita"
$Repo = "https://Takawira-Mazando:Takawira%40Mazando%21654%23@github.com/takawira-mazando/sita-consolidated-security-reporting.git"
$StackDir = "$DeployDir/sita-platform/infrastructure"

function Write-Status($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "==> $msg" -ForegroundColor Green }
function Write-Warning($msg) { Write-Host "==> $msg" -ForegroundColor Yellow }
function Write-Error($msg) { Write-Host "==> $msg" -ForegroundColor Red }

Write-Host "`n=== SITA Platform Remote Deployment ===" -ForegroundColor Green
Write-Host "Target: $RemoteUser@$RemoteHost"
Write-Host "Repo: $Repo"
Write-Host ""

# Check for sshpass
if (-not (Get-Command sshpass -ErrorAction SilentlyContinue)) {
    Write-Error "sshpass not found. This script requires sshpass for non-interactive SSH password auth."
    Write-Host ""
    Write-Host "Install options:" -ForegroundColor Yellow
    Write-Host "  1. winget install sshpass" -ForegroundColor Gray
    Write-Host "  2. choco install sshpass" -ForegroundColor Gray
    Write-Host "  3. Use Git Bash / WSL and run: ./deploy-to-remote.sh (RECOMMENDED)" -ForegroundColor Green
    Write-Host ""
    exit 1
}

# Step 1: Deploy to remote server
Write-Status "Step 1: Deploying to remote server..."

# Build remote bash script using single-quoted here-string (no PowerShell variable expansion)
# Then replace placeholders
$remoteScript = @'
set -euo pipefail

DEPLOY_DIR="__DEPLOY_DIR__"
REPO="__REPO__"
STACK_DIR="__STACK_DIR__"

echo "==> Installing Docker if needed..."
if ! command -v docker >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg sshpass
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker "$USER"
    newgrp docker << 'EOF'
EOF
else
    echo "==> Docker found: $(docker --version)"
fi
sudo systemctl enable --now docker 2>/dev/null || true

echo "==> Fetching deployment assets..."
sudo mkdir -p "$DEPLOY_DIR"
if [ ! -d "$STACK_DIR" ]; then
    echo "==> Cloning repo..."
    sudo git clone --depth 1 "$REPO" "$DEPLOY_DIR/sita-platform"
else
    echo "==> Pulling latest..."
    sudo git -C "$DEPLOY_DIR/sita-platform" pull --ff-only
fi

echo "==> Managing .env secrets..."
ENV_FILE="$STACK_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "==> Generating .env with strong secrets..."
    {
        echo "DB_PASSWORD=$(openssl rand -hex 32)"
        echo "REDIS_PASSWORD=$(openssl rand -hex 32)"
        echo "JWT_SECRET=$(openssl rand -hex 64)"
        echo "BOOTSTRAP_ADMIN_EMAIL=admin@sita.local"
        echo "BOOTSTRAP_ADMIN_PASSWORD=$(openssl rand -hex 20)"
        echo "SEED_DEMO_USERS_ENABLED=false"
        echo "ENVIRONMENT=production"
    } | sudo tee "$ENV_FILE" > /dev/null
    sudo chmod 600 "$ENV_FILE"
    echo "==> Bootstrap admin password:"
    sudo grep BOOTSTRAP_ADMIN_PASSWORD "$ENV_FILE"
else
    echo "==> .env exists - keeping it."
fi

echo "==> Pulling latest images..."
sudo docker compose -f "$STACK_DIR/docker-compose.remote.yml" --env-file "$ENV_FILE" pull

echo "==> Starting stack..."
sudo docker compose -f "$STACK_DIR/docker-compose.remote.yml" --env-file "$ENV_FILE" up -d

echo "==> Waiting for backend health on port 8000 (up to 2 min)..."
OK=0
for i in $(seq 1 24); do
    sleep 5
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then OK=1; break; fi
    printf "."
done
echo ""

if [ "$OK" = "1" ]; then
    echo "==> DEPLOY SUCCESS"
    echo "    Frontend:  http://__REMOTE_HOST__:8088"
    echo "    Backend:   http://__REMOTE_HOST__:8000"
    echo "    API:       http://__REMOTE_HOST__:8000/api/v1"
    echo "    Health:    http://__REMOTE_HOST__:8000/health"
    echo "    Swagger:   http://__REMOTE_HOST__:8000/docs"
    exit 0
else
    echo "==> Deploy started, health check failed. Check logs:"
    echo "    sudo docker compose -f $STACK_DIR/docker-compose.remote.yml --env-file $ENV_FILE logs --tail 100 backend"
    exit 1
fi
'@

# Replace placeholders
$remoteScript = $remoteScript -replace "__DEPLOY_DIR__", $DeployDir
$remoteScript = $remoteScript -replace "__REPO__", $Repo
$remoteScript = $remoteScript -replace "__STACK_DIR__", $StackDir
$remoteScript = $remoteScript -replace "__REMOTE_HOST__", $RemoteHost

# Write remote script to temp file and execute via ssh (using Get-Content to pipe)
$tempScript = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tempScript, $remoteScript)

$sshCmd = "sshpass -p '$RemotePass' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $RemoteUser@$RemoteHost 'bash -s'"
Get-Content $tempScript -Raw | Invoke-Expression "$sshCmd"

# Cleanup
Remove-Item -Force $tempScript -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Error "Remote deployment failed!"
    exit 1
}

Write-Success "Remote deployment successful!"

# Step 2: Establish SSH tunnels
Write-Status "Step 2: Establishing SSH tunnels..."
Write-Host "Tunnels:"
Write-Host "  localhost:8801 -> $RemoteHost:8000 (Backend API, Swagger, Health)"
Write-Host "  localhost:8802 -> $RemoteHost:8088 (Frontend App)"
Write-Host ""

# Kill existing tunnels
foreach ($port in 8801, 8802) {
    $pids = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    foreach ($pid in $pids) {
        try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
    }
}

# Start tunnels in background
$tunnelCmd = "sshpass -p '$RemotePass' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -f -N -L 8801:localhost:8000 -L 8802:localhost:8088 $RemoteUser@$RemoteHost"
Invoke-Expression $tunnelCmd

Start-Sleep 2

# Verify tunnels
foreach ($port in 8801, 8802) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Success "Tunnel on port $port established"
    } else {
        Write-Warning "Tunnel on port $port may not be active yet"
    }
}

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Remote server (LAN/VPN with port access):"
Write-Host "  Frontend:  http://$RemoteHost:8088"
Write-Host "  Backend API:       http://$RemoteHost:8000/api/v1"
Write-Host "  Health:            http://$RemoteHost:8000/health"
Write-Host "  Swagger UI:        http://$RemoteHost:8000/docs"
Write-Host "  OpenAPI:           http://$RemoteHost:8000/openapi.json"
Write-Host ""
Write-Host "Local tunnels (via SSH over VPN):"
Write-Host "  Frontend:  http://localhost:8802"
Write-Host "  Backend API:       http://localhost:8801/api/v1"
Write-Host "  Health:            http://localhost:8801/health"
Write-Host "  Swagger UI:        http://localhost:8801/docs"
Write-Host "  OpenAPI:           http://localhost:8801/openapi.json"
Write-Host ""
Write-Host "To stop tunnels:"
Write-Host "  Get-NetTCPConnection -LocalPort 8801,8802 -State Listen | ForEach-Object { Stop-Process -Id `$_.OwningProcess -Force }"