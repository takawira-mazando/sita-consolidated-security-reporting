import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routers import (
    admin,
    alerts,
    auth,
    benchmark,
    compliance,
    dashboard,
    exports,
    exports_ag,
    findings,
    metrics,
    risks,
)
from app.config import settings
from app.db import SessionFactory
from app.monitoring.metrics import setup_metrics

logger = logging.getLogger(__name__)

start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_metrics()
    try:
        async with SessionFactory() as session:
            if await auth.bootstrap_superadmin(session):
                logger.warning(
                    "Bootstrapped superadmin %s — change its password after first login",
                    settings.bootstrap_admin_email,
                )
            if settings.seed_demo_users_enabled:
                created = await auth.seed_demo_users(session)
                if created:
                    logger.info("Seeded %d demo users", created)
            elif settings.bootstrap_admin_password == "admin123":
                logger.warning(
                    "Demo users disabled; set a strong BOOTSTRAP_ADMIN_PASSWORD for %s",
                    settings.bootstrap_admin_email,
                )
    except Exception:
        logger.exception("Failed to initialize identity users")
    yield

app = FastAPI(
    title="SITA Security Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(risks.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(exports_ag.router, prefix="/api/v1")
app.include_router(benchmark.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/admin")

register_exception_handlers(app)

@app.get("/health")
async def health():
    return {"status": "healthy", "db": "ok", "uptime": int(time.time() - start_time)}
