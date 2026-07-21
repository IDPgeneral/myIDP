from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.db.models import Product, ProductResource, ProviderAccount, SyncRun
from app.db.session import get_db
from app.schemas.common import SyncRunOut
from app.services.audit import audit
from app.services.sync import SyncBusyError, SyncCoordinator

router = APIRouter(tags=["sync"])


def _run_and_audit(db: Session, user: CurrentUser, action: str, callable, **audit_ids):
    try:
        run = callable()
        audit(db, action=action, user=user, success=run.status not in {"error"}, after_data={"sync_run_id": str(run.id), "status": run.status}, **audit_ids)
        return SyncRunOut.model_validate(run)
    except SyncBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sync/all", response_model=SyncRunOut)
def sync_all(user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    return _run_and_audit(db, user, "sync.all", SyncCoordinator(db, settings).sync_all)


@router.post("/sync/products/{product_id}", response_model=SyncRunOut)
def sync_product(product_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    product = db.get(Product, uuid.UUID(product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return _run_and_audit(db, user, "sync.product", lambda: SyncCoordinator(db, settings).sync_product(product), product_id=product_id)


@router.post("/sync/provider-accounts/{account_id}", response_model=SyncRunOut)
def sync_account(account_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    account = db.get(ProviderAccount, uuid.UUID(account_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    return _run_and_audit(db, user, "sync.provider_account", lambda: SyncCoordinator(db, settings).sync_account(account), product_id=str(account.product_id), provider_account_id=account_id)


@router.post("/sync/resources/{resource_id}", response_model=SyncRunOut)
def sync_resource(resource_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if resource is None:
        raise HTTPException(status_code=404, detail="Recurso não encontrado.")
    return _run_and_audit(db, user, "sync.resource", lambda: SyncCoordinator(db, settings).sync_resource(resource), product_id=str(resource.product_id), provider_account_id=str(resource.provider_account_id) if resource.provider_account_id else None, resource_id=resource_id)


@router.get("/sync/runs", response_model=list[SyncRunOut])
def list_sync_runs(_: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], limit: int = Query(50, ge=1, le=200)):
    runs = db.scalars(select(SyncRun).order_by(desc(SyncRun.created_at)).limit(limit)).all()
    return [SyncRunOut.model_validate(run) for run in runs]
