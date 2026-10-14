#!/bin/bash
set -euo pipefail

ENV="${1:-staging}"
TAG="${2:-latest}"

echo "Deploying SITA Platform to ${ENV} (tag: ${TAG})"

export DOCKER_BUILDKIT=1
export COMPOSE_PROJECT_NAME="sita-${ENV}"

# Container resource limits (CPU/Memory/ulimits: CWE-400), non-root execution (CWE-266),
# read-only root filesystem (CWE-16), and no-new-privileges are enforced declaratively
# within infrastructure/docker-compose.prod.yml.
DOCKER_EXE="$(command -v docker 2>/dev/null || echo 'docker')"
COMPOSE_FILE="infrastructure/docker-compose.prod.yml"

run_compose() {
    "${DOCKER_EXE}" compose -f "${COMPOSE_FILE}" "$@"
}

run_compose build
run_compose up -d --wait

echo "Running migrations..."
# Run migrations under the non-root appuser with restricted privileges (CWE-266)
run_compose exec -T --user appuser backend alembic upgrade head

echo "Health check..."
sleep 5
curl -sf http://localhost:8000/health && echo " OK" || echo " FAILED"

echo "Deploy complete: ${ENV}"
