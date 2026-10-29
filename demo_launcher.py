"""SITA Security Intelligence Platform - End-to-End Demo Launcher.

One-command setup and orchestrator for executive PoC demonstrations to SITA.
Starts backend (FastAPI/Uvicorn), frontend (Vite), verifies PostgreSQL database
connectivity and seed telemetry, and launches the browser to http://localhost:3000.

Usage:
    python demo_launcher.py
    python demo_launcher.py --reseed
    python demo_launcher.py --no-browser
"""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 on Windows consoles to support ANSI and Unicode emojis
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Paths
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   🇿🇦  SITA CONSOLIDATED CYBER SECURITY INTELLIGENCE PLATFORM            ║
║       End-to-End Proof-of-Concept & Executive Demonstration Orchestrator  ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


def check_database():
    """Verify database connection and table telemetry counts."""
    print(f"{YELLOW}🔍 Checking PostgreSQL Database Connection...{RESET}")
    # Ensure backend is on sys.path
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    try:
        from app.config import settings
        from app.db import SessionFactory
        from sqlalchemy import text

        async def _check():
            async with SessionFactory() as session:
                res = await session.execute(text("SELECT count(*) FROM warehouse.findings"))
                count = res.scalar()
                return count

        count = asyncio.run(_check())
        print(f"{GREEN}✓ PostgreSQL Connected successfully.{RESET} (warehouse.findings: {count:,} records)")
        return True, count
    except Exception as e:
        print(f"{RED}✗ Database check failed: {e}{RESET}")
        return False, 0


def seed_data():
    """Seed synthetic telemetry data into database."""
    print(f"\n{YELLOW}🌱 Seeding simulated OEM telemetry (AppScan, Imperva DAM/WAF, APISec)...{RESET}")
    cmd = [sys.executable, "-m", "app.entrypoints.seed_simulated", "--sources", "all", "--count", "200", "--days", "14"]
    res = subprocess.run(cmd, cwd=str(BACKEND_DIR))
    if res.returncode == 0:
        print(f"{GREEN}✓ Database seeded successfully.{RESET}")
    else:
        print(f"{RED}✗ Seeding failed with exit code {res.returncode}.{RESET}")


def is_url_alive(url: str) -> bool:
    """Quick check if a URL is already responsive."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Sita-Demo-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status in (200, 304, 302)
    except Exception:
        return False


def wait_for_url(url: str, timeout: int = 45, service_name: str = "Service") -> bool:
    """Poll URL until it responds with HTTP 200 or timeout."""
    if is_url_alive(url):
        print(f"⏳ {service_name} at {url} {GREEN}[READY]{RESET}")
        return True

    start = time.time()
    sys.stdout.write(f"⏳ Waiting for {service_name} at {url} ")
    sys.stdout.flush()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Sita-Demo-Launcher"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status in (200, 304, 302):
                    sys.stdout.write(f" {GREEN}[READY]{RESET}\n")
                    sys.stdout.flush()
                    return True
        except Exception:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
    sys.stdout.write(f" {RED}[TIMEOUT]{RESET}\n")
    return False


def main():
    parser = argparse.ArgumentParser(description="SITA Platform End-to-End Demo Launcher")
    parser.add_argument("--reseed", action="store_true", help="Force re-seeding of synthetic OEM data")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    args = parser.parse_args()

    print_banner()

    # Step 1: Database validation
    db_ok, findings_count = check_database()
    if not db_ok:
        print(f"\n{RED}{BOLD}ERROR:{RESET} Cannot connect to PostgreSQL on port 5432.")
        print(f"Please ensure PostgreSQL service is running. Database URL in .env: {ROOT_DIR / '.env'}")
        sys.exit(1)

    if findings_count == 0 or args.reseed:
        seed_data()

    processes = []

    def cleanup(sig=None, frame=None):
        print(f"\n\n{YELLOW}🛑 Shutting down demo environment...{RESET}")
        for p in processes:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
            except Exception:
                pass
        print(f"{GREEN}✓ Demo services terminated cleanly. Goodbye!{RESET}\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, cleanup)

    try:
        # Step 2: Start Backend (if not already running)
        backend_alive = is_url_alive(f"{BACKEND_URL}/health")
        if backend_alive:
            print(f"{GREEN}✓ Backend API is already running on {BACKEND_URL}{RESET}")
        else:
            print(f"\n{CYAN}🚀 Launching Backend API (FastAPI / Uvicorn on :8000)...{RESET}")
            backend_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
            backend_proc = subprocess.Popen(
                backend_cmd,
                cwd=str(BACKEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            processes.append(backend_proc)

        # Step 3: Start Frontend (if not already running)
        frontend_alive = is_url_alive(FRONTEND_URL)
        if frontend_alive:
            print(f"{GREEN}✓ Frontend Web App is already running on {FRONTEND_URL}{RESET}")
        else:
            print(f"{CYAN}🎨 Launching Frontend Web App (Vite React on :3000)...{RESET}")
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            frontend_proc = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            processes.append(frontend_proc)

        # Step 4: Health Check verification
        backend_ready = wait_for_url(f"{BACKEND_URL}/health", timeout=30, service_name="Backend API")
        frontend_ready = wait_for_url(FRONTEND_URL, timeout=45, service_name="Frontend UI")

        if not backend_ready or not frontend_ready:
            print(f"\n{RED}{BOLD}Warning:{RESET} One or more services did not respond in time.")
            print(f"Backend status: {'OK' if backend_ready else 'FAIL'}, Frontend status: {'OK' if frontend_ready else 'FAIL'}")

        # Step 5: Presentation & Pitch Guide
        guide_text = f"""
{GREEN}{BOLD}═══════════════════════════════════════════════════════════════════════════════
  🎉 DEMO STACK IS LIVE AND READY FOR SITA EXECUTIVE PRESENTATION!
═══════════════════════════════════════════════════════════════════════════════{RESET}

  🔗 {BOLD}Web Application:{RESET}        {CYAN}{FRONTEND_URL}{RESET}
  🔗 {BOLD}Backend API Docs:{RESET}       {CYAN}{BACKEND_URL}/docs{RESET}
  📑 {BOLD}Executive Slide Deck:{RESET}   {CYAN}{FRONTEND_URL}/presentation.html{RESET}
  🏛️ {BOLD}Architecture Viewer:{RESET}   {CYAN}{FRONTEND_URL}/architecture.html{RESET}

{YELLOW}{BOLD}📋 7-ACT DEMO SCRIPT WALKTHROUGH:{RESET}
  {BOLD}Act 1: Landing & Public Summary{RESET}  → Unauthenticated landing page & granular 14-role RBAC matrix
  {BOLD}Act 2: Multi-Tier Tenancy{RESET}        → Impersonate Executive, DHA SOC Lead, DDG Branch
  {BOLD}Act 3: 6 Security Dashboards{RESET}     → Executive (Fused Risk), SOC, AppSec (OWASP), DbSec (DAM)
  {BOLD}Act 4: AI Intelligence Studio{RESET}    → 8 Capabilities (Attribution, POPIA, VAPT, Two-Gate)
  {BOLD}Act 5: Delegated User Provisioning{RESET}→ 4-tier admin cascade with SAP HCM & PERSAL verification
  {BOLD}Act 6: Export & Reporting{RESET}         → Auditor-General signed attestations (.docx / .xlsx / .csv)
  {BOLD}Act 7: Security & Arch Deep-Dive{RESET}  → Microservice isolation, JWT hardening, PII encryption

{BOLD}💡 Tip:{RESET} An interactive {BOLD}SITA Demo Co-Pilot HUD{RESET} is embedded at the bottom-right
of the screen to guide your demonstration Act-by-Act with one-click persona transitions!

{DIM}Press Ctrl+C at any time to shut down all demo services.{RESET}
"""
        print(guide_text)

        # Step 6: Launch Browser
        if not args.no_browser:
            print(f"{CYAN}🌐 Launching default browser to {FRONTEND_URL}...{RESET}")
            webbrowser.open(FRONTEND_URL)

        # Keep alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"\n{RED}Error running demo: {e}{RESET}")
        cleanup()


if __name__ == "__main__":
    main()
