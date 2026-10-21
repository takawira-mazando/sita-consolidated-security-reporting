"""Automated Remote Deployment Script for SITA Platform to 192.168.101.20 via SSH/VPN."""
import sys
import time
import paramiko

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REMOTE_HOST = os.environ.get("REMOTE_HOST", "127.0.0.1")
REMOTE_USER = os.environ.get("REMOTE_USER", "sita")
REMOTE_PASS = os.environ.get("REMOTE_PASS", "")
STACK_DIR = "/opt/sita/sita-platform/infrastructure"
REPO_DIR = "/opt/sita/sita-platform"
COMPOSE_FILE = f"{STACK_DIR}/docker-compose.remote.yml"


def connect_ssh(retries=3, delay=5):
    for i in range(1, retries + 1):
        print(f"==> [Attempt {i}/{retries}] Connecting to {REMOTE_USER}@{REMOTE_HOST}:22...")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=20)
            print("==> SSH connection established.")
            return client
        except Exception as e:
            print(f"==> Connection failed: {e}")
            if i < retries:
                time.sleep(delay)
    raise RuntimeError("Failed to connect to remote host after retries.")


def run_sudo_cmd(client, cmd, timeout=300):
    print(f"\n[REMOTE EXEC] {cmd}")
    stdin, stdout, stderr = client.exec_command(f"sudo -S {cmd}", timeout=timeout)
    stdin.write(f"{REMOTE_PASS}\n")
    stdin.flush()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    clean_err = "\n".join([line for line in err.splitlines() if "[sudo]" not in line and "password for" not in line])
    if out.strip():
        print(out.strip())
    if clean_err.strip():
        print(f"[STDERR] {clean_err.strip()}")
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, out, clean_err


def main():
    print("=======================================================")
    print("   SITA PLATFORM REMOTE DEPLOYMENT TO 192.168.101.20   ")
    print("=======================================================")

    client = connect_ssh()

    try:
        # Step 1: Update repository to latest origin/main
        print("\n==> Step 1: Updating repository from origin/main...")
        run_sudo_cmd(client, f"git -C {REPO_DIR} fetch origin main")
        run_sudo_cmd(client, f"git -C {REPO_DIR} reset --hard origin/main")
        _, out, _ = run_sudo_cmd(client, f"git -C {REPO_DIR} log -1 --oneline")
        print(f"==> Deployed Commit: {out.strip()}")

        # Step 2: Build fresh application images from updated source
        print("\n==> Step 2: Building backend & frontend containers...")
        run_sudo_cmd(client, f"docker compose -f {COMPOSE_FILE} build backend frontend")

        # Step 3: Pull Nginx 1.27.4-alpine and database images
        print("\n==> Step 3: Pulling infrastructure images (Nginx 1.27.4-alpine, etc.)...")
        run_sudo_cmd(client, f"docker compose -f {COMPOSE_FILE} pull nginx postgres redis")

        # Step 4: Up the stack
        print("\n==> Step 4: Starting Docker Compose stack...")
        run_sudo_cmd(client, f"docker compose -f {COMPOSE_FILE} up -d --remove-orphans")

        # Step 5: Verify container statuses
        print("\n==> Step 5: Container status:")
        run_sudo_cmd(client, f"docker compose -f {COMPOSE_FILE} ps")

        # Step 6: Wait for health checks
        print("\n==> Step 6: Polling backend health endpoint...")
        ok = False
        for attempt in range(1, 25):
            time.sleep(3)
            exit_code, out, _ = run_sudo_cmd(client, "curl -sf http://localhost:8000/health")
            if exit_code == 0 and "ok" in out.lower():
                print(f"==> Health check passed on attempt {attempt}: {out.strip()}")
                ok = True
                break
            print(f"    Waiting for backend... ({attempt}/24)")

        if not ok:
            print("\n[ERROR] Backend health check did not pass in time. Showing logs:")
            run_sudo_cmd(client, f"docker compose -f {COMPOSE_FILE} logs --tail 40 backend")
            sys.exit(1)

        # Step 7: Verify Nginx frontend response & headers
        print("\n==> Step 7: Verifying Nginx frontend response & security headers...")
        _, headers_out, _ = run_sudo_cmd(client, "curl -sI http://localhost:8088/")
        print("Frontend Response Headers:")
        print(headers_out.strip())

        print("\n=======================================================")
        print("       DEPLOYMENT COMPLETED SUCCESSFULLY!              ")
        print(f"  Frontend: http://{REMOTE_HOST}:8088/                ")
        print(f"  Backend:  http://{REMOTE_HOST}:8000/api/v1          ")
        print(f"  Health:   http://{REMOTE_HOST}:8000/health          ")
        print(f"  Docs:     http://{REMOTE_HOST}:8000/docs            ")
        print("=======================================================")

    finally:
        client.close()
        print("\n==> SSH connection closed.")


if __name__ == "__main__":
    main()
