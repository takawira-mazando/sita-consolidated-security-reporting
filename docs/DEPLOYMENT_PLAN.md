# Deployment Strategy — Docker Containers, Shipped to the Customer's Environment

**Project:** SITA Consolidated Security Reporting (`sita-platform`)
**Repo:** https://github.com/takawira-mazando/sita-consolidated-security-reporting
**Deployment unit:** Docker containers (prebuilt images on GHCR) — portable to any Docker-capable host
**From:** Local Windows dev machine (Docker Desktop, no persistent hosting)
**To (now):** Linux Docker host at Hosi Technologies, Fourways, Johannesburg, South Africa
**To (customer):** SITA's preferred environment (their own servers / cloud / chosen platform)
**To (Hosi-managed cloud, optional):** Amazon Web Services (AWS) — only if Hosi Technologies operates the system as a cloud-based, managed service
**Date:** 19 August 2026
**Related docs:** [SITA_Platform_System_Documentation.md](./SITA_Platform_System_Documentation.md), [Role-Provisioning-Roadmap.html](./Role-Provisioning-Roadmap.html)

---

## 1. Goal

Deliver the SITA platform as **portable Docker containers** that run identically wherever they are placed, and stand them up in stages:

| Stage | Target | Rationale |
|-------|--------|-----------|
| **Stage A (now)** | Linux server at Hosi Fourways (LAN `192.168.101.x`) | Cost-effective today; no licensing; already has Docker; under our physical control |
| **Stage B (customer)** | **SITA's preferred environment** | The platform is **shipped to SITA** — deployed as Docker containers on the environment SITA chooses (on-prem, their cloud, or third-party hosting) |
| **Stage C (optional)** | Amazon AWS | **Only if the system is cloud-based and managed from there by us, Hosi Technologies** — managed services, elastic scale, HA/DR |

**Key principle:** AWS is **not** the default destination. The deliverable is a containerized system. AWS is one hosting option among several, and only makes sense when Hosi Technologies operates it as a managed cloud service. If SITA specifies a different environment, the **same Docker images and compose topology** are shipped there unchanged.

Success criteria (Stage A):

- Platform reachable at a stable HTTP URL on the Hosi LAN / via VPN
- Backend, frontend, Postgres, Redis running from **prebuilt GHCR images** (no source build on server)
- HR schema + demo/seed data initialized on first boot
- Strong generated secrets; demo seeding disabled; admin bootstrap active
- A **portable shipping bundle** (compose files + images + runbook) that can be handed to SITA for any environment

---

## 2. Current State (Local Windows / Dev)

```
Dev machine (Windows, hosi)
   ├── Docker Desktop (dev compose: postgres, redis, backend, frontend)
   ├── Uvicorn on 127.0.0.1:8000 + Vite dev on 127.0.0.1:3000 (dual-stack ::)
   └── No persistent host / public URL / backups / monitoring
```

What exists in the repo today:

| Asset | Purpose |
|-------|---------|
| `infrastructure/docker-compose.remote.yml` | Pulls `ghcr.io/…/sita-backend:latest` + `sita-frontend:latest`, Postgres 16, Redis 7, nginx :80 |
| `infrastructure/nginx/sita-http.conf` | HTTP entrypoint for first deploy (no TLS dependency) |
| `infrastructure/scripts/init-db.sql`, `seed-hr-system.sql`, `seed-hr-system-branches.sql` | Schema + HR seed mounted into Postgres init |
| `infrastructure/scripts/deploy-remote.ps1` | Windows-side bootstrap (clones, generates `.env`, pulls, up) |
| `.github/workflows/ci.yml`, `publish-ghcr.yml` | CI + publish images to GitHub Container Registry on `main` |
| `docs/` | System documentation, role-provisioning roadmap |

GHCR images are **public** — the target server can pull them without credentials:

```bash
docker pull ghcr.io/takawira-mazando/sita-backend:latest
docker pull ghcr.io/takawira-mazando/sita-frontend:latest
```

---

## 3. Target State (Stage A — Hosi Fourways Linux)

```
LAN users / VPN
   │ HTTP :80
   ▼
┌──────────────────────────────────────┐
│  HOSI FOURWAYS LINUX SERVER          │
│  (192.168.101.20, Ubuntu/Docker)     │
│  • Docker Compose: sita stack        │
│  • backend    :8000 (internal)       │
│  • frontend   :80   (internal)       │
│  • postgres 16 + redis 7 (internal)  │
│  • nginx      :80   → frontend/API   │
│  • GHCR images pulled, no build      │
└──────────────────────────────────────┘
```

### Recommended sizing (start)

| Server | CPU | RAM | Disk | Notes |
|--------|-----|-----|------|-------|
| Hosi Fourways Linux | 4+ vCPU | 8+ GB | 100 GB SSD | Compose stack + images + DB + backups |

OS: **Ubuntu 22.04/24.04 LTS** preferred (matches Docker/GHCR images, no licensing). Access via VPN to the `192.168.101.0/24` range.

---

## 4. Why Linux (Hosi Fourways) over Windows (AnyDesk box)

The current alternative — a Windows box reachable via AnyDesk (`Administrator` / eval licensing) — was evaluated and set aside. The deciding factor: **Windows Server licensing on that box expires in < 30 days**, which forces a re-license or re-build mid-flight. Details:

| Factor | Linux (Hosi Fourways) | Windows Server (AnyDesk box) |
|--------|------------------------|------------------------------|
| **Licensing** | Free (Ubuntu LTS); no expiry | Per-core/OS licensing; **eval expires < 30 days** → urgent renewal risk |
| **Docker** | Native engine, `docker compose` v2; 1:1 with our compose files | Docker Desktop or Windows containers; **Windows containers need matching host build** (kernel-version pinning) |
| **Images** | Pull GHCR Linux images directly | Linux images won't run without a Linux VM/WSL2 layer — extra moving parts |
| **Ops tooling** | `deploy.sh`, `backup.sh`, UFW, cron — battle-tested on Linux | PowerShell equivalents must be written; no equivalent to shell scripts |
| **Footprint** | ~300 MB images, low idle RAM | Heavier base image + WSL2/VM overhead |
| **Remote access** | SSH key-based (already reachable via `154.66.211.3` / Tailscale) | AnyDesk GUI only — not scriptable from CI/CD |
| **Cost** | None (existing Hosi asset) | License + renewal risk + potential CALs |
| **Risk** | Low | High (expiry deadline forces urgent remediation) |

**Verdict:** Linux at Hosi Fourways is the accessible, cost-effective, low-risk choice **now**. It also keeps the exact same compose topology that can later be shipped to SITA's environment or lifted into AWS — the Windows path would force a parallel, incompatible deployment model for zero benefit.

---

## 5. Deployment Principles

1. **Image-driven, not build-driven** — the server pulls GHCR images; it never compiles. The same images are what gets shipped.
2. **Portable by construction** — everything needed to run (compose files, nginx config, init SQL, `.env` template, runbook) is in the repo. Deployment = `docker compose up` on any Docker-capable host.
3. **Fresh secrets everywhere** — strong generated `JWT_SECRET`, `DB_PASSWORD`, `REDIS_PASSWORD`, bootstrap admin password; `SEED_DEMO_USERS_ENABLED=false` in production.
4. **Server-side state is disposable** — Postgres/Redis volumes live on the host, but backups are taken off-host.
5. **Same topology, every host** — the compose model is identical whether deployed at Hosi Fourways, in SITA's preferred environment, or on AWS. Only image tags / TLS / ingress differ. No re-architecture.
6. **Keep a rollback path** — the current dev stack stays intact until a stage is signed off.
7. **VPN-gated access** — Hosi LAN `192.168.101.0/24` is only reachable via VPN (per-request access provisioning). No public exposure during Stage A.

---

## 6. Phased Plan

### Phase 0 — Access & inventory (D −3 to D −1)

- [ ] Confirm VPN access to `192.168.101.0/24` for each dev team member (request via Arezoo / IT)
- [ ] Verify SSH reachability: `ssh tk@192.168.101.20` (or provided user) from a VPN-connected jump host
- [ ] Confirm target server has Docker + Compose: `docker --version && docker compose version`
- [ ] Confirm GHCR images are pullable from the server (public, no auth needed)
- [ ] Record server hostname, IP, available disk/memory

Decisions to lock:

| Decision | Options |
|----------|---------|
| Public/LAN URL | `http://192.168.101.20` vs internal DNS name |
| TLS | Skip for Stage A; add Let's Encrypt / internal CA in Stage A+ |
| Data | Fresh init + HR seed on first boot (no legacy data yet) |
| Access model | VPN-only (LAN) vs public IP (not recommended for Stage A) |

Deliverable: written access plan + owner list.

---

### Phase 1 — Prepare Hosi Fourways Linux server

1. Apply OS updates: `sudo apt update && sudo apt upgrade -y`
2. Create deploy user with SSH keys; disable password auth if possible.
3. Ensure Docker Engine + Compose plugin installed (Docker 24+ / Compose v2).
4. Prepare the deployment directory (clone once, or copy compose + scripts):

```bash
sudo mkdir -p /opt/sita && sudo chown $USER /opt/sita
git clone --depth 1 https://github.com/takawira-mazando/sita-consolidated-security-reporting.git /opt/sita/sita-platform
```

5. Create `.env` in `infrastructure/` with strong secrets:

```bash
cd /opt/sita/sita-platform/infrastructure
openssl rand -hex 32 | xargs -I{} echo "DB_PASSWORD={}"  >> .env
openssl rand -hex 32 | xargs -I{} echo "REDIS_PASSWORD={}" >> .env
openssl rand -hex 64 | xargs -I{} echo "JWT_SECRET={}"     >> .env
openssl rand -hex 20 | xargs -I{} echo "BOOTSTRAP_ADMIN_PASSWORD={}" >> .env
echo "BOOTSTRAP_ADMIN_EMAIL=admin@sita.local" >> .env
echo "SEED_DEMO_USERS_ENABLED=false" >> .env
echo "ENVIRONMENT=production" >> .env
chmod 600 .env
```

6. Firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp    # nginx (Stage A; drop or TLS-gate later)
sudo ufw enable
```

---

### Phase 2 — Deploy the stack (Stage A)

```bash
cd /opt/sita/sita-platform/infrastructure
docker compose -f docker-compose.remote.yml --env-file .env pull
docker compose -f docker-compose.remote.yml --env-file .env up -d
docker compose -f docker-compose.remote.yml --env-file .env ps
```

Smoke tests:

1. `curl -s http://localhost:80/api/v1/public/summary` → JSON with findings/assets
2. `curl -s http://localhost:80/api/v1/auth/demo-accounts` → 200 (demo accounts visible for login page)
3. Browser: open `http://192.168.101.20` → login page renders
4. Log in with bootstrap admin; verify tenant scope + dashboard access

Verify seeds took effect (HR system present):

```bash
docker compose exec -T postgres psql -U sita -d sita -c '\dn'
docker compose exec -T postgres psql -U sita -d sita -c 'SELECT count(*) FROM hr.employees;'
```

---

### Phase 3 — Backup & observability baseline

1. Set up nightly Postgres backup on the host:

```bash
docker compose exec -T postgres pg_dump -U sita -Fc sita > /opt/sita/backups/sita_$(date +%F).dump
```

   (adapt `infrastructure/scripts/backup.sh` + a cron entry; keep copies off-host)
2. Optional: enable Prometheus/Grafana compose services (`infrastructure/monitoring/`)
3. Confirm container log rotation (already set to 10m x 3 in compose)

---

### Phase 4 — Cutover (Stage A live)

1. Point dev team / stakeholders at `http://192.168.101.20` (VPN required).
2. Update README / docs "access" section with the LAN URL.
3. Keep local dev stack running as fallback until sign-off.

---

### Phase 5 — Ship to SITA's preferred environment (Stage B — the customer deliverable)

The SITA platform is **shipped to SITA** as portable Docker containers. SITA chooses the environment; we hand over the same images and topology that ran at Stage A, plus a runbook.

#### 5.1 Shipping bundle

A self-contained package handed to SITA (or run remotely with their consent):

| Item | Contents |
|------|----------|
| `infrastructure/docker-compose.remote.yml` | The runnable compose stack (backend, frontend, postgres, redis, nginx) |
| `infrastructure/docker-compose.prod.yml` | The production/compliance variant (replicas, TLS, resource limits) |
| `infrastructure/nginx/sita-http.conf` + `sita.conf` | HTTP and HTTPS ingress configurations |
| `infrastructure/scripts/init-db.sql`, `seed-hr-system.sql`, `seed-hr-system-branches.sql` | Schema + HR seed (Postgres first-boot) |
| `.env.template` | Required secrets/configuration with placeholders |
| GHCR images | `ghcr.io/takawira-mazando/sita-backend:latest`, `sita-frontend:latest` (public, pullable without credentials) |
| `DEPLOYMENT_RUNBOOK` | Phase-by-phase install, smoke tests, backup/restore, rollback |
| Export of `openapi.json` + system documentation | For SITA's integration, security review, and audit |

Alternatively, SITA may prefer a **bundle on media** (USB/artefact) if their environment is air-gapped from GitHub/GHCR — the images can be `docker save`d to tar files and `docker load`ed offline.

#### 5.2 Deployment flow on SITA's environment

```bash
# On SITA's chosen host (Docker required)
# 1. Load images (online: pull; air-gapped: docker load from tar)
docker pull ghcr.io/takawira-mazando/sita-backend:latest
docker pull ghcr.io/takawira-mazando/sita-frontend:latest

# 2. Provision
mkdir -p /opt/sita && cp -r sita-bundle/* /opt/sita/
cd /opt/sita/infrastructure
cp .env.template .env && $EDITOR .env   # SITA supplies production secrets

# 3. Start
docker compose -f docker-compose.remote.yml --env-file .env up -d

# 4. Verify
curl -s http://localhost:80/api/v1/public/summary
```

#### 5.3 Environment-specific notes for SITA

| SITA's environment | Notes |
|--------------------|-------|
| On-prem / their own servers | Provide the shipping bundle + runbook; they run it, or we do a supported install with their credentials |
| Their cloud (any provider) | Same compose; ingress is the only provider-specific piece (LB/NSG/security group) |
| Air-gapped network | `docker save`/`load` image tars; no dependency on GHCR at runtime |
| Kubernetes-based | Compose can be converted (compose → k8s) — same images, no code change |

**Hosi's role shifts** from "the environment" to "the vendor of the containerized system": we ship, support, patch images, and provide documentation. Whether we also **operate** the environment depends on the agreement (see Stage C).

---

### Phase 6 — AWS, only as a Hosi-managed cloud service (Stage C — optional)

AWS is **not the default destination**. The system is cloud-based and managed from AWS **only if Hosi Technologies operates it from there**. If Hosi runs SITA as a managed cloud service (Hosi operates the platform on behalf of SITA), AWS is the right long-term home. If SITA prefers to host it themselves, the same containers are shipped to their environment (Stage B) and AWS is out of scope.

#### When AWS is the choice (Hosi-managed SaaS / managed service)

```
Internet
   ▼ HTTPS :443
┌──────────────────────────────────────────────┐
│ Application Load Balancer (ALB)              │
│   • TLS (ACM), WAF optional                  │
└──────────────┬───────────────────────────────┘
               ▼
┌──────────────────────────────────────────────┐
│ ECS Fargate (or EC2 ASG) — sita-backend ×N   │
│   • sita-frontend (nginx container)          │
│   • ingestion / processing / dispatch /      │
│     analytics workers (from GHCR images)     │
└──────────────┬───────────────────────────────┘
               ▼
┌──────────────────────────────────────────────┐
│ Amazon RDS PostgreSQL (Multi-AZ)             │
│   • automated backups + PITR                 │
│   • RDS Proxy (optional pooling)             │
└──────────────────────────────────────────────┘
   + ElastiCache Redis (HA)                    │
   + S3 (dumps, exports, AG attestations)      │
   + Secrets Manager / SSM Parameter Store     │
   + CloudWatch (metrics, logs, alarms)        │
   + Route 53 + ACM (DNS/TLS)                  │
   + ECR mirror of GHCR images                 │
```

#### Lift-and-shift mapping (Stage A/C compose → AWS)

| Hosi Linux / shipped compose | AWS (managed by Hosi) | Change |
|------------------------------|-----------------------|--------|
| `postgres` container | RDS PostgreSQL Multi-AZ | Managed HA + backups |
| `redis` container | ElastiCache Redis | Managed, multi-AZ optional |
| `backend`/`frontend`/workers | ECS Fargate tasks/services | `deploy.replicas` semantics from `docker-compose.prod.yml` map 1:1 to ECS service count |
| nginx `:80` | ALB + ACM TLS | TLS handled by load balancer |
| `.env` on host | Secrets Manager / SSM | No secrets on disk |
| host `pg_dump` cron | RDS automated snapshots + PITR | No custom cron needed |
| `sita.conf` HTTPS-only | ALB TLS | CSP/HSTS preserved at LB layer |

The existing `docker-compose.prod.yml` (which already expresses replicas, healthchecks, resource limits, logging) is the **draft of the AWS compose** — run it through Compose→ECS conversion, or transcribe services into CDK/Terraform.

#### Why AWS (Stage C) only when Hosi operates it

| Need | SITA's environment (Stage B) | AWS managed by Hosi (Stage C) |
|------|------------------------------|-------------------------------|
| Ownership | SITA runs it (their ops) | Hosi operates on SITA's behalf |
| Uptime/HA | Depends on SITA's host | Multi-AZ ALB+RDS; autoscaling |
| Scaling | Manual; host-bound | Elastic (Fargate/ASG) |
| Backups/DR | SITA's responsibility (runbook) | RDS PITR + snapshots; S3 versioning |
| Compliance attestation | SITA's environment, their audit | Managed services + audit logs + regions |
| Ops burden | SITA (or Hosi-supported install) | Hosi-managed operations |
| Cost | SITA bears hosting cost | Hosi bears/marks up managed service |

> **Staging logic:** Stage A (Hosi Fourways) proves the containerized platform works. Stage B ships those same containers to SITA's environment — the actual deliverable. Stage C (AWS) applies **only** if Hosi Technologies takes on operating the system as a cloud-based managed service; then AWS provides the scale, HA, DR, and auditability Hosi needs to run it well.

---

## 7. Rollback Plan (Stage A)

If the Hosi Linux deployment fails after cutover:

1. Point stakeholders back to the local dev environment (`http://localhost:3000`) for continuity.
2. Fix forward on the host (logs, env, nginx) — the compose image-driven model makes re-deploy fast:

```bash
cd /opt/sita/sita-platform/infrastructure
docker compose -f docker-compose.remote.yml --env-file .env pull && docker compose -f docker-compose.remote.yml --env-file .env up -d
```

3. If the host itself is unusable, rebuild on a fresh Hosi Linux VM from the same compose + `.env` (data loss limited to Postgres volume; restore from backup).
4. **Stage B (SITA) is never blocked by Stage A state** — the same GHCR images and compose are shipped to SITA's environment regardless.
5. **Stage C (AWS, if Hosi operates it)** restores from the same GHCR images + RDS import; independent of earlier stages.

Rollback for a Stage B (SITA) deployment is defined in the runbook shipped with the bundle: SITA reverts to their previous environment or to a known-good image tag.

---

## 8. Security Checklist (Stage A)

- [ ] UFW: only SSH + 80 (management via VPN; no public admin ports)
- [ ] Strong unique `DB_PASSWORD`, `REDIS_PASSWORD`, `JWT_SECRET`, `BOOTSTRAP_ADMIN_PASSWORD`
- [ ] `.env` never committed; `chmod 600` on the host
- [ ] SSH key-only auth; password auth disabled
- [ ] `SEED_DEMO_USERS_ENABLED=false` in production `.env`
- [ ] Bootstrapped admin credentials distributed via secure channel, then rotated
- [ ] Nightly Postgres dump + off-host copy
- [ ] Docker log rotation (configured in compose)
- [ ] VPN-only access to `192.168.101.0/24` per individual (IT request)
- [ ] Shipping bundle: no secrets in compose/template; `.env.template` uses placeholders only
- [ ] Air-gapped delivery: images verified via checksum/SBOM before `docker load`

---

## 9. Operational Commands (Stage A)

```bash
# Status
docker compose -f docker-compose.remote.yml --env-file .env ps

# Logs
docker compose -f docker-compose.remote.yml --env-file .env logs -f --tail 100 backend

# Redeploy after image update (pull latest GHCR tag)
cd /opt/sita/sita-platform/infrastructure
docker compose -f docker-compose.remote.yml --env-file .env pull
docker compose -f docker-compose.remote.yml --env-file .env up -d

# Health
curl -s http://localhost:80/api/v1/public/summary

# Backup
docker compose exec -T postgres pg_dump -U sita -Fc sita > /opt/sita/backups/sita_$(date +%F).dump

# Restore (disaster)
docker compose exec -T postgres pg_restore -U sita -d sita --clean /opt/sita/backups/sita_YYYY-MM-DD.dump

# Prepare offline shipping bundle (air-gapped SITA environment)
docker save ghcr.io/takawira-mazando/sita-backend:latest ghcr.io/takawira-mazando/sita-frontend:latest \
  | gzip > sita-images.tar.gz
```

---

## 10. Suggested Timeline

| Day | Activity |
|-----|----------|
| D−3 | VPN access request to IT for `192.168.101.0/24` (per individual) |
| D−2 | Confirm SSH + Docker on Hosi Fourways Linux; clone repo |
| D−1 | Deploy stack from GHCR images; verify seeds + health |
| D0 | Smoke test UI/API; sign-off by stakeholder |
| D+1…D+7 | Hypercare; nightly backups verified |
| D+8…D+30 | Assemble shipping bundle + runbook; agree SITA's preferred environment |
| D+30+ | Deploy at SITA (Stage B) — and only if Hosi operates the cloud: AWS kickoff (Stage C) |

---

## 11. Open Decisions (fill before execution)

| Item | Decision | Owner |
|------|----------|-------|
| Hosi server SSH user/credentials | | IT / Arezoo |
| LAN URL vs DNS name | | |
| TLS on Stage A (immediately vs later) | | |
| **SITA's preferred environment** (on-prem / their cloud / third-party) | | Hosi + SITA |
| **Delivery model** (Hosi-supported install vs SITA-run vs Hosi-managed cloud) | | Hosi + SITA |
| Air-gapped delivery (media) vs online pull | | SITA |
| AWS only if Hosi operates it — landing zone (account, region `af-south-1`, VPC), IaC tool | | Hosi (conditional) |
| Sign-off owner + cutover date | | |

---

## 12. Summary

| | Local dev (today) | Hosi Fourways Linux (Stage A) | SITA's environment (Stage B — the deliverable) | AWS managed by Hosi (Stage C — conditional) |
|--|-------------------|------------------------------|------------------------------------------------|---------------------------------------------|
| Host | Windows dev box | Existing Hosi Linux server | SITA's chosen environment | AWS managed (RDS/ECS/ALB) |
| Images | Build in Docker Desktop | **Pull GHCR images** | Same GHCR images (or offline tar) | Same GHCR → ECR |
| Cost | n/a | Free (existing asset) | SITA bears hosting cost | Hosi bears/marks up managed service |
| Licensing | — | None (Ubuntu LTS) | Per SITA's host | None (AWS-managed) |
| Accessibility | Local only | VPN-gated LAN | SITA's network | Public HTTPS |
| HA/DR | None | Host-level backups | Per SITA's environment + runbook | Multi-AZ, PITR, autoscale |
| Fit | Dev | **Now** — cost-effective, accessible | **The customer deliverable** — shipped to SITA | **Only if Hosi runs the cloud** — scale/HA/audit |

**Recommendation:** deploy **now** to the Hosi Fourways Linux server from prebuilt GHCR images (Stage A) as the working reference. The real deliverable is **portable Docker containers** shipped to **SITA's preferred environment** (Stage B) with compose files, images, `.env.template`, and a runbook. **AWS (Stage C) is included only if Hosi Technologies operates the system as a cloud-based managed service**; otherwise it is out of scope and SITA's own environment is the deployment target. The Windows/AnyDesk option is excluded because its evaluation license expires in < 30 days, forcing a high-risk mid-flight re-license for no architectural benefit.
