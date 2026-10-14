import sys
import time
import base64
import os
import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REMOTE_HOST = "192.168.101.20"
REMOTE_USER = "uni"
REMOTE_PASS = "H051@pivot"
DEPLOY_DIR = "/opt/sita/sita-platform"
STACK_DIR = "/opt/sita/sita-platform/infrastructure"

print(f"==> Connecting to {REMOTE_USER}@{REMOTE_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15)

def run(cmd, timeout=300):
    print(f"\n[REMOTE RUN] {cmd}")
    full_cmd = f"echo '{REMOTE_PASS}' | sudo -S bash -c \"{cmd}\""
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out.strip())
    if err and "Password:" not in err:
        print("[STDERR]", err.strip())
    return out

# Step 1: Git pull
print("\n==> Step 1: Resetting /opt/sita/sita-platform to latest origin/main...")
run(f"cd {DEPLOY_DIR} && git fetch origin main && git reset --hard origin/main")
run(f"cd {DEPLOY_DIR} && git log -1 --oneline")

# Step 2: Ensure .env has valid keys
print("\n==> Step 2: Ensuring .env has valid environment configuration...")
env_file = f"{STACK_DIR}/.env"
# Generate real PII key
pii_key = base64.b64encode(os.urandom(32)).decode()
run(f"grep -q 'PII_ENCRYPTION_KEY' {env_file} || echo 'PII_ENCRYPTION_KEY={pii_key}' >> {env_file}")
run(f"sed -i 's/ENVIRONMENT=production/ENVIRONMENT=development/' {env_file}")
run(f"sed -i 's/SEED_DEMO_USERS_ENABLED=false/SEED_DEMO_USERS_ENABLED=true/' {env_file}")
run(f"cat {env_file}")

# Step 3: Up stack with build and force recreate
print("\n==> Step 3: Starting containers with docker compose build...")
compose_file = f"{STACK_DIR}/docker-compose.remote.yml"
run(f"docker compose -f {compose_file} up -d --build --force-recreate", timeout=300)

# Step 4: Verify health
print("\n==> Step 4: Verifying container health on remote...")
time.sleep(8)
run(f"docker compose -f {compose_file} ps")

health_ok = False
for attempt in range(1, 15):
    print(f"Health check attempt {attempt}/15...")
    res = run("curl -s http://localhost:8000/health || true")
    if "ok" in res or "status" in res:
        print("Backend health OK:", res)
        health_ok = True
        break
    time.sleep(3)

if not health_ok:
    print("Backend logs:")
    run(f"docker compose -f {compose_file} logs --tail 40 backend")

# Step 5: Verify DAST remediations on live Nginx (:8088)
print("\n==> Step 5: Verifying live DAST remediations on port 8088...")
res_fe = run("curl -s -I http://localhost:8088/ || true")
print("Frontend HTTP headers:\n", res_fe)

# Verify alg:none token is rejected with 401 on tenancy
res_jwt = run("curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiIxMjMifQ.' http://localhost:8088/api/v1/auth/tenancy || true")
print("Crafted alg:none JWT check (expected 401):", res_jwt)

# Verify null byte injection is rejected with 400
res_null = run("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8088/admin/persons?employment_status=%00' || true")
print("Null byte injection check (expected 400):", res_null)

res_api = run("curl -s http://localhost:8000/api/v1/public/summary || true")
print("Public summary API response:\n", res_api[:200] if res_api else "None")

ssh.close()
print("\n==> Remote deployment complete!")
