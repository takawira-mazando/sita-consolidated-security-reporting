#!/bin/bash
# SITA Platform - Remote Deployment Command
# Run this from your local machine to deploy to 192.168.101.20

set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-192.168.101.20}"
REMOTE_USER="${REMOTE_USER:-uni}"
REMOTE_PASS="${REMOTE_PASS:-}"
DEPLOY_DIR="/opt/sita"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_URL="${REPO_URL:-https://github.com/takawira-mazando/sita-consolidated-security-reporting.git}"
if [ -n "$GITHUB_TOKEN" ]; then
    REPO="https://${GITHUB_TOKEN}@github.com/takawira-mazando/sita-consolidated-security-reporting.git"
else
    REPO="$REPO_URL"
fi
STACK_DIR="$DEPLOY_DIR/sita-platform/infrastructure"

if [ -z "$REMOTE_PASS" ]; then
    echo -n "Enter remote SSH password for $REMOTE_USER@$REMOTE_HOST: "
    read -rs REMOTE_PASS
    echo ""
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== SITA Platform Remote Deployment ===${NC}"
echo "Target: $REMOTE_USER@$REMOTE_HOST"
echo "Repo: $REPO_URL"
echo ""

# Step 1: SSH and deploy
echo -e "${YELLOW}Step 1: Deploying to remote server...${NC}"

sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$REMOTE_USER@$REMOTE_HOST" sudo -S bash -s << REMOTE_EOF
$REMOTE_PASS
set -euo pipefail

DEPLOY_DIR="/opt/sita"
REPO="$REPO"
STACK_DIR="\$DEPLOY_DIR/sita-platform/infrastructure"

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
    echo "    Frontend:  http://$REMOTE_HOST:8088"
    echo "    Backend:   http://$REMOTE_HOST:8000"
    echo "    API:       http://$REMOTE_HOST:8000/api/v1"
    echo "    Health:    http://$REMOTE_HOST:8000/health"
    echo "    Swagger:   http://$REMOTE_HOST:8000/docs"
else
    echo "==> Deploy started, health check failed. Check logs:"
    echo "    sudo docker compose -f $STACK_DIR/docker-compose.remote.yml --env-file $ENV_FILE logs --tail 100 backend"
    exit 1
fi
REMOTE_EOF

# Step 2: Establish SSH tunnels
echo -e "${YELLOW}Step 2: Establishing SSH tunnels...${NC}"
echo "Tunnels:"
echo "  localhost:8801 -> $REMOTE_HOST:8000 (Backend API, Swagger, Health)"
echo "  localhost:8802 -> $REMOTE_HOST:8088 (Frontend App)"
echo ""

# Kill existing tunnels on these ports
for port in 8801 8802; do
    PID=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        echo "Killed existing process on port $port"
    fi
done

# Start new tunnels in background
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -f -N -L 8801:localhost:8000 -L 8802:localhost:8088 "$REMOTE_USER@$REMOTE_HOST"

sleep 2

# Verify tunnels
for port in 8801 8802; do
    if lsof -ti:"$port" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Tunnel on port $port established${NC}"
    else
        echo -e "${RED}✗ Tunnel on port $port failed${NC}"
    fi
done

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo "Remote server (LAN/VPN with port access):"
echo "  Frontend:  http://$REMOTE_HOST:8088"
echo "  Backend API:       http://$REMOTE_HOST:8000/api/v1"
echo "  Health:            http://$REMOTE_HOST:8000/health"
echo "  Swagger UI:        http://$REMOTE_HOST:8000/docs"
echo "  OpenAPI:           http://$REMOTE_HOST:8000/openapi.json"
echo ""
echo "Local tunnels (via SSH over VPN):"
echo "  Frontend:  http://localhost:8802"
echo "  Backend API:       http://localhost:8801/api/v1"
echo "  Health:            http://localhost:8801/health"
echo "  Swagger UI:        http://localhost:8801/docs"
echo "  OpenAPI:           http://localhost:8801/openapi.json"
echo ""
echo "To verify backend health:"
echo "  curl http://localhost:8801/health"
echo ""
echo "To stop tunnels:"
echo "  pkill -f 'ssh.*8801:localhost:8000'"
echo "  pkill -f 'ssh.*8802:localhost:8088'"