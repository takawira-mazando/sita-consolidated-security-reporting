#!/bin/bash
set -euo pipefail

ENV="${1:-staging}"
TAG="${2:-latest}"

echo "Deploying SITA Platform to ${ENV} (tag: ${TAG})"

export DOCKER_BUILDKIT=1
export COMPOSE_PROJECT_NAME="sita-${ENV}"

docker compose -f infrastructure/docker-compose.prod.yml build
docker compose -f infrastructure/docker-compose.prod.yml up -d --wait

echo "Running migrations..."
docker compose -f infrastructure/docker-compose.prod.yml exec -T backend alembic upgrade head

echo "Health check..."
sleep 5
curl -sf http://localhost:8000/health && echo " OK" || echo " FAILED"

echo "Deploy complete: ${ENV}"
