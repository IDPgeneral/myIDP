from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import ProductResource, ProviderAccount

CREDENTIAL_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


class CredentialUnavailable(RuntimeError):
    pass


class IsolationViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class ResourceBinding:
    product_id: str
    provider_account_id: str
    resource_id: str
    environment: str


class CredentialResolver:
    def resolve(self, account: ProviderAccount) -> str:
        credential_ref = account.credential_ref.strip()
        if not CREDENTIAL_REF_PATTERN.fullmatch(credential_ref):
            raise CredentialUnavailable("Referência de credencial inválida.")
        value = os.getenv(credential_ref, "")
        if not value:
            raise CredentialUnavailable(f"Credencial não configurada: {credential_ref}")
        return value


def assert_resource_binding(
    db: Session,
    *,
    product_id: str,
    provider_account_id: str,
    resource_id: str,
    environment: str | None = None,
) -> tuple[ProviderAccount, ProductResource]:
    account = db.get(ProviderAccount, uuid.UUID(provider_account_id))
    resource = db.get(ProductResource, uuid.UUID(resource_id))
    if account is None or resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conexão ou recurso não encontrado.")
    if str(account.product_id) != str(product_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conexão não pertence ao produto informado.")
    if str(resource.product_id) != str(product_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recurso não pertence ao produto informado.")
    if str(resource.provider_account_id) != str(provider_account_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recurso não pertence à conexão informada.")
    if environment and resource.environment != environment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ambiente do recurso não corresponde ao solicitado.")
    return account, resource
