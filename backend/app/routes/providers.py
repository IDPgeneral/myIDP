from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.core.logging import sanitized_error
from app.core.security import CredentialResolver
from app.db.models import AuditLog, ProductResource, ProviderAccount, ResourceSnapshot
from app.db.session import get_db
from app.integrations.render.client import RenderClient
from app.schemas.common import ActionConfirmation
from app.services.audit import audit

router = APIRouter(tags=["providers"])


def _resources_for(db: Session, product_id: str, resource_type: str):
    return db.scalars(select(ProductResource).where(ProductResource.product_id == uuid.UUID(product_id), ProductResource.resource_type == resource_type, ProductResource.active.is_(True))).all()


def _latest(db: Session, resource_id: uuid.UUID, snapshot_type: str):
    return db.scalar(select(ResourceSnapshot).where(ResourceSnapshot.resource_id == resource_id, ResourceSnapshot.snapshot_type == snapshot_type).order_by(desc(ResourceSnapshot.captured_at)).limit(1))


@router.get("/products/{product_id}/github/repositories")
def github_repositories(product_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    output = []
    for resource in _resources_for(db, product_id, "repository"):
        snapshot = _latest(db, resource.id, "github_repository")
        output.append({"resource_id": str(resource.id), "name": resource.name, "environment": resource.environment, "url": resource.url, "snapshot": snapshot.payload_sanitized if snapshot else None, "captured_at": snapshot.captured_at if snapshot else None})
    return output


@router.get("/products/{product_id}/github/commits")
def github_commits(product_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    repos = github_repositories(product_id, user, db)
    return [{"resource_id": item["resource_id"], "name": item["name"], "last_commit": (item["snapshot"] or {}).get("last_commit")} for item in repos]


@router.get("/products/{product_id}/github/workflows")
def github_workflows(product_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    repos = github_repositories(product_id, user, db)
    return [{"resource_id": item["resource_id"], "name": item["name"], "workflow_runs": (item["snapshot"] or {}).get("workflow_runs", [])} for item in repos]


@router.get("/products/{product_id}/github/pull-requests")
def github_pull_requests(product_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    repos = github_repositories(product_id, user, db)
    return [{"resource_id": item["resource_id"], "name": item["name"], "open_pull_requests": (item["snapshot"] or {}).get("open_pull_requests", 0)} for item in repos]


@router.get("/products/{product_id}/render/services")
def render_services(product_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    output = []
    for resource in _resources_for(db, product_id, "render_service"):
        snapshot = _latest(db, resource.id, "render_service")
        output.append({"resource_id": str(resource.id), "name": resource.name, "environment": resource.environment, "snapshot": snapshot.payload_sanitized if snapshot else None, "captured_at": snapshot.captured_at if snapshot else None})
    return output


@router.get("/render/services/{resource_id}/deploys")
def render_deploys(resource_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "render_service":
        raise HTTPException(status_code=404, detail="Serviço Render não encontrado.")
    snapshot = _latest(db, resource.id, "render_service")
    return (snapshot.payload_sanitized if snapshot else {}).get("recent_deploys", [])


@router.get("/render/services/{resource_id}/usage")
def render_service_usage(resource_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "render_service":
        raise HTTPException(status_code=404, detail="Serviço Render não encontrado.")
    snapshot = _latest(db, resource.id, "render_service")
    return {"usage": (snapshot.payload_sanitized if snapshot else {}).get("usage"), "captured_at": snapshot.captured_at if snapshot else None}


def _render_write_action(resource_id: str, action_name: str, payload: ActionConfirmation, user: CurrentUser, db: Session, settings: Settings):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "render_service" or resource.provider_account_id is None:
        raise HTTPException(status_code=404, detail="Serviço Render não encontrado.")
    account = db.get(ProviderAccount, resource.provider_account_id)
    if account is None or account.provider != "render" or account.product_id != resource.product_id:
        raise HTTPException(status_code=409, detail="Vínculo Render inválido.")
    try:
        client = RenderClient(settings, CredentialResolver().resolve(account))
        result = (
            client.trigger_deploy(
                resource.external_id,
                commit_id=payload.commit_id,
                clear_cache=payload.clear_cache,
            )
            if action_name == "deploy"
            else client.restart_service(resource.external_id)
        )
        audit(
            db,
            action=f"render.{action_name}",
            user=user,
            product_id=str(resource.product_id),
            provider_account_id=str(account.id),
            resource_id=resource_id,
            after_data={
                "confirmation": payload.confirmation,
                "commit_id": payload.commit_id,
                "clear_cache": payload.clear_cache,
                "provider_response": result,
            },
            success=True,
        )
        return {"status": "accepted", "result": result}
    except Exception as exc:
        error = sanitized_error(exc)
        audit(db, action=f"render.{action_name}", user=user, product_id=str(resource.product_id), provider_account_id=str(account.id), resource_id=resource_id, success=False, error=error)
        raise HTTPException(status_code=502, detail=error) from exc


@router.post("/render/services/{resource_id}/deploy")
def trigger_render_deploy(resource_id: str, payload: ActionConfirmation, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    return _render_write_action(resource_id, "deploy", payload, user, db, settings)


@router.post("/render/services/{resource_id}/restart")
def restart_render_service(resource_id: str, payload: ActionConfirmation, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    return _render_write_action(resource_id, "restart", payload, user, db, settings)


@router.get("/render/services/{resource_id}/deploys/{deploy_id}/status")
def render_deploy_status(
    resource_id: str,
    deploy_id: Annotated[str, Path(pattern=r"^dep-[A-Za-z0-9]+$")],
    _: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "render_service" or resource.provider_account_id is None:
        raise HTTPException(status_code=404, detail="Serviço Render não encontrado.")
    account = db.get(ProviderAccount, resource.provider_account_id)
    if account is None or account.provider != "render" or account.product_id != resource.product_id:
        raise HTTPException(status_code=409, detail="Vínculo Render inválido.")
    try:
        payload = RenderClient(settings, CredentialResolver().resolve(account)).retrieve_deploy(resource.external_id, deploy_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=sanitized_error(exc)) from exc
    return payload


@router.get("/products/{product_id}/supabase/projects")
def supabase_projects(product_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    output = []
    for resource in _resources_for(db, product_id, "supabase_project"):
        snapshot = _latest(db, resource.id, "supabase_project")
        output.append({"resource_id": str(resource.id), "name": resource.name, "environment": resource.environment, "snapshot": snapshot.payload_sanitized if snapshot else None, "captured_at": snapshot.captured_at if snapshot else None})
    return output


@router.get("/supabase/projects/{resource_id}/status")
def supabase_project_status(resource_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "supabase_project":
        raise HTTPException(status_code=404, detail="Projeto Supabase não encontrado.")
    snapshot = _latest(db, resource.id, "supabase_project")
    return snapshot.payload_sanitized if snapshot else {"status": "unknown"}


@router.get("/supabase/projects/{resource_id}/usage")
def supabase_project_usage(resource_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None or resource.resource_type != "supabase_project":
        raise HTTPException(status_code=404, detail="Projeto Supabase não encontrado.")
    snapshot = _latest(db, resource.id, "supabase_project")
    return {
        "usage": (snapshot.payload_sanitized if snapshot else {}).get("usage"),
        "captured_at": snapshot.captured_at if snapshot else None,
        "message": "Métricas são exibidas somente quando disponíveis no snapshot.",
    }


@router.get("/audit-logs")
def audit_logs(_: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], limit: int = 100):
    logs = db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(min(max(limit, 1), 500))).all()
    return [{"id": str(log.id), "user_id": str(log.user_id) if log.user_id else None, "product_id": str(log.product_id) if log.product_id else None, "provider_account_id": str(log.provider_account_id) if log.provider_account_id else None, "resource_id": str(log.resource_id) if log.resource_id else None, "action": log.action, "success": log.success, "error": log.error, "correlation_id": log.correlation_id, "created_at": log.created_at} for log in logs]
