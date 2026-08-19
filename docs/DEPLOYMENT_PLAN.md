# Deployment Strategy — Hosi Fourways Linux (now) → Amazon AWS (long-term)

**Project:** SITA Consolidated Security Reporting (`sita-platform`)
**Repo:** https://github.com/takawira-mazando/sita-consolidated-security-reporting
**From:** Local Windows dev machine (Docker Desktop, no persistent hosting)
**To (now):** Linux Docker host at Hosi Technologies, Fourways, Johannesburg, South Africa
**To (ultimate):** Amazon Web Services (AWS) — managed, scalable, resilient
**Date:** 19 August 2026
**Related docs:** [SITA_Platform_System_Documentation.md](./SITA_Platform_System_Documentation.md), [Role-Provisioning-Roadmap.html](./Role-Provisioning-Roadmap.html)

---

## 1. Goal

Stand up the SITA platform in Docker on a persistent, accessible host, in two stages:

| Stage | Target | Rationale |
|-------|--------|-----------|
| **Stage A (now)** | Linux server at Hosi Fourways (LAN `192.168.101.x`) | Cost-effective today; no licensing; already has Docker; under our physical control |
| **Stage B (ultimate)** | Amazon AWS | Long-term home: managed services, elastic scale, HA/DR, compliance-ready |

Success criteria (Stage A):

- Platform reachable at a stable HTTP URL on the Hosi LAN / via VPN
- Backend, frontend, Postgres, Redis running from **prebuilt GHCR images** (no source build on server)
- HR schema + demo/seed data initialized on first boot
- Strong generated secrets; demo seeding disabled; admin bootstrap active
- Documented, near-identical path to lift into AWS later

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

**Verdict:** Linux at Hosi Fourways is the accessible, cost-effective, low-risk choice **now**. It also keeps the exact same compose topology that will later be lifted into AWS — the Windows path would force a parallel, incompatible deployment model for zero benefit.

---

## 5. Deployment Principles

1. **Image-driven, not build-driven** — the server pulls GHCR images; it never compiles.
2. **Fresh secrets everywhere** — strong generated `JWT_SECRET`, `DB_PASSWORD`, `REDIS_PASSWORD`, bootstrap admin password; `SEED_DEMO_USERS_ENABLED=false` in production.
3. **Server-side state is disposable** — Postgres/Redis volumes live on the host, but backups are taken off-host.
4. **Same topology, different host** — Stage A compose ≈ Stage B AWS compose (only image tags / TLS / ingress differ). No re-architecture later.
5. **Keep a rollback path** — the current dev stack stays intact until Stage A is signed off.
6. **VPN-gated access** — Hosi LAN `192.168.101.0/24` is only reachable via VPN (per-request access provisioning). No public exposure during Stage A.

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

### Phase 5 — AWS: the ultimate long-term deployment

AWS is the **strategic target**. It is chosen for the long term because the platform is a government-facing security reporting system that will eventually need: managed scaling, regional resilience, compliance attestation, and professional SLAs. Stage A is explicitly a stepping stone, not the endpoint.

#### Target AWS architecture (Stage B)

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

#### Lift-and-shift mapping (Stage A → Stage B)

| Stage A (Hosi Linux) | Stage B (AWS) | Change |
|----------------------|---------------|--------|
| `postgres` container | RDS PostgreSQL Multi-AZ | Managed HA + backups |
| `redis` container | ElastiCache Redis | Managed, multi-AZ optional |
| `backend`/`frontend`/workers | ECS Fargate tasks/services | `deploy.replicas` semantics from `docker-compose.prod.yml` map 1:1 to ECS service count |
| nginx `:80` | ALB + ACM TLS | TLS handled by load balancer |
| `.env` on host | Secrets Manager / SSM | No secrets on disk |
| host `pg_dump` cron | RDS automated snapshots + PITR | No custom cron needed |
| `sita.conf` HTTPS-only | ALB TLS | CSP/HSTS preserved at LB layer |

The existing `docker-compose.prod.yml` (which already expresses replicas, healthchecks, resource limits, logging) is the **draft of the AWS compose** — run it through `amazon-ecs-cli` / Compose→ECS conversion, or transcribe services into CDK/Terraform.

#### Why AWS (Stage B) wins long-term

| Need | Linux at Hosi (Stage A) | AWS (Stage B) |
|------|------------------------|---------------|
| Uptime/HA | Single host; manual recovery | Multi-AZ ALB+RDS; autoscaling |
| Scaling | Manual; host-bound | Elastic (Fargate/ASG) |
| Backups/DR | Host cron + off-host copy | RDS PITR + snapshots; S3 versioning |
| Compliance attestation | Manual | Managed services + audit logs + regions |
| Ops burden | Ours (patching, storage, network) | Shifted to AWS-managed layer |
| Cost at small scale | Lowest (existing asset) | Moderate (still cost-effective at scale) |
| Latency for SA users | Good (SA-hosted) | Choose `af-south-1` (Cape Town) for similar |

> **Staging logic:** AWS becomes worth it when the platform outgrows one box — multi-tenant production traffic, SLAs, or audit obligations. Until then, Hosi Fourways Linux is the right-sized, free, accessible host — and the lift path is deliberately small because both stages share the same compose/images.

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
4. Stage B (AWS) is never blocked by Stage A state — it restores from the same GHCR images + RDS import.

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
| D+30+ | Decide AWS kickoff (Stage B) when scale/SLA warrants |

---

## 11. Open Decisions (fill before execution)

| Item | Decision | Owner |
|------|----------|-------|
| Hosi server SSH user/credentials | | IT / Arezoo |
| LAN URL vs DNS name | | |
| TLS on Stage A (immediately vs later) | | |
| AWS landing zone (account, region `af-south-1`, VPC) | | |
| AWS IaC tool (CDK / Terraform / Compose→ECS) | | |
| Sign-off owner + cutover date | | |

---

## 12. Summary

| | Local dev (today) | Hosi Fourways Linux (Stage A) | AWS (Stage B — ultimate) |
|--|-------------------|------------------------------|---------------------------|
| Host | Windows dev box | Existing Hosi Linux server | AWS managed (RDS/ECS/ALB) |
| Images | Build in Docker Desktop | **Pull GHCR images** | Same GHCR → ECR |
| Cost | n/a | Free (existing asset) | Pay-as-you-go (at scale) |
| Licensing | — | None (Ubuntu LTS) | None (AWS-managed) |
| Accessibility | Local only | VPN-gated LAN | Public HTTPS |
| HA/DR | None | Host-level backups | Multi-AZ, PITR, autoscale |
| Fit | Dev | **Now** — cost-effective, accessible | **Long-term** — when scale/SLA/compliance demand it |

**Recommendation:** deploy **now** to the Hosi Fourways Linux server from prebuilt GHCR images (Stage A), keep the compose topology identical, and treat that deployment as the rehearsal for AWS (Stage B) — the same images and compose model lift into ECS/RDS with minimal rework. The Windows/AnyDesk option is excluded because its evaluation license expires in < 30 days, forcing a high-risk mid-flight re-license for no architectural benefit.
