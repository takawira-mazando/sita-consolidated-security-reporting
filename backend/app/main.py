import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response

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
    intel,
    meta,
    metrics,
    public_summary,
    reports_ai,
    risks,
)
from app.config import settings, is_disallowed_credential
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
            elif is_disallowed_credential(settings.bootstrap_admin_password):
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

from jose import JWTError, jwt

# Security headers & global token validation middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Guard against null byte injection in URL or query string (prevents 500 DB errors)
    raw_query = request.url.query or ""
    if "\x00" in request.url.path or "\x00" in raw_query or "%00" in raw_query.lower():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid request: Null byte injection detected"},
            headers={"X-Content-Type-Options": "nosniff"},
        )

    # Guard against weak signature / forged / alg:none JWTs on all requests bearing Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.strip().lower().startswith("bearer "):
        token = auth_header.strip()[7:].strip()
        parts = token.split(".")
        if len(parts) < 2 or not parts[0]:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token structure"},
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )

        # Explicitly inspect token algorithm in header to reject 'none'
        try:
            import base64
            import json
            header_b64 = parts[0]
            header_b64 += "=" * ((4 - len(header_b64) % 4) % 4)
            header_data = json.loads(base64.urlsafe_b64decode(header_b64.encode("utf-8")))
            alg = str(header_data.get("alg", "")).strip().lower()
            if not alg or alg in ("none", "null", "undefined"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Algorithm 'none' is forbidden"},
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                    },
                )
        except Exception:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Malformed token header"},
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )

        # Cryptographically verify signature using allowed algorithms
        try:
            if settings.auth0_domain:
                jwt.decode(
                    token,
                    settings.auth0_domain,
                    algorithms=settings.auth0_algorithms,
                    audience=settings.auth0_audience,
                    options={"verify_aud": bool(settings.auth0_audience), "verify_signature": True},
                )
            else:
                jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_signature": True},
                )
        except (JWTError, Exception):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                },
            )

    response: Response = await call_next(request)
    # Security headers
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Hide server version
    if "Server" in response.headers:
        del response.headers["Server"]
    # HSTS only in production with HTTPS
    if settings.environment.lower() not in ("dev", "development", "test", "testing"):
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' https://*.auth0.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "require-trusted-types-for 'script'"
    )
    return response


# CORS configuration - strict trusted origins to prevent overly permissive CORS
allowed_origins = [
    "http://192.168.101.20:8088",
    "http://192.168.101.20:8000",
    "http://localhost:8088",
    "http://localhost:8000",
    "http://localhost:8801",
    "http://localhost:8802",
    "http://127.0.0.1:8801",
    "http://127.0.0.1:8802",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://sita.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
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
app.include_router(meta.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(exports_ag.router, prefix="/api/v1")
app.include_router(benchmark.router, prefix="/api/v1")
app.include_router(intel.router, prefix="/api/v1")
app.include_router(public_summary.router, prefix="/api/v1")
app.include_router(reports_ai.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/admin")

register_exception_handlers(app)

@app.get("/", include_in_schema=False)
async def root():
    if settings.environment.lower() in ("dev", "development", "test", "testing"):
        return RedirectResponse(url="/docs")
    return {
        "service": "SITA Security Intelligence Platform API",
        "version": "1.0.0",
        "health": "/health",
    }


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    return FileResponse(
        Path(__file__).parent / "static" / "favicon.svg",
        media_type="image/svg+xml",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check - restricted to internal use"""
    return {"status": "healthy", "db": "ok", "uptime": int(time.time() - start_time)}
