from __future__ import annotations

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import HealthCheck, ProviderAccount
from app.db.session import SessionLocal
from app.services.health import HealthCheckService
from app.services.sync import SyncCoordinator

logger = logging.getLogger(__name__)


def _sync_provider(provider: str, settings: Settings) -> None:
    with SessionLocal() as db:
        accounts = db.scalars(select(ProviderAccount).where(ProviderAccount.provider == provider)).all()
        for account in accounts:
            try:
                SyncCoordinator(db, settings).sync_account(account)
            except Exception:
                logger.exception("Falha na sincronização periódica do provedor %s", provider)


def _sync_health() -> None:
    with SessionLocal() as db:
        checks = db.scalars(select(HealthCheck).where(HealthCheck.active.is_(True))).all()
        service = HealthCheckService(db)
        for check in checks:
            try:
                service.run(check)
            except Exception:
                logger.exception("Falha no health check periódico %s", check.id)


def build_scheduler(settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_sync_health, "interval", minutes=settings.sync_health_interval_minutes, id="health", max_instances=1, coalesce=True)
    scheduler.add_job(_sync_provider, "interval", minutes=settings.sync_github_interval_minutes, id="github", args=["github", settings], max_instances=1, coalesce=True)
    scheduler.add_job(
        _sync_provider,
        "interval",
        minutes=settings.sync_render_interval_minutes,
        id="render",
        args=["render", settings],
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(UTC),
    )
    scheduler.add_job(_sync_provider, "interval", minutes=settings.sync_supabase_interval_minutes, id="supabase", args=["supabase", settings], max_instances=1, coalesce=True)
    return scheduler
