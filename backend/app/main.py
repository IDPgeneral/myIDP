from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import CorrelationIdMiddleware, configure_logging
from app.core.rate_limit import RateLimitMiddleware
from app.routes import catalog, health, products, provider_accounts, providers, sync, users
from app.sync.scheduler import build_scheduler

settings = get_settings()
configure_logging()
scheduler = None


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
            "render_credentials": {
                "milu": bool(os.getenv("RENDER_API_KEY_MILU")),
                "colorglass": bool(os.getenv("RENDER_API_KEY_COLORGLASS")),
                "superexcel": bool(os.getenv("RENDER_API_KEY_SUPEREXCEL")),
            },
        },
    }


@app.exception_handler(ValueError)
def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)[:500]})
