from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import CorrelationIdMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import SessionLocal
from app.routes import catalog, health, products, provider_accounts, providers, sync, users
from app.sync.scheduler import build_scheduler

settings = get_settings()
configure_logging()
scheduler = None


def _database_mode() -> str:
    database_url = settings.database_url.lower()
    if "localhost" in database_url:
        return "default_local"
    if ".pooler.supabase.com" in database_url and ":5432" in database_url:
        return "session_pooler"
    if ".pooler.supabase.com" in database_url and ":6543" in database_url:
        return "transaction_pooler"
    if ".supabase.co" in database_url:
        return "direct"
    return "custom"


def _database_error_category(exc: SQLAlchemyError) -> str:
    message = str(getattr(exc, "orig", exc)).lower()
    if "password authentication failed" in message or "authentication failed" in message:
        return "invalid_credentials"
    if "name or service not known" in message or "could not translate host name" in message:
        return "dns_error"
    if "network is unreachable" in message:
        return "network_unreachable"
    if "connection refused" in message:
        return "connection_refused"
    if "timeout" in message:
        return "connection_timeout"
    return "connection_failed"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global scheduler
    if settings.sync_enabled:
        scheduler = build_scheduler(settings)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.auth_disabled else settings.cors_origin_list,
    allow_credentials=not settings.auth_disabled,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

for router in (products.router, provider_accounts.router, sync.router, providers.router, health.router, catalog.router, users.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {
        "status": "ok",
        "service": "idp-backend",
        "revision": (os.getenv("RENDER_GIT_COMMIT") or "")[:12] or None,
        "configuration": {
            "auth_configured": bool(settings.supabase_url or settings.supabase_jwt_secret),
            "sync_enabled": settings.sync_enabled,
            "scheduler_running": bool(scheduler and scheduler.running),
            "render_credentials": {
                "milu": bool(os.getenv("RENDER_API_KEY_MILU")),
                "colorglass": bool(os.getenv("RENDER_API_KEY_COLORGLASS")),
                "superexcel": bool(os.getenv("RENDER_API_KEY_SUPEREXCEL")),
            },
        },
    }


@app.get("/readyz", include_in_schema=False)
def readyz():
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": False,
                "database_mode": _database_mode(),
                "error_type": type(exc).__name__,
                "error_category": _database_error_category(exc),
            },
        )
    return {"status": "ready", "database": True, "database_mode": _database_mode()}


@app.exception_handler(SQLAlchemyError)
def database_error_handler(_, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Banco de dados indisponível.", "error_type": type(exc).__name__},
    )


@app.exception_handler(ValueError)
def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)[:500]})
