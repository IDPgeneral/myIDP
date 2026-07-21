from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.core.logging import sanitized_error
from app.db.models import Product, ProviderAccount
from app.db.session import get_db
from app.schemas.common import ProviderAccountOut
from app.schemas.inputs import ProviderAccountCreate, ProviderAccountPatch
from app.services.audit import audit
from app.services.status import provider_account_dict
from app.services.sync import SyncCoordinator

router = APIRouter(tags=["provider-accounts"])


@router.get("/provider-accounts", response_model=list[ProviderAccountOut])
def list_accounts(_: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    accounts = db.scalars(select(ProviderAccount).order_by(ProviderAccount.name)).all()
    return [provider_account_dict(account) for account in accounts]


@router.post("/provider-accounts", response_model=ProviderAccountOut, status_code=201)
def create_account(payload: ProviderAccountCreate, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    product = db.get(Product, uuid.UUID(payload.product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    if db.scalar(select(ProviderAccount).where(ProviderAccount.name == payload.name)):
        raise HTTPException(status_code=409, detail="Nome da conexão já cadastrado.")
    account = ProviderAccount(**payload.model_dump(), status="not_configured", connection_status="not_configured")
    db.add(account)
    db.commit()
    db.refresh(account)
    audit(db, action="provider_account.create", user=user, product_id=payload.product_id, provider_account_id=str(account.id), after_data={"name": account.name, "provider": account.provider, "credential_ref": account.credential_ref}, success=True)
    return provider_account_dict(account)


@router.patch("/provider-accounts/{account_id}", response_model=ProviderAccountOut)
def patch_account(account_id: str, payload: ProviderAccountPatch, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    account = db.get(ProviderAccount, uuid.UUID(account_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    before = {"name": account.name, "credential_ref": account.credential_ref, "external_account_id": account.external_account_id, "status": account.status}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    audit(db, action="provider_account.update", user=user, product_id=str(account.product_id), provider_account_id=account_id, before_data=before, after_data=payload.model_dump(exclude_unset=True), success=True)
    return provider_account_dict(account)


@router.post("/provider-accounts/{account_id}/test")
def test_account(account_id: str, user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    account = db.get(ProviderAccount, uuid.UUID(account_id))
    if account is None:
        raise HTTPException(status_code=404, detail="Conexão não encontrada.")
    try:
        result = SyncCoordinator(db, settings).test_account(account)
        audit(db, action="provider_account.test", user=user, product_id=str(account.product_id), provider_account_id=account_id, after_data=result, success=True)
        return {"status": "connected", "result": result}
    except Exception as exc:
        error = sanitized_error(exc)
        audit(db, action="provider_account.test", user=user, product_id=str(account.product_id), provider_account_id=account_id, success=False, error=error)
        raise HTTPException(status_code=502, detail=error) from exc
