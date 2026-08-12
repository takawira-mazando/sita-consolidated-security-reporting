# SITA Consolidated Security Reporting

SITA Consolidated Security Reporting is a full-stack security intelligence platform that brings together application security, database security, SOC operations, compliance, and executive reporting into a unified experience. The solution combines a FastAPI backend, a React/Vite frontend, and supporting infrastructure for PostgreSQL, Redis, and containerized deployment.

## Overview

The platform is designed to help security and operations teams:

- Monitor alerts and findings from multiple security domains
- Correlate and normalise data for richer analysis
- Review compliance posture and executive-level summaries
- Explore role-based dashboards for different stakeholder personas
- Operate through a modern web interface backed by a service-oriented API

## Key capabilities

- Multi-role dashboards for executive, SOC, appsec, DBsec, and compliance users
- FastAPI-based REST API with health checks and monitoring hooks
- React frontend with role-aware navigation and dashboard components
- Data processing pipeline structure for ingestion, processing, dispatch, and analytics
- Docker-based local development and deployment support

## Architecture

The project is split into three main layers:

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Pydantic
- Infrastructure: Docker Compose, PostgreSQL, Redis, and supporting scripts

### Repository structure

```text
backend/
  app/
    api/
    bus/
    connectors/
    dispatch/
    entrypoints/
    ingestion/
    lake/
    models/
    monitoring/
    processing/
  migrations/
frontend/
  src/
  public/
  package.json
infrastructure/
  docker-compose.yml
  monitoring/
  nginx/
  scripts/
```

## Prerequisites

Before running the project locally, ensure you have the following installed:

- Python 3.11+ (the project is currently configured for Python 3.13 in the local environment)
- Node.js 18+ and npm
- Docker Desktop (optional, for container-based runs)

## Local development setup

### 1. Backend

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate    # Windows PowerShell
pip install -r requirements.txt
```

Start the backend API:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:

- http://127.0.0.1:8000
- Health endpoint: http://127.0.0.1:8000/health

### 2. Frontend

From the repository root:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

The frontend will be available at:

- http://127.0.0.1:3000

### 3. Demo login

The application includes demo accounts for local exploration. Use the credentials displayed on the login page, such as:

- exec@example.com / pass123
- soc@example.com / pass123
- appsec@example.com / pass123
- dbsec@example.com / pass123
- compliance@example.com / pass123
- transversal@example.com / pass123 (transversal superadmin — spans all-department reports / multiple departments)
- provincesoc@example.com / pass123 (provincial SOC lead — scoped to Gauteng's provincial departments)
- admin@example.com / admin123

Demo login supports a tenancy-scope override: pick a province, department or branch on the login page to sign in under that scope (province scope expands to every provincial department inside the province).

### 4. Provincial peer benchmarking & AG export

- `GET /api/v1/benchmark/province` — anonymised provincial peer benchmark. The caller's own province is unblinded with a department drill-down; peers appear as `Peer Province A/B/…` (aggregated fused risk only — raw vulnerability counts, findings and logs are never exposed).
- `POST /api/v1/exports/ag-compliance` — Auditor-General aggregation-only compliance attestation. Raw findings and PII are stripped; a SHA-256 integrity hash is bound to the actor + tenant scope in the `audit.action_audit` trail. Returns `integrity_hash` and `verify_url` (`GET /api/v1/exports/ag-compliance/verify/{hash}`).

## Docker-based setup

The project also includes Docker Compose configuration for local orchestration.

From the repository root:

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

This will bring up the backend, PostgreSQL, Redis, and frontend services in a containerized environment.

## Environment and services

### Backend services

The backend includes modules for:

- Authentication and API routing
- Alert and finding ingestion
- Compliance and risk processing
- Dispatch and notification adapters
- Monitoring and metrics

### Infrastructure services

The deployment stack includes:

- PostgreSQL for relational data storage
- Redis for message caching and event coordination
- Nginx configuration for frontend traffic handling
- Prometheus/Grafana monitoring assets

## API notes

The backend exposes API routes under the following base paths:

- /api/v1 for core platform APIs
- /admin for admin-focused routes
- /health for service health checks

## Development notes

- The frontend uses Vite for fast local development and build pipelines.
- The backend uses FastAPI and Pydantic v2 for modern API development.
- Database migrations are managed through Alembic.
- Monitoring and metrics are wired into the backend startup lifecycle.

## Contributing

Contributions are welcome. A typical workflow is:

1. Create a feature branch
2. Make your changes
3. Run local tests or validations as appropriate
4. Open a pull request with a clear summary

## License

This repository currently does not declare a specific license. If you plan to distribute or reuse this project publicly, add an appropriate open-source license before release.

## Next steps

If you want to extend the platform further, the most natural next areas are:

- Additional connectors for third-party security tooling
- More advanced enrichment and correlation rules
- Authentication integration with enterprise identity providers
- Expanded analytics and reporting dashboards
