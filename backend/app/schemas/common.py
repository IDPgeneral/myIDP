from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

StatusName = Literal[
    "healthy",
    "degraded",
    "down",
    "unknown",
    "syncing",
    "error",
    "authentication_error",
    "permission_error",
    "provider_unavailable",
    "not_configured",
    "connected",
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    status: str
    owner: str
    created_at: datetime
    updated_at: datetime


class ProviderAccountOut(ORMModel):
    id: uuid.UUID
    provider: str
    name: str
    product_id: uuid.UUID
    credential_ref: str
    external_account_id: str | None
    status: str
    connection_status: str
    credential_configured: bool = False
    last_sync_at: datetime | None
    last_validated_at: datetime | None
    last_error: str | None


class ProductResourceOut(ORMModel):
    id: uuid.UUID
    product_id: uuid.UUID
    provider_account_id: uuid.UUID | None
    resource_type: str
    external_id: str
    name: str
    environment: str
    url: str | None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    active: bool


class HealthResultOut(BaseModel):
    health_check_id: str
    name: str
    status: str
    http_status: int | None
    response_time_ms: int | None
    message: str
    checked_at: datetime | None


class ProductSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    owner: str
    status: str
    github_status: str
    render_status: str
    supabase_status: str
    last_commit: dict[str, Any] | None = None
    last_deploy: dict[str, Any] | None = None
    ci: dict[str, Any] | None = None
    health: HealthResultOut | None = None
    last_sync_at: datetime | None = None
    alert_count: int = 0


class ProductDetail(BaseModel):
    summary: ProductSummary
    resources: list[ProductResourceOut]
    provider_accounts: list[ProviderAccountOut]
    health_checks: list[HealthResultOut]


class SyncRunOut(ORMModel):
    id: uuid.UUID
    target_type: str
    target_id: str | None
    product_id: uuid.UUID | None
    provider_account_id: uuid.UUID | None
    resource_id: uuid.UUID | None
    provider: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    error: str | None
    correlation_id: str | None
    created_at: datetime


class ActionConfirmation(BaseModel):
    confirmation: Literal["CONFIRMAR"]
    commit_id: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{7,40}$")
    clear_cache: bool = False


class MessageResponse(BaseModel):
    message: str
    correlation_id: str | None = None
