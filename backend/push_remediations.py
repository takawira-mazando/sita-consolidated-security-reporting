"""
Push VAPT remediations to remote server and verify security headers.
Pulls latest origin/main, rebuilds containers, verifies live headers.
"""
import paramiko
import time
import sys

REMOTE_HOST = "192.168.101.20"
REMOTE_USER = "uni"
REMOTE_PASS = "H051@pivot"
DEPLOY_DIR = "/opt/sita/sita-platform"
STACK_FILE = "/opt/sita/sita-platform/infrastructure/docker-compose.remote.yml"

print(f"==> Connecting to {REMOTE_USER}@{REMOTE_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=20)
print("    Connected.\n")


def run(cmd, timeout=300, check_stderr=True):
    full_cmd = f"echo '{REMOTE_PASS}' | sudo -S bash -c \"{cmd}\""
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out.strip())
    if err and check_stderr:
        for line in err.splitlines():
            if "Password:" in line or not line.strip():
                continue
            print(f"  [stderr] {line}")
    return out, err


# ─── Step 1: Pull latest commit ────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Pull latest code (commit 948d02d — VAPT remediations)")
print("=" * 60)
run(f"cd {DEPLOY_DIR} && git fetch origin main && git reset --hard origin/main")
out, _ = run(f"cd {DEPLOY_DIR} && git log -1 --oneline")
print(f"  Remote HEAD: {out.strip()}")


# ─── Step 2: Pull new images ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Pull latest Docker images from GHCR")
print("=" * 60)
run(f"docker compose -f {STACK_FILE} pull", timeout=300)


# ─── Step 3: Restart containers ────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: Restart containers with force-recreate")
print("=" * 60)
run(f"docker compose -f {STACK_FILE} up -d --force-recreate", timeout=300)


# ─── Step 4: Wait for backend health ──────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Waiting for backend health...")
print("=" * 60)
time.sleep(10)
health_ok = False
for attempt in range(1, 20):
    out, _ = run("curl -s http://localhost:8000/health || true", check_stderr=False)
    if "ok" in out or "status" in out:
        print(f"  [OK] Backend healthy on attempt {attempt}: {out.strip()}")
        health_ok = True
        break
    print(f"  Attempt {attempt}/20 — waiting...")
    time.sleep(4)

if not health_ok:
    print("  [ERROR] Backend not healthy — dumping logs:")
    run(f"docker compose -f {STACK_FILE} logs --tail 50 backend")
    ssh.close()
    sys.exit(1)


# ─── Step 5: Verify security headers on Nginx (:8088) ─────────────────────
print("\n" + "=" * 60)
print("STEP 5: Verifying VAPT remediation headers on port 8088 (Nginx)")
print("=" * 60)
out, _ = run("curl -s -I http://localhost:8088/ || true", check_stderr=False)
print(out)

required_headers = [
    "X-Frame-Options",
    "X-Content-Type-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Permissions-Policy",
]
missing = [h for h in required_headers if h.lower() not in out.lower()]
if missing:
    print(f"  [WARN] Missing headers: {missing}")
else:
    print("  [PASS] All required security headers present on :8088.")

# Confirm server token suppression
if "nginx/1.25" in out.lower() or "uvicorn" in out.lower():
    print("  [WARN] Server version token still visible in headers!")
else:
    print("  [PASS] Server version token suppressed.")


# ─── Step 6: Verify security headers on backend (:8000) ───────────────────
print("\n" + "=" * 60)
print("STEP 6: Verifying security headers on port 8000 (Backend API)")
print("=" * 60)
out_be, _ = run("curl -s -I http://localhost:8000/health || true", check_stderr=False)
print(out_be)

missing_be = [h for h in required_headers if h.lower() not in out_be.lower()]
if missing_be:
    print(f"  [WARN] Backend missing headers: {missing_be}")
else:
    print("  [PASS] All security headers present on :8000.")

if "uvicorn" in out_be.lower():
    print("  [WARN] Uvicorn server token still exposed!")
else:
    print("  [PASS] Uvicorn server token suppressed (--no-server-header).")


# ─── Step 7: Container status ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7: Final container status")
print("=" * 60)
run(f"docker compose -f {STACK_FILE} ps")

ssh.close()
print("\n==> Remote remediation deployment and verification COMPLETE.")
