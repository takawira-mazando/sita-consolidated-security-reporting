#!/bin/bash
# SITA Platform remote deployment - Linux target (Ubuntu 24.04/26.04 LTS)
# Run as a normal user with sudo access. Pulls prebuilt GHCR images - no build.
set -euo pipefail

DEPLOY_DIR="${1:-/opt/sita}"
REPO="https://github.com/takawira-mazando/sita-consolidated-security-reporting.git"
STACK_DIR="$DEPLOY_DIR/sita-platform/infrastructure"

echo "==> SITA Platform deployer (Linux)"

# 1. Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing Docker Engine..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker "$USER"
    echo "==> Docker installed. Re-login required for docker group - run: newgrp docker"
    newgrp docker || true
else
    echo "==> Docker found: $(docker --version)"
fi
sudo systemctl enable --now docker 2>/dev/null || true

# 2. Disable the legacy 'sita' system account used by this project on shared hosts.
#    (Unopinionated no-op guard - project repos that misuse 'sita' user are out of scope.)

# 3. Fetch deployment assets
sudo mkdir -p "$DEPLOY_DIR"
if [ ! -d "$STACK_DIR" ]; then
    echo "==> Cloning repo..."
    sudo git clone --depth 1 "$REPO" "$DEPLOY_DIR/sita-platform"
else
    echo "==> Pulling latest..."
    sudo git -C "$DEPLOY_DIR/sita-platform" pull --ff-only
fi

# 4. Secrets (.env) - generate once, keep if present
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
    echo "==> .env written. Bootstrap admin password below (save it):"
    sudo grep BOOTSTRAP_ADMIN_PASSWORD "$ENV_FILE"
else
    echo "==> .env exists - keeping it."
fi

# 5. Firewall (optional, best-effort)
if command -v ufw >/dev/null 2>&1; then
    echo "==> Configuring UFW (SSH + 80)..."
    sudo ufw allow OpenSSH >/dev/null 2>&1 || true
    sudo ufw allow 80/tcp >/dev/null 2>&1 || true
    sudo ufw --force enable >/dev/null 2>&1 || true
fi

# 6. Deploy
echo "==> Pulling images..."
sudo docker compose -f "$STACK_DIR/docker-compose.remote.yml" --env-file "$ENV_FILE" pull
echo "==> Starting stack..."
sudo docker compose -f "$STACK_DIR/docker-compose.remote.yml" --env-file "$ENV_FILE" up -d

# 7. Health check
echo "==> Waiting for backend health... (up to 2 min)"
OK=0
for i in $(seq 1 24); do
    sleep 5
    if curl -sf http://localhost:80/api/v1/public/summary >/dev/null 2>&1; then OK=1; break; fi
    printf "."
done
echo ""
if [ "$OK" = "1" ]; then
    echo ""
    echo "==> DEPLOY SUCCESS"
    echo "    UI:   http://$(hostname -I | awk '{print $1}')  (or http://192.168.101.20)"
    echo "    API:  http://192.168.101.20/api/v1"
    echo "    Health: curl -s http://localhost:80/api/v1/public/summary"
else
    echo ""
    echo "==> Deploy started, health check failed. Inspect:"
    echo "    sudo docker compose -f $STACK_DIR/docker-compose.remote.yml --env-file $ENV_FILE logs --tail 100 backend"
fi