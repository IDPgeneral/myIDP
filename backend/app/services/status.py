from __future__ import annotations

import os

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import HealthCheck, HealthCheckResult, Product, ProductResource, ProviderAccount, ResourceSnapshot
from app.schemas.common import HealthResultOut, ProductSummary

PROVIDER_BAD = {"error", "authentication_error", "permission_error", "provider_unavailable"}


def _latest_snapshot(db: Session, resource_ids: list, snapshot_type: str) -> ResourceSnapshot | None:
    if not resource_ids:
        return None
    return db.scalar(
        select(ResourceSnapshot)
        .where(ResourceSnapshot.resource_id.in_(resource_ids), ResourceSnapshot.snapshot_type == snapshot_type)
        .order_by(desc(ResourceSnapshot.captured_at))
        .limit(1)
    )


def latest_health_results(db: Session, product_id: str) -> list[HealthResultOut]:
    checks = db.scalars(select(HealthCheck).where(HealthCheck.product_id == product_id, HealthCheck.active.is_(True))).all()
    output: list[HealthResultOut] = []
    for check in checks:
        result = db.scalar(
            select(HealthCheckResult)
            .where(HealthCheckResult.health_check_id == check.id)
            .order_by(desc(HealthCheckResult.checked_at))
            .limit(1)
        )
        output.append(
            HealthResultOut(
                health_check_id=str(check.id),
                name=check.name,
                status=result.status if result else "unknown",
                http_status=result.http_status if result else None,
                response_time_ms=result.response_time_ms if result else None,
                message=result.message if result else "Ainda não verificado.",
                checked_at=result.checked_at if result else None,
            )
        )
    return output


def product_summary(db: Session, product: Product) -> ProductSummary:
    accounts = db.scalars(select(ProviderAccount).where(ProviderAccount.product_id == product.id)).all()
    account_map = {account.provider: account for account in accounts}
    resources = db.scalars(select(ProductResource).where(ProductResource.product_id == product.id, ProductResource.active.is_(True))).all()
    by_type: dict[str, list] = {}
    for resource in resources:
        by_type.setdefault(resource.resource_type, []).append(resource.id)

    github = _latest_snapshot(db, by_type.get("repository", []), "github_repository")
    render = _latest_snapshot(db, by_type.get("render_service", []), "render_service")
    health_results = latest_health_results(db, str(product.id))
    worst_health = next((item for item in health_results if item.status == "down"), None) or next(
        (item for item in health_results if item.status == "degraded"), None
    ) or (health_results[0] if health_results else None)

    provider_status = {
        name: account_map[name].connection_status if name in account_map else "not_configured"
        for name in ("github", "render", "supabase")
    }
    alert_count = sum(1 for value in provider_status.values() if value not in {"connected", "healthy"})
    alert_count += sum(1 for item in health_results if item.status in {"down", "degraded", "unknown"})
    if any(item.status == "down" for item in health_results):
        overall = "down"
    elif any(value in PROVIDER_BAD for value in provider_status.values()):
        overall = "degraded"
    elif any(item.status == "degraded" for item in health_results):
        overall = "degraded"
    elif accounts and all(value == "connected" for value in provider_status.values()) and (not health_results or all(item.status == "healthy" for item in health_results)):
        overall = "healthy"
    else:
        overall = "unknown"

    sync_times = [account.last_sync_at for account in accounts if account.last_sync_at]
    last_sync_at = max(sync_times) if sync_times else None
    github_summary = github.summary if github else {}
    render_summary = render.summary if render else {}
    return ProductSummary(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        owner=product.owner,
        status=overall,
        github_status=provider_status["github"],
        render_status=provider_status["render"],
        supabase_status=provider_status["supabase"],
        last_commit=github_summary.get("last_commit") if github else None,
        last_deploy=render_summary.get("last_deploy") if render else None,
        ci=(github_summary.get("workflow_runs") or [None])[0] if github else None,
        health=worst_health,
        last_sync_at=last_sync_at,
        alert_count=alert_count,
    )


def provider_account_dict(account: ProviderAccount) -> dict:
    return {
        "id": str(account.id),
        "provider": account.provider,
        "name": account.name,
        "product_id": str(account.product_id),
        "credential_ref": account.credential_ref,
        "external_account_id": account.external_account_id,
        "status": account.status,
        "connection_status": account.connection_status,
        "credential_configured": bool(os.getenv(account.credential_ref)),
        "last_sync_at": account.last_sync_at,
        "last_validated_at": account.last_validated_at,
        "last_error": account.last_error,
    }
