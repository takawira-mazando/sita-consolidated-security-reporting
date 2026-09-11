import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

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
    public_summary,
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
            elif settings.bootstrap_admin_password == "admin123":  # nosec B105
                logger.warning(
                    "Demo users disabled; set a strong BOOTSTRAP_ADMIN_PASSWORD for %s",
                    settings.bootstrap_admin_email,
                )
    except Exception:
        logger.exception("Failed to initialize identity users")
    yield

# Disable Swagger/OpenAPI in production
if settings.environment.lower() in ("dev", "development", "test", "testing"):
    app = FastAPI(
        title="SITA Security Intelligence Platform API",
        version="1.0.0",
        lifespan=lifespan,
    )
else:
    app = FastAPI(
        title="SITA Security Intelligence Platform API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    # Security headers
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Hide server version
    if "Server" in response.headers:
        del response.headers["Server"]
    # HSTS only in production with HTTPS
    if settings.environment.lower() not in ("dev", "development", "test", "testing"):
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://*.auth0.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


# CORS configuration - restrict to trusted origins in production
if settings.environment.lower() in ("dev", "development", "test", "testing"):
    allowed_origins = ["*"]
    allow_credentials = True
else:
    # In production, only allow the frontend origin
    allowed_origins = ["http://192.168.101.20:8088", "https://sita.example.com"]
    allow_credentials = False  # Don't allow credentials with wildcard origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    max_age=600,
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
app.include_router(public_summary.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/admin")

register_exception_handlers(app)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check - restricted to internal use"""
    return {"status": "healthy", "db": "ok", "uptime": int(time.time() - start_time)}
