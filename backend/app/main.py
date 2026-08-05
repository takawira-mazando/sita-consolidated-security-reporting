import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routers import admin, alerts, compliance, dashboard, findings, risks
from app.monitoring.metrics import setup_metrics

start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_metrics()
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

app.include_router(risks.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/admin")

register_exception_handlers(app)

@app.get("/health")
async def health():
    return {"status": "healthy", "db": "ok", "uptime": int(time.time() - start_time)}
