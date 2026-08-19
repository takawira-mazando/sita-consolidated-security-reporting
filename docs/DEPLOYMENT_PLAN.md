# SITA Platform — Detailed Deployment Plan (Enriched)

**Project:** SITA Consolidated Security Reporting (`sita-platform`)
**Repo:** https://github.com/takawira-mazando/sita-consolidated-security-reporting
**Deployment unit:** Docker containers (prebuilt images on GHCR) — portable to any Docker-capable host
**From:** Local Windows dev machine (Docker Desktop, no persistent hosting)
**To (now):** Linux Docker host at Hosi Technologies, Fourways, Johannesburg, South Africa
**To (customer):** SITA's preferred environment (their own servers / cloud / chosen platform)
**To (Hosi-managed cloud, optional):** Amazon Web Services (AWS) — only if Hosi Technologies operates the system as a cloud-based, managed service
**Date:** 19 August 2026
**Version:** 2.0 (enriched)
**Status:** Phase 0 ✅ · Phase 1 ✅ (script ready) · Phase 2 🔄 (execution started) · Phases 3–6 ⬜
**Related docs:** [SITA_Platform_System_Documentation.md](./SITA_Platform_System_Documentation.md), [Role-Provisioning-Roadmap.html](./Role-Provisioning-Roadmap.html)

---

## 1. Executive Summary

The SITA platform is built and running only on a local Windows dev machine today. This plan deploys it as **portable Docker containers** to a Linux server on the Hosi Technologies LAN (`192.168.101.20`, hostname `unified`, Ubuntu 26.04 LTS), using **prebuilt public GHCR images** — the server pulls images, it never compiles.

This Linux deployment (Stage A) is the *working reference* and proves the containerized platform. The real deliverable is **shipping the same containers to SITA's preferred environment** (Stage B), with compose files, images, `.env.template`, and a runbook. AWS (Stage C) is included **only if** Hosi Technologies operates the system as a cloud-based managed service; otherwise it is out of scope.

The deployment is **image-driven, not build-driven**: no source code ever needs a compiler on the target host; the same image digest deployed at Stage A is exactly what gets shipped to Stage B or lifted into AWS.

**Current execution status:**
- Host `unified` is inventoried and reachable via the `hosiai` tailnet jump node.
- `infrastructure/scripts/deploy-remote-linux.sh` is written and ready (installs Docker if missing, generates strong secrets, pulls GHCR images, `up -d`, health-check).
- VPN access to `192.168.101.0/24` is requested from IT; per-individual provisioning pending — the single blocker before the one-shot deploy can run.

---

## 2. Goal, Scope, and Success Criteria

### 2.1 Goal

Deliver the SITA platform as **portable Docker containers** that run identically wherever they are placed, and stand them up in stages:

| Stage | Target | Rationale | Owned by |
|-------|--------|-----------|----------|
| **Stage A (now)** | Linux server at Hosi Fourways (LAN `192.168.101.20`) | Cost-effective immediately; no licensing; existing Hosi asset; under our control | Hosi Dev |
| **Stage B (customer)** | **SITA's preferred environment** | The platform is **shipped to SITA** — deployed as Docker containers on the environment SITA chooses (on-prem, their cloud, third-party hosting) | SITA + Hosi support |
| **Stage C (optional)** | Amazon AWS | **Only if Hosi Technologies operates the system as a cloud-based managed service** — managed services, elastic scale, HA/DR | Hosi Ops |

### 2.2 Key principle

**AWS is not the default destination.** The deliverable is a containerized system. AWS is one hosting option among several, and only makes sense when Hosi Technologies operates it as a managed cloud service. If SITA specifies a different environment, the **same Docker images and compose topology** are shipped there unchanged (Stage B).

### 2.3 Success criteria (Stage A)

| # | Criterion | How it is measured / verified |
|---|-----------|-------------------------------|
| S1 | Platform reachable at a stable HTTP URL on the Hosi LAN / via VPN | `curl http://192.168.101.20` returns 200; login page renders in a browser |
| S2 | Backend, frontend, Postgres, Redis running from **prebuilt GHCR images** (no source build on server) | `docker compose ps` = 5 services `Up`; `docker image ls` shows `ghcr.io/takawira-mazando/*` images; no build context on host |
| S3 | HR schema + seed data initialized on first boot | `\dn` shows `hr` schema; `SELECT count(*) FROM hr.employees;` returns seeded rows |
| S4 | Strong generated secrets; demo seeding disabled; admin bootstrap active | `.env` is `chmod 600`; `SEED_DEMO_USERS_ENABLED=false`; bootstrap admin login succeeds |
| S5 | A **portable shipping bundle** ready for SITA | Bundle assembled (compose + images + `.env.template` + runbook) and validated in Stage B rehearsal |
| S6 | Backups running and restorable | Nightly `pg_dump` cron active; one restore drill passed (`backup.sh drill`) |

---

## 3. Stakeholders & Responsibility (RACI)

| Activity | Hosi Dev (hero) | Hosi Ops/IT | SITA | Tooling/Asset |
|----------|-----------------|-------------|------|----------------|
| Access provisioning (VPN `192.168.101.0/24`, per individual) | C | **A/R** | — | IT VPN request via Arezoo |
| Host inventory & SSH access to `unified` | **R** | C | — | Tailscale `hosiai` jump |
| Run deploy script / stand up stack | **A/R** | C | I | `deploy-remote-linux.sh` |
| Generate & custody secrets (`.env`) | **A/R** | I | — | `openssl rand`, `chmod 600` |
| Verify health, seeds, smoke tests | **R** | I | — | curl + browser + psql |
| Decision: SITA's preferred environment | C | — | **A/R** | Commercial agreement |
| Sign-off of Stage A cutover | **A** | C | I | Stakeholder review |
| Ship bundle + runbook to SITA | **A/R** | C | C | `docker save` tars + docs |
| Operate Staged B environment | C | C | **R** (or Hosi under service agreement) | Runbook |
| Operate Stage C AWS (if chosen) | C | **A/R** | I | CDK/Terraform + AWS |

Legend: R = Responsible, A = Accountable, C = Consulted, I = Informed.

---

## 4. Current State (Local Windows / Dev)

```
Dev machine (Windows, hosi)
   ├── Docker Desktop (dev compose: postgres, redis, backend, frontend)
   ├── Uvicorn on 127.0.0.1:8000 + Vite dev on 127.0.0.1:3000 (dual-stack ::)
   └── No persistent host / public URL / backups / monitoring
```

### 4.1 What exists in the repo today

| Asset | Purpose |
|-------|---------|
| `infrastructure/docker-compose.remote.yml` | The Stage A stack — pulls `ghcr.io/…/sita-backend:latest` + `sita-frontend:latest`, Postgres 16, Redis 7, nginx :80 |
| `infrastructure/docker-compose.prod.yml` | Production/compliance variant — replicas, workers (ingestion/processing/dispatch/analytics), resource limits, HTTPS nginx; the draft of the AWS compose |
| `infrastructure/nginx/sita-http.conf` | HTTP entrypoint for first deploy (no TLS dependency) |
| `infrastructure/nginx/sita.conf` | HTTPS-only TLS config (Stage B/prod) |
| `infrastructure/scripts/init-db.sql`, `seed-hr-system.sql`, `seed-hr-system-branches.sql` | Schema + HR seed mounted into Postgres first-boot (`/docker-entrypoint-initdb.d/01…03`) |
| `infrastructure/scripts/deploy-remote.ps1` | Windows-side bootstrap (secondary; superseded) |
| `infrastructure/scripts/deploy-remote-linux.sh` | **Linux (primary) bootstrap** — one-shot deploy (details in §9) |
| `infrastructure/scripts/backup.sh` | PostgreSQL `pg_basebackup`, WAL archiving helper, PITR restore drill, backup verify |
| `infrastructure/monitoring/prometheus.yml` | Scrape config for backend `/metrics`, postgres-exporter (:9187), redis-exporter (:9121) |
| `.github/workflows/ci.yml`, `publish-ghcr.yml` | CI + publish images to GitHub Container Registry on `main` |
| `backend/.env.example` | Full reference of configuration keys (secrets + tuning knobs) |
| `docs/` | System documentation, role-provisioning roadmap |

### 4.2 GHCR images (public, pullable without credentials)

```bash
docker pull ghcr.io/takawira-mazando/sita-backend:latest
docker pull ghcr.io/takawira-mazando/sita-frontend:latest
```

Verified public via `docker manifest inspect` on 19 Aug 2026. The publisher workflow tags `latest` on every merged `main`. For reproducible deployments, pin a **specific digest/tag** (`git sha` tag) once Stage A is signed off.

---

## 5. Target State (Stage A — Hosi Fourways Linux)

### 5.1 Confirmed host inventory (captured 19 Aug 2026)

| Attribute | Value |
|-----------|-------|
| Hostname | `unified` |
| IP | `192.168.101.20` (LAN `192.168.101.0/24`) |
| OS | Ubuntu 26.04 LTS (GNU/Linux 7.0.0-30-generic x86_64) |
| SSH user | `uni` |
| Access path | Via `hosiai` tailnet node (`100.116.102.102`) → `ssh uni@192.168.101.20` (VPN / jump host required from `hosi`) |
| Disk | 97.87 GB used 11.4% — ample (~87 GB free) |
| Memory | ~1% used at inventory — plenty for the stack |
| Docker | To be installed by `deploy-remote-linux.sh` (script auto-installs if missing) |

### 5.2 Target topology

```
LAN users / VPN
   │ HTTP :80
   ▼
┌──────────────────────────────────────┐
│  HOSI FOURWAYS LINUX SERVER          │
│  hostname: unified (192.168.101.20)  │
│  Ubuntu 26.04 LTS, user: uni         │
│  • Docker Compose: sita stack        │
│  • backend    :8000 (internal)       │
│  • frontend   :80   (internal)       │
│  • postgres 16 + redis 7 (internal)  │
│  • nginx      :80   → frontend/API   │
│  • GHCR images pulled, no build      │
└──────────────────────────────────────┘
```

### 5.3 Compose service map (as expressed by `docker-compose.remote.yml`)

| Service | Image | Ports (host) | Healthcheck | Volume | Notes |
|---------|-------|--------------|-------------|--------|-------|
| `postgres` | `postgres:16-alpine` | none | `pg_isready -U sita -d sita` (10s/5s/5) | `pgdata`, `pg_wal` | `POSTGRES_DB/USER=sita`; seeds mounted `01/02/03`; log rotation 10m×3 |
| `redis` | `redis:7-alpine` | none | `redis-cli ping` (10s/3s/3) | `redis_data` | `--requirepass ${REDIS_PASSWORD}` |
| `backend` | `ghcr.io/takawira-mazando/sita-backend:latest` | none | — | — | `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` (required), `SEED_DEMO_USERS_ENABLED=false`, bootstrap admin env; waits on postgres+redis healthy |
| `frontend` | `ghcr.io/takawira-mazando/sita-frontend:latest` | none | — | — | depends on backend |
| `nginx` | `nginx:1.25-alpine` | **80 → 80** | — | mounts `sita-http.conf` ro | sole public entrypoint; proxies frontend + `/api` |

### 5.4 Recommended sizing (start)

| Server | CPU | RAM | Disk | Notes |
|--------|-----|-----|------|-------|
| Hosi Fourways Linux (`unified`) | 4+ vCPU | 8+ GB | 100 GB SSD | Compose stack + images + DB + backups (~package target) |
| Stage B (SITA on-prem equivalent) | 4+ vCPU | 8+ GB | 100 GB SSD | Same topology; scale to multi-worker `docker-compose.prod.yml` if load demands |
| Stage C (AWS, if Hosi-managed) | per-service Fargate/ASG | per-service | RDS allocated storage | See §17 |

---

## 6. Why Linux (Hosi Fourways) over Windows (AnyDesk box)

The current alternative — a Windows box reachable via AnyDesk (`Administrator` / eval licensing) — was evaluated and set aside. The deciding factor: **Windows Server licensing on that box expires in < 30 days**, which forces a re-license or re-build mid-flight.

| Factor | Linux (Hosi Fourways) | Windows Server (AnyDesk box) |
|--------|------------------------|------------------------------|
| **Licensing** | Free (Ubuntu LTS); no expiry | Per-core/OS licensing; **eval expires < 30 days** → urgent renewal risk |
| **Docker** | Native engine, `docker compose` v2; 1:1 with our compose files | Docker Desktop or Windows containers; **Windows containers need matching host build** (kernel-version pinning) |
| **Images** | Pull GHCR Linux images directly | Linux images won't run without a Linux VM/WSL2 layer — extra moving parts |
| **Ops tooling** | `deploy-remote-linux.sh`, `backup.sh`, UFW, cron — battle-tested on Linux | PowerShell equivalents must be written; no equivalent to shell scripts |
| **Footprint** | ~300 MB images, low idle RAM | Heavier base image + WSL2/VM overhead |
| **Remote access** | SSH key-based (reachable via `hosiai` tailnet / VPN) | AnyDesk GUI only — not scriptable from CI/CD |
| **Cost** | None (existing Hosi asset) | License + renewal risk + potential CALs |
| **Risk** | Low | High (expiry deadline forces urgent remediation) |

**Verdict:** Linux at Hosi Fourways is the accessible, cost-effective, low-risk choice **now**. It also keeps the exact same compose topology that can later be shipped to SITA's environment or lifted into AWS — the Windows path would force a parallel, incompatible deployment model for zero benefit.

---

## 7. Deployment Principles

1. **Image-driven, not build-driven** — the server pulls GHCR images; it never compiles. The same images are what gets shipped.
2. **Portable by construction** — everything needed to run (compose files, nginx config, init SQL, `.env` template, runbook) is in the repo. Deployment = `docker compose up` on any Docker-capable host.
3. **Fresh secrets everywhere** — strong generated `JWT_SECRET`, `DB_PASSWORD`, `REDIS_PASSWORD`, bootstrap admin password; `SEED_DEMO_USERS_ENABLED=false` in production.
4. **Server-side state is disposable** — Postgres/Redis volumes live on the host, but backups are taken off-host.
5. **Same topology, every host** — the compose model is identical whether deployed at Hosi Fourways, in SITA's preferred environment, or on AWS. Only image tags / TLS / ingress differ. No re-architecture.
6. **Keep a rollback path** — the current dev stack stays intact until a stage is signed off.
7. **VPN-gated access** — Hosi LAN `192.168.101.0/24` is only reachable via VPN (per-request access provisioning). No public exposure during Stage A.
8. **Reproducibility over re-provisioning** — scripts and compose files are the source of truth; manual host edits are logged and, where possible, folded back into the script.

---

## 8. Prerequisites & Pre-flight Checklist (Stage A)

### 8.1 Access

| # | Prerequisite | Status | Owner |
|---|--------------|--------|-------|
| P1 | SSH path from `hosi` to `192.168.101.20` usable (via `hosiai` jump or VPN) | ✅ (jump works; VPN requested) | IT / Arezoo |
| P2 | Ability to run `sudo` as `uni` on `unified` | ⬜ confirm on first SSH | `uni` |
| P3 | Outbound HTTPS (443) from `unified` to `github.com` and `ghcr.io` | ⬜ verify `curl -I https://ghcr.io` | deploy script |
| P4 | UDP/offlines not required; no inbound ports beyond 80 needed | — | — |

### 8.2 Assets

| # | Prerequisite | Status | Notes |
|---|--------------|--------|-------|
| P5 | GHCR images public / pullable | ✅ verified 19 Aug | `sita-backend:latest`, `sita-frontend:latest` |
| P6 | `deploy-remote-linux.sh` committed to `main` | ✅ commit `732e6e2` | repo cloned on host |
| P7 | `.env.template` exists in bundle (no secrets) | ⬜ create in bundle phase | placeholders only |
| P8 | Seed SQL files present & valid | ✅ in repo | bad seed = init failures (see §13) |

### 8.3 Environment

| # | Prerequisite | Status | Notes |
|---|--------------|--------|-------|
| P9 | `unified` has ≥4 GB free RAM and ≥20 GB free disk | ✅ inventory | 87 GB free |
| P10 | No existing service on port 80 (nginx/Apache host install) | ⬜ check `ss -ltnp` before deploy | port 80 must be free |
| P11 | Host clock synchronised (TLS, backups, JWT) | ✅ standard Ubuntu | `timedatectl` if needed |
| P12 | VPN access for reviewer list (each person) | ⬜ in progress with IT | per individual |

---

## 9. Phased Execution Plan

### Phase 0 — Access & inventory ✅ (completed 19 Aug 2026)

**What was done:**
- ✅ Server reached via `hosiai` tailnet node: `ssh uni@192.168.101.20`; interactive SSH works.
- ✅ Host inventory captured (`unified`, Ubuntu 26.04 LTS, 97.87 GB disk, ample RAM, kernel 7.0.0-30).
- ✅ GHCR images confirmed public / pullable without auth.
- ✅ VPN access to `192.168.101.0/24` being provisioned per individual (request via Arezoo/IT); jump access via `hosiai` works today.

**Decisions locked at Phase 0:**

| Decision | Chosen |
|----------|--------|
| Public/LAN URL | `http://192.168.101.20` (LAN, VPN-gated) |
| TLS | Deferred — HTTP for Stage A; add Let's Encrypt/internal CA after sign-off |
| Data | Fresh init + HR seed on first boot (no legacy data yet) |
| Access model | VPN-gated LAN only; no public exposure |

**Exit criteria:** inventory captured, images pullable, access path defined. ✅ MET.

### Phase 1 — Prepare host (`unified`) ✅ (automated by script)

The **`deploy-remote-linux.sh`** script performs this phase automatically when run as `uni` (with sudo). Steps performed, in order:

| # | Step | Command (inside script) | Failure handling |
|---|------|-------------------------|------------------|
| 1.1 | Install Docker if missing | apt install `docker-ce docker-ce-cli containerd.io docker-compose-plugin` from Docker's Ubuntu repo; add `$USER` to `docker` group; `systemctl enable --now docker` | `set -euo pipefail` — script halts on error with message |
| 1.2 | Fetch deployment assets | `git clone --depth 1` repo to `$DEPLOY_DIR/sita-platform` (pulls `--ff-only` if present) | halts if clone fails (check P3/P4) |
| 1.3 | Generate `.env` with strong secrets | `openssl rand -hex 32/64/20` for `DB_PASSWORD`/`JWT_SECRET`/`BOOTSTRAP_ADMIN_PASSWORD`; static values for email + `SEED_DEMO_USERS_ENABLED=false`; `chmod 600` | preserves existing `.env` if already present (idempotent) |
| 1.4 | Print bootstrap admin password | `sudo grep BOOTSTRAP_ADMIN_PASSWORD "$ENV_FILE"` | output must be captured securely (§10) |
| 1.5 | Configure UFW | `ufw allow OpenSSH`, `ufw allow 80/tcp`, `ufw --force enable` | best-effort (`|| true`) |
| 1.6 | Pull images | `docker compose … pull` | halts on failure |

**Script prerequisites:** run from a shell as `uni` with `sudo` rights; network egress to `github.com` + Docker's apt repo + `ghcr.io`.

**Manual equivalents** (if run by hand instead of the script):

```bash
sudo apt update && sudo apt upgrade -y
sudo mkdir -p /opt/sita/sita-platform
git clone --depth 1 https://github.com/takawira-mazando/sita-consolidated-security-reporting.git /opt/sita/sita-platform
cd /opt/sita/sita-platform/infrastructure
# write .env (see script for the openssl generation) then:
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw --force enable
```

**Exit criteria:** Docker present, repo cloned, `.env` generated (`chmod 600`), bootstrap password captured, UFW active.

### Phase 2 — Deploy the stack (Stage A) 🔄 (execution started)

**Primary command (one-shot):**

```bash
git clone --depth 1 https://github.com/takawira-mazando/sita-consolidated-security-reporting.git /opt/sita/sita-platform
sudo bash /opt/sita/sita-platform/infrastructure/scripts/deploy-remote-linux.sh
```

Expected outputs, step by step:

| Script output | Meaning |
|---------------|---------|
| `Docker found: …` or `Docker installed. Re-login required` | Docker present or installed |
| `Cloning repo…` / `Pulling latest…` | assets fetched to `/opt/sita/sita-platform` |
| `Generating .env with strong secrets…` + `Bootstrap admin password below` | `.env` written; **capture the password** |
| `Configuring UFW (SSH + 80)…` | firewall rule set |
| `Pulling images…`, `Starting stack…` | images pulled; `up -d` |
| `DEPLOY SUCCESS` + UI/API/health lines (`curl health` OK) | ✅ deploy verified |
| `Deploy started, health check failed…` + log hint | backend unhealthy — go to troubleshooting §13 |

Manual equivalent:

```bash
cd /opt/sita/sita-platform/infrastructure
sudo docker compose -f docker-compose.remote.yml --env-file .env pull
sudo docker compose -f docker-compose.remote.yml --env-file .env up -d
sudo docker compose -f docker-compose.remote.yml --env-file .env ps
```

**Validation checkpoint (must all pass):**

| # | Check | Command (on `unified`) | Pass = |
|---|-------|------------------------|--------|
| V1 | All containers up | `docker compose … ps` | 5 services `Up`, healthy where healthcheck set |
| V2 | Public summary API | `curl -sf http://localhost/api/v1/public/summary` | JSON with findings/assets |
| V3 | Demo accounts endpoint | `curl -sf http://localhost/api/v1/auth/demo-accounts` | 200 with demo account list |
| V4 | UI renders | browser `http://192.168.101.20` | login page loads |
| V5 | Admin login | login with bootstrap admin | dashboard renders; tenant scope correct |
| V6 | HR schema seeded | `docker compose … exec -T postgres psql -U sita -d sita -c '\dn'` | `hr` schema present |
| V7 | HR rows present | `docker compose … exec -T postgres psql -U sita -d sita -c 'SELECT count(*) FROM hr.employees;'` | > 0 seeded rows |
| V8 | No demo users enabled | `docker compose … exec -T postgres psql -U sita -d sita -c "SELECT count(*) FROM users WHERE is_demo=…;"` (or backend env) | `SEED_DEMO_USERS_ENABLED=false` also visible in backend env |
| V9 | Host firewall | `sudo ufw status` | `80/tcp` + `OpenSSH` allowed |

**Exit criteria:** V1–V9 pass. Record outputs into the deployment log.

### Phase 3 — Backup & observability baseline

1. **Nightly Postgres backup** on the host:

```bash
sudo mkdir -p /opt/sita/backups
sudo docker compose -f /opt/sita/sita-platform/infrastructure/docker-compose.remote.yml --env-file /opt/sita/sita-platform/infrastructure/.env \
  exec -T postgres pg_dump -U sita -Fc sita > /opt/sita/backups/sita_$(date +%F).dump

# cron (daily 01:15 SAST), run:
(crontab -u uni -l 2>/dev/null; echo '15 1 * * * sudo bash /opt/sita/sita-platform/infrastructure/scripts/backup.sh base') | crontab -u uni -
```

2. **Off-host copy** — sync the dump off the server (S3, NAS, or a second Hosi host). A backup that lives only on the dying host is not a backup.

3. **PITR capability** — `infrastructure/scripts/backup.sh` supports `base` (pg_basebackup), `drill "<ts>"` (restore-drill), `verify`. Schedule a drill monthly and record results.

4. **Observability (optional in Stage A):** enable Prometheus/Grafana from `infrastructure/monitoring/` (scrape targets: backend `:8000/metrics`, postgres-exporter `:9187`, redis-exporter `:9121`) — do the same after sign-off.

5. **Log rotation** already baked into compose (`10m × 3`, json-file driver) — no action needed.

**Exit criteria:** one successful dump + off-host copy verified; `backup.sh verify` passes; cron entry present.

### Phase 4 — Cutover (Stage A live)

1. Point dev team / stakeholders at `http://192.168.101.20` (VPN required).
2. Update README / docs "access" section with the LAN URL.
3. Keep local dev stack running as fallback until sign-off.
4. Announce cutover + window; record sign-off in the log.
5. Fix **image tags**: switch from `latest` to the signed-off commit-tagged images (`sita-backend:<git-sha>`, `sita-frontend:<git-sha>`) for reproducibility.

**Exit criteria:** signed-off; tags pinned; README updated.

### Phase 5 — Ship to SITA's preferred environment (Stage B — the customer deliverable)

The SITA platform is **shipped to SITA** as portable Docker containers. SITA chooses the environment; we hand over the same images and topology that ran at Stage A, plus a runbook.

#### 5.1 Shipping bundle

A self-contained package handed to SITA (or run remotely with their consent):

| Item | Contents |
|------|----------|
| `infrastructure/docker-compose.remote.yml` | The runnable compose stack (backend, frontend, postgres, redis, nginx) |
| `infrastructure/docker-compose.prod.yml` | The production/compliance variant (replicas, workers, TLS, resource limits) |
| `infrastructure/nginx/sita-http.conf` + `sita.conf` | HTTP and HTTPS ingress configurations |
| `infrastructure/scripts/init-db.sql`, `seed-hr-system.sql`, `seed-hr-system-branches.sql` | Schema + HR seed (Postgres first-boot) |
| `.env.template` | Required secrets/configuration with placeholders (no real values) |
| GHCR images | `ghcr.io/takawira-mazando/sita-backend:<sha>`, `sita-frontend:<sha>` (public) — pinned, reproducible |
| `DEPLOYMENT_RUNBOOK.md` | Phase-by-phase install, smoke tests, backup/restore, rollback (§11 content packaged as its own doc) |
| `openapi.json` export + system documentation | For SITA's integration, security review, and audit |
| SBOM / digest manifest | For air-gapped verification (see P-check §10) |

**Offline option:** if SITA's environment is air-gapped from GitHub/GHCR, ship a bundle on media (USB/artefact); the images are saved to tar with `docker save` and loaded with `docker load` (§14.3).

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

**Hosi's role shifts** from "the environment" to "the vendor of the containerized system": we ship, support, patch images, and provide documentation. Whether we also **operate** the environment depends on the agreement (see Stage C §16).

#### 5.4 Stage B acceptance checklist (run once per SITA env)

- [ ] `docker compose ps` → all services Up
- [ ] `curl http://<host>/api/v1/public/summary` → 200
- [ ] Login page renders; SSO (if configured) works
- [ ] HR seed verified (`\dn`, `hr.employees` count)
- [ ] Nightly backup cron + off-box copy configured
- [ ] TLS (if prod variant) valid; HSTS/CSP observed
- [ ] Stakeholder sign-off recorded

**Exit criteria:** bundle validated in a staged rehearsal (on a scratch host) before it leaves Hosi; acceptance checklist signed at SITA.

### Phase 6 — AWS, only as a Hosi-managed cloud service (Stage C — optional)

See §17 for the full Stage C treatment. Conditions to enter this phase:
1. SITA and Hosi agree Hosi operates the platform as a cloud-based managed service, **and**
2. Commercial agreement includes hosting, uptime (SLA), support, and ops ownership by Hosi.

**Exit criteria:** hosting agreement signed; AWS account + landing zone created; IaC scaffolded from `docker-compose.prod.yml`.

---

## 10. Secrets & Configuration Management

### 10.1 Variables in `.env` (as generated by `deploy-remote-linux.sh`)

| Variable | Value source | Sensitive | Notes |
|----------|--------------|-----------|-------|
| `DB_PASSWORD` | `openssl rand -hex 32` | 🔒 | Postgres superuser for `sita` DB |
| `REDIS_PASSWORD` | `openssl rand -hex 32` | 🔒 | Redis `--requirepass` |
| `JWT_SECRET` | `openssl rand -hex 64` | 🔒 | Signed tokens; **compose requires it** (`:?`) |
| `BOOTSTRAP_ADMIN_EMAIL` | static `admin@sita.local` | — | change to a real mailbox at sign-off |
| `BOOTSTRAP_ADMIN_PASSWORD` | `openssl rand -hex 20` | 🔒 | **print once** by script; rotate after first login |
| `SEED_DEMO_USERS_ENABLED` | `false` | — | locked off in prod |
| `ENVIRONMENT` | `production` | — | disables dev-only behaviours |

References: `backend/.env.example` lists the fuller configuration surface (AUTH0, SMTP, Teams, PagerDuty, worker tuning) for Stage B/C.

### 10.2 Rules

- `.env` is **never committed**; it is `.gitignore`d and `chmod 600`.
- The script is **idempotent**: it regenerates only if `.env` is missing; existing `.env` is preserved.
- `BOOTSTRAP_ADMIN_PASSWORD` is shown exactly once in the script output — capture it at deploy time.
- After first admin login, **rotate** the bootstrap password and store under password manager, not in the repo.
- Stage B: SITA supplies production secrets; `.env.template` ships with placeholders only.
- Stage C: move secrets to AWS Secrets Manager / SSM Parameter Store (no secrets on disk) — see §17.

---

## 11. Operational Runbook (Day-2, Stage A)

All commands run on `unified` (`ssh uni@192.168.101.20` via `hosiai`), in `/opt/sita/sita-platform/infrastructure`.

### 11.1 Status & health

```bash
# Stack status
sudo docker compose -f docker-compose.remote.yml --env-file .env ps

# Health endpoints
curl -s http://localhost:80/api/v1/public/summary

# Container health detail
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
```

### 11.2 Logs

```bash
# Follow backend logs
sudo docker compose -f docker-compose.remote.yml --env-file .env logs -f --tail 100 backend

# All services, last 200 lines
sudo docker compose -f docker-compose.remote.yml --env-file .env logs --tail 200

# nginx access/error (verify proxy works)
sudo docker compose -f docker-compose.remote.yml --env-file .env logs nginx
```

### 11.3 Redeploy after image update

```bash
# Pull the new GHCR tag then recreate changed containers
sudo docker compose -f docker-compose.remote.yml --env-file .env pull
sudo docker compose -f docker-compose.remote.yml --env-file .env up -d
```

For a clean recreate (schema/env changes), also `--force-recreate`; if `postgres` image/env changed, data must be migrated — never `down -v` without a fresh backup.

### 11.4 Backup & restore

```bash
# Backup (custom-format dump, compressible/restorable subset)
sudo mkdir -p /opt/sita/backups
sudo docker compose -f docker-compose.remote.yml --env-file .env exec -T postgres pg_dump -U sita -Fc sita \
  > /opt/sita/backups/sita_$(date +%F).dump

# Restore (disaster) — into a running postgres
sudo docker compose -f docker-compose.remote.yml --env-file .env exec -T postgres pg_restore -U sita -d sita \
  --clean --if-exists /opt/sita/backups/sita_YYYY-MM-DD.dump

# Full + WAL/PITR path (off-host capable)
sudo bash /opt/sita/sita-platform/infrastructure/scripts/backup.sh base     # full base
sudo bash /opt/sita/sita-platform/infrastructure/scripts/backup.sh drill "2026-08-20 03:00:00"  # test PITR
sudo bash /opt/sita/sita-platform/infrastructure/scripts/backup.sh verify   # verify latest set
```

### 11.5 Stop / start / teardown (careful)

```bash
# Stop (keep volumes)
sudo docker compose -f docker-compose.remote.yml --env-file .env stop

# Start again
sudo docker compose -f docker-compose.remote.yml --env-file .env start   # or: up -d

# Tear down containers+networks (KEEPS volumes)
sudo docker compose -f docker-compose.remote.yml --env-file .env down

# DESTRUCTIVE: also delete postgres/redis data volumes — ONLY after confirmed backup
sudo docker compose -f docker-compose.remote.yml --env-file .env down -v
```

### 11.6 Host maintenance

```bash
# Updates (Ubuntu security patches)
sudo apt update && sudo apt upgrade -y

# Disk space check (backups grow)
df -h /opt/sita

# Firewall state
sudo ufw status verbose
```

### 11.7 Escalation path

| Symptom | First response | Escalate to |
|---------|----------------|-------------|
| UI unreachable, API down | §13 troubleshoot; check docker/logs | Hosi Dev (SLA-owner) |
| Disk > 85% | prune old backups; `docker system prune`; check `/opt/sita/backups` | Hosi Ops |
| DB corruption / failed restore | stop services; restore from last good dump; keep dev up | Hosi Dev + backup owner |
| Security incident | disconnect from VPN; snapshot host; notify Hosi IT | Hosi IT / incident owner |

---

## 12. Verification & Acceptance Test Plan (Stage A)

### 12.1 Functional smoke (repeatable)

| Test | Steps | Expected |
|------|-------|----------|
| API summary | `curl -sf http://192.168.101.20/api/v1/public/summary` | JSON blob; exit 0 |
| Login page | browser → `http://192.168.101.20` | SPA loads; login form |
| Auth | login as bootstrap admin | dashboard renders; no console errors |
| HR data present | psql `SELECT count(*) FROM hr.employees;` | seeded count > 0 |
| Redis reachable | `docker compose … exec redis redis-cli -a "$REDIS_PASSWORD" ping` | `PONG` |
| Tenant scoping | create/switch tenants in UI | data isolation observed |

### 12.2 Non-functional checks

| Area | Check | Pass = |
|------|-------|--------|
| Resource use | `docker stats --no-stream` at idle | memory within leaves per service |
| Restart resiliency | `sudo systemctl restart docker` then `compose up -d` | stack returns to healthy; volumes intact |
| Persistence | restart postgres; data still in `hr.employees` | data survives container recreate |
| Backup restore | restore last dump into scratch DB | row counts match |

### 12.3 Acceptance gate

Secretary of the sign-off on D0 (see §19 timeline) verifies each box, signs, and dates. Any V-check failure in §9 Phase 2 blocks cutover (§Phase 4) until resolved.

---

## 13. Troubleshooting Runbook

### 13.1 Deploy script health check failed

**Symptom:** script prints `Deploy started, health check failed`.

| # | Likely cause | Diagnose | Fix |
|---|--------------|----------|-----|
| A | Backend can't reach Postgres (secrets mismatch, `postgres` not healthy) | `docker compose logs backend`, `docker compose ps postgres` | confirm `postgres` healthy; `.env` `DB_PASSWORD` consistent between postgres + backend URL |
| B | Backend can't reach Redis | `docker compose logs redis`; test `redis-cli -a $REDIS_PASSWORD ping` | confirm `REDIS_PASSWORD` matches compose command |
| C | Port 80 taken by host nginx/Apache | `sudo ss -ltnp \| grep :80` | stop host service or change mapping |
| D | Image tags/Digest mismatch after GHCR push | `docker compose pull` again; inspect `docker image ls` | pull again or pin correct sha |
| E | DNS/egress blocked | `curl -I https://ghcr.io` | check P3/network/firewall |
| F | Seed SQL error on first init | `docker compose logs postgres` | fix seed file in repo; new volume (`down -v` **only with backup**) |

### 13.2 Services crash-looping

```bash
# What does the backend think?
sudo docker compose -f docker-compose.remote.yml --env-file .env logs --tail 200 backend
# Exit codes / restarts?
sudo docker ps -a
```

Common: missing env var (compose uses `:?…` which fails fast — that's a **config** error, not runtime), CPU/mem limits in prod variant too tight (`docker stats`), or DB schema drift.

### 13.3 UI loads but API calls fail

- Check nginx proxy config (`sita-http.conf`): frontend routes `/api/*` → backend; confirm `nginx` resolves `backend:8000`.
- `curl http://localhost/api/v1/public/summary` from host — if OK but browser fails, check VPN/route on the client.

### 13.4 Postgres will not start after host crash

- Check `docker compose logs postgres` for missing `pg_wal`/permission issues; volume path `pgdata` present.
- Recover from last dump (`pg_restore`) or PITR (backup.sh drill path).
- Never run `docker compose down -v` before confirming a valid backup exists.

### 13.5 "Address already in use" for port 80 or 443

`sudo ss -ltnp | grep -E ':(80|443)'`; on `unified` a pre-existing web service would conflict — resolve before deploying.

### 13.6 Host full disk

`df -h /opt/sita`; prune old dumps (`/opt/sita/backups`, retention policy), `docker system prune -af --volumes` only when safe, then re-run backups.

---

## 14. Security Plan

### 14.1 Stage A security checklist

- [x] Host reachable only via VPN/jump (`hosiai`); no public exposure during Stage A
- [x] Strong secrets generated by `deploy-remote-linux.sh` (`openssl rand`); `.env` set to `chmod 600`
- [ ] UFW set by script: only SSH + 80 (verify with `sudo ufw status`)
- [ ] `.env` never committed; confirm `git status` clean on host (`git -C /opt/sita/sita-platform status`)
- [ ] SSH key-only auth (disable password) on `unified` — for `uni`, set up key and disable password
- [x] `SEED_DEMO_USERS_ENABLED=false` in generated `.env`
- [ ] Bootstrap admin password captured securely from script output, then rotated after first login
- [ ] Nightly Postgres dump (`backup.sh` + cron) + off-host copy
- [x] Docker log rotation (configured in compose: 10m x 3)
- [ ] Shipping bundle: no secrets in compose/template; `.env.template` uses placeholders only
- [ ] Air-gapped delivery: images verified via checksum/SBOM before `docker load`
- [ ] Backend container as non-root; no privileged containers; read-only FS where possible (image-level, verify on upstream images)
- [ ] `SEED_DEMO_USERS_ENABLED=false` re-confirmed before SITA bundle ships

### 14.2 Threat notes

| Threat | Mitigation |
|--------|-----------|
| Public exposure of Stage A | VPN-gated LAN; UFW only 80/SSH; no port-forward |
| `.env` / secrets leak | never committed; `chmod 600`; rotated after first login; Secrets Manager in Stage C |
| Compromised image | pin digests at sign-off; SBOM/checksum on air-gapped load; GHCR is signed/build from CI |
| DB data exfiltration | VPN-only reachable ports; no PUBLIC bind of postgres/redis |
| Supply chain (GHCR) | registry is repo-coupled (publish-ghcr.yml); tags pinned post-sign-off |

### 14.3 Air-gapped delivery process (Stage B)

```bash
# On an internet-connected machine (e.g., a Hosi build box)
docker save ghcr.io/takawira-mazando/sita-backend:<sha> ghcr.io/takawira-mazando/sita-frontend:<sha> | gzip > sita-images.tar.gz
# Compute manifest hashes for the bundle manifest
sha256sum sita-images.tar.gz > SHA256SUMS

# On SITA's air-gapped host
sha256sum -c SHA256SUMS && docker load -i sita-images.tar.gz
docker compose -f docker-compose.remote.yml --env-file .env up -d
```

---

## 15. Backup, Restore & DR (Stage A)

### 15.1 Strategy summary

| Layer | Mechanism | Frequency | Retention | Restore target |
|-------|-----------|-----------|-----------|----------------|
| Logical DB (primary) | `pg_dump -Fc` dump + pg_basebackup (`backup.sh base`) | nightly cron | 14 dumps / 2 base sets | Same or scratch host |
| WAL / PITR | `backup.sh` archive (needs `archive_command` per server profile) | continuous | WAL dir policy | Point-in-time |
| Off-host | rsync/object store copy of `/opt/sita/backups` | nightly after dump | 30 d | DR host / S3 |

### 15.2 Restore procedure (disaster)

1. Confirm latest known-good dump + off-host copy (`sha256sum` match).
2. Recreate environment: clone repo, write `.env` (restore secrets from vault or regenerate w/ admin rebuild).
3. Start stack with **empty** `pgdata` (`docker compose down -v` is fine now — data comes from the dump).
4. `pg_restore -U sita -d sita --clean --if-exists /opt/sita/backups/sita_<date>.dump` (or PITR replay via `backup.sh drill`).
5. Verify V2–V7 smoke checks (§9 Phase 2).
6. Record RTO/RPO observed (target RTO ≤ 4 h, RPO ≤ 24 h for logical dump; PITR improves RPO if WAL shipped).

### 15.3 Backup verification schedule

| Cadence | Action |
|---------|--------|
| Daily | cron dump; confirm non-zero file + off-host copy |
| Weekly | `backup.sh verify` |
| Monthly | `backup.sh drill "<timestamp>"` PITR rehearsal; record time-to-restore |

---

## 16. Monitoring & Observability (Stage A baseline)

| Signal | Source | Action |
|--------|--------|--------|
| Stack health | `docker compose ps` / healthchecks | alert if not healthy |
| API liveness | curl `/api/v1/public/summary` every 5 min (cron/systemd timer) | page/email on failure |
| Backend metrics | `/metrics` (prom) | Prometheus + Grafana (opt-in) |
| Postgres exporter | `:9187` (profile) | connection/space/WAL metrics |
| Redis exporter | `:9121` (profile) | memory, evictions, hit-rate |
| Logs | json-file (10m×3) per container | `docker compose logs`; ship to Loki/ELK in later phase |
| Disk | `df -h /opt/sita` | alert > 85% |

Prometheus scrape config already provisioned in repo (`infrastructure/monitoring/prometheus.yml`); enabling the monitoring compose services is opt-in for Stage A and required before Stage B handover.

---

## 17. Stage C — AWS, only as a Hosi-Managed Cloud Service

AWS is **not the default destination.** The system is cloud-based and managed from AWS **only if Hosi Technologies operates it from there**. If Hosi runs SITA as a managed cloud service (Hosi operates the platform on behalf of SITA), AWS is the right long-term home. If SITA prefers to host it themselves, the same containers are shipped to their environment (Stage B) and AWS is out of scope.

### 17.1 Entry criteria

1. Hosting/commercial agreement in place (Hosi operates on SITA's behalf).
2. Agreed SLA, support model, cost model (Hosi bears/marks up managed service).
3. AWS account + billing under Hosi's control; `af-south-1` (Cape Town) landing zone.

### 17.2 Target architecture

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

### 17.3 Lift-and-shift mapping (compose → AWS)

| Hosi Linux / shipped compose | AWS (managed by Hosi) | Change |
|------------------------------|-----------------------|--------|
| `postgres` container | RDS PostgreSQL Multi-AZ | Managed HA + backups |
| `redis` container | ElastiCache Redis | Managed, multi-AZ optional |
| `backend`/`frontend`/workers | ECS Fargate tasks/services | `deploy.replicas` semantics from `docker-compose.prod.yml` map 1:1 to ECS service count |
| nginx `:80` | ALB + ACM TLS | TLS handled by load balancer |
| `.env` on host | Secrets Manager / SSM | No secrets on disk |
| host `pg_dump` cron | RDS automated snapshots + PITR | No custom cron needed |
| `sita.conf` HTTPS-only | ALB TLS | CSP/HSTS preserved at LB layer |

The existing `docker-compose.prod.yml` (which already expresses replicas, healthchecks, resource limits, workers) is the **draft of the AWS compose** — run it through Compose→ECS conversion, or transcribe services into CDK/Terraform.

### 17.4 Why AWS (Stage C) only when Hosi operates it

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

### 17.5 AWS rollout milestones (if Stage C engaged)

| # | Milestone | Output |
|---|-----------|--------|
| C1 | Landing zone (account, org, billing) | `af-south-1` VPC (3 AZ) + subnets/NAT |
| C2 | Data plane | RDS Postgres Multi-AZ + ElastiCache; import Stage A data |
| C3 | App plane | ECR mirror of GHCR; Fargate services from prod compose; ALB + ACM cert |
| C4 | Config & secrets | Secrets Manager / SSM; parameter validation (`:?` semantics preserved) |
| C5 | Observability | CloudWatch dashboards/alarms; log groups |
| C6 | DR | RDS PITR test; S3 versioning; cross-region snapshot choice |
| C7 | Handover | runbook for Hosi Ops; cost/billing review |

---

## 18. Rollback Plan

### 18.1 Stage A

If the Hosi Linux deployment fails after cutover:

1. Point stakeholders back to the local dev environment (`http://localhost:3000`) for continuity.
2. Fix forward on the host (logs, env, nginx) — the compose image-driven model makes re-deploy fast:

```bash
cd /opt/sita/sita-platform/infrastructure
docker compose -f docker-compose.remote.yml --env-file .env pull && docker compose -f docker-compose.remote.yml --env-file .env up -d
```

3. If the host itself is unusable, rebuild on a fresh Hosi Linux VM from the same compose + `.env` (data loss limited to Postgres volume; restore from backup §15.2).
4. **Stage B (SITA) is never blocked by Stage A state** — the same GHCR images and compose are shipped to SITA's environment regardless.
5. **Stage C (AWS, if Hosi operates it)** restores from the same GHCR images + RDS import; independent of earlier stages.

Rollback for a Stage B (SITA) deployment is defined in the runbook shipped with the bundle: SITA reverts to their previous environment or to a known-good image tag.

### 18.2 Tag pinning for rollback

- Before any redeploy, record current image digests: `docker inspect --format '{{.Image}}'` the running containers.
- Keep the previous known-good tag available in GHCR (publisher keeps history); never `untag` signed-off images.
- If `latest` regresses, rollback = `docker compose … pull` of previous `:<sha>` and `up -d`.

---

## 19. Risk Register

| # | Risk | Likelihood | Impact | Mitigation / Contingency | Owner |
|---|------|-----------|--------|--------------------------|-------|
| R1 | VPN to `192.168.101.0/24` not provisioned in time | Med | High (blocks Phase 2) | Use `hosiai` jump today; escalate IT/Arezoo; schedule on-site session | Hosi IT |
| R2 | Port 80 conflict on `unified` | Low | Med | Pre-check `ss -ltnp`; shift port 8080 temporarily | Hosi Dev |
| R3 | GHCR pull failure on host (egress/FW) | Low | Med | Test `curl -I https://ghcr.io`; use mirrored registry/offline tar | Hosi Dev |
| R4 | Seed SQL error on first boot | Low | Med | Logs: `docker compose logs postgres`; fix + boot with fresh volume (with backup) | Hosi Dev |
| R5 | Secrets leak (`.env`, bootstrap pw) | Low | High | 600 perms; not committed; rotate post first login; capture pw at deploy | Hosi Dev |
| R6 | Host disk fills with backups | Med | Med | Retention policy; off-host copy; `df` alert > 85% | Hosi Ops |
| R7 | Image `latest` drift after future pushes | Med | Med | Pin `<sha>` at sign-off; keep previous tag | Hosi Dev |
| R8 | Windows eval license expiry presses for another path | — | — | Already excluded; Linux verdict locked | — |
| R9 | SITA prefers a different environment than planned | Med | Low | Stage B is environment-agnostic (container deliverable) | Hosi + SITA |
| R10 | No off-host backup during first weeks | Med | High | Stand up rsync/S3 copy D0+1; treat host as single point until then | Hosi Ops |

Acceptance: residual risk after mitigations reviewed at D0 sign-off; R1 is the only open blocker.

---

## 20. Detailed Timeline

| Day | Activity | Owner | Status |
|-----|----------|-------|--------|
| D−3 | VPN access request to IT for `192.168.101.0/24` (per individual) | Hosi IT (Arezoo) | ✅ requested |
| D−2 | Confirm SSH + host inventory on `unified`; GHCR pullability | Hosi Dev | ✅ done (19 Aug) |
| D−1 | **Deploy stack from GHCR images; verify seeds + health** (Phase 2) | Hosi Dev | 🔄 executing (blocked on R1) |
| D0 | Smoke test UI/API (V1–V9); stakeholder sign-off | Hosi Dev + stakeholder | ⬜ next |
| D+1 | Nightly backup cron verified; off-host copy stood up (R10) | Hosi Ops | ⬜ |
| D+1…D+7 | Hypercare; monitoring baseline (Prometheus optional); UFW/SSH-key hardening | Hosi Dev | ⬜ |
| D+8…D+30 | Assemble shipping bundle + runbook; Stage B rehearsal on scratch host; agree SITA's environment | Hosi Dev + SITA | ⬜ |
| D+30+ | Deploy at SITA (Stage B) and acceptance (§5.4) — and only if Hosi operates the cloud: AWS kickoff (Stage C) | Hosi + SITA | ⬜ |

---

## 21. Open Decisions & Next Actions

| # | Item | Decision | Owner | Status |
|---|------|----------|-------|--------|
| 1 | Host (Stage A) | **`unified` — `192.168.101.20`, user `uni`, Ubuntu 26.04** | ✅ resolved | |
| 2 | LAN URL | `http://192.168.101.20` | ✅ resolved | |
| 3 | TLS on Stage A | Deferred (HTTP first) | ✅ resolved | |
| 4 | Access | VPN-gated LAN; jump via `hosiai` tailnet | ✅ resolved | |
| 5 | Data | Fresh seed + HR system | ✅ resolved | |
| 6 | **VPN access to 192.168.101.0/24** | ⬜ provisioned per individual | Hosi IT | open (blocks D−1) |
| 7 | **SITA's preferred environment** (on-prem / their cloud / third-party) | ⬜ to be agreed | Hosi + SITA | open |
| 8 | **Delivery model** (Hosi-supported install vs SITA-run vs Hosi-managed cloud) | ⬜ to be agreed | Hosi + SITA | open |
| 9 | Air-gapped delivery (media) vs online pull | ⬜ depends on SITA network | SITA | open |
| 10 | AWS only if Hosi operates it — landing zone (account, region `af-south-1`, VPC), IaC tool | ⬜ conditional on Stage C | Hosi | open |
| 11 | Bootstrap admin email (currently `admin@sita.local`) | ⬜ set to real mailbox at sign-off | Hosi Dev | open |
| 12 | Sign-off owner + cutover date | ⬜ | stakeholder | open |

---

## 22. Summary

| | Local dev (today) | Hosi Fourways Linux (Stage A) | SITA's environment (Stage B — the deliverable) | AWS managed by Hosi (Stage C — conditional) |
|--|-------------------|------------------------------|------------------------------------------------|---------------------------------------------|
| Host | Windows dev box | Existing Hosi Linux server | SITA's chosen environment | AWS managed (RDS/ECS/ALB) |
| Images | Build in Docker Desktop | **Pull GHCR images** | Same GHCR images (or offline tar) | Same GHCR → ECR |
| Cost | n/a | Free (existing asset) | SITA bears hosting cost | Hosi bears/marks up managed service |
| Licensing | — | None (Ubuntu LTS) | Per SITA's host | None (AWS-managed) |
| Accessibility | Local only | VPN-gated LAN | SITA's network | Public HTTPS |
| HA/DR | None | Host-level backups | Per SITA's environment + runbook | Multi-AZ, PITR, autoscale |
| Fit | Dev | **Now** — cost-effective, accessible | **The customer deliverable** — shipped to SITA | **Only if Hosi runs the cloud** — scale/HA/audit |

**Recommendation:** deploy **now** to the Hosi Fourways Linux server from prebuilt GHCR images (Stage A) as the working reference. **Execution is underway** — host `unified` (`192.168.101.20`, user `uni`) is inventoried and the `deploy-remote-linux.sh` one-shot script is ready to run. The only open blocker is **VPN access to `192.168.101.0/24`** (§21#6); until then, the deploy can proceed via the `hosiai` jump node with interactive credentials. The real deliverable is **portable Docker containers** shipped to **SITA's preferred environment** (Stage B) with compose files, images, `.env.template`, and a runbook. **AWS (Stage C) is included only if Hosi Technologies operates the system as a cloud-based managed service**; otherwise it is out of scope and SITA's own environment is the deployment target. The Windows/AnyDesk option is excluded because its evaluation license expires in < 30 days, forcing a high-risk mid-flight re-license for no architectural benefit.

---

## 23. Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 19 Aug 2026 | Initial deployment strategy (Hosi Fourways → AWS) |
| 1.1 | 19 Aug 2026 | Reframed — ship to SITA (Stage B); AWS only if Hosi-managed |
| 1.2 | 19 Aug 2026 | Finalized with confirmed host, execution status, decisions |
| 2.0 | 19 Aug 2026 | **Enriched:** RACI, prerequisites, per-step expected outputs & validation checkpoints, troubleshooting runbook, secrets mgmt, day-2 runbook, acceptance tests, backup/DR procedures, risk register, AWS milestone plan |