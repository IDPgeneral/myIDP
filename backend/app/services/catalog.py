from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import HealthCheck, Product, ProductResource, ProviderAccount

FORBIDDEN_KEYS = {"token", "secret", "password", "apiKey", "api_key", "privateKey", "private_key", "serviceRoleKey", "connectionString"}
PLACEHOLDER_VALUES = {"REPLACE_ME", "PLACEHOLDER", "TODO"}


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    title: str
    description: str | None = None


class RepositorySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    fullName: str
    defaultBranch: str = "main"
    path: str | None = None


class RenderServiceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    serviceId: str
    plan: str = "free"


class SupabaseProjectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    projectRef: str
    plan: str = "free"


class GitHubProviderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection: str
    repositories: list[RepositorySpec] = Field(default_factory=list)


class RenderProviderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection: str
    services: list[RenderServiceSpec] = Field(default_factory=list)


class SupabaseProviderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection: str
    projects: list[SupabaseProjectSpec] = Field(default_factory=list)


class ProvidersSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    github: GitHubProviderSpec | None = None
    render: RenderProviderSpec | None = None
    supabase: SupabaseProviderSpec | None = None


class HealthCheckSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    url: str
    expectedStatus: int = 200


class DocumentationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repositoryReadme: str | None = None
    projectReadme: str | None = None
    modulesIndex: str | None = None


class SystemSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner: str
    lifecycle: str
    providers: ProvidersSpec
    healthChecks: list[HealthCheckSpec] = Field(default_factory=list)
    documentation: DocumentationSpec | None = None


class CatalogDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    apiVersion: str
    kind: str
    metadata: Metadata
    spec: SystemSpec


def _reject_secrets(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in FORBIDDEN_KEYS or any(fragment in str(key).lower() for fragment in ("token", "secret", "password", "private_key", "api_key")):
                raise ValueError(f"Campo de credencial proibido no catálogo: {key}")
            _reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            _reject_secrets(item)


def load_catalog_file(path: Path) -> CatalogDocument:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Catálogo YAML deve conter um objeto.")
    _reject_secrets(raw)
    try:
        document = CatalogDocument.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Catálogo inválido: {exc}") from exc
    if document.apiVersion != "platform.internal/v1" or document.kind != "System":
        raise ValueError("apiVersion ou kind não suportado.")
    return document


def import_catalog_document(db: Session, document: CatalogDocument) -> dict[str, int]:
    product = db.scalar(select(Product).where(Product.slug == document.metadata.name))
    if product is None:
        product = Product(
            name=document.metadata.title,
            slug=document.metadata.name,
            description=document.metadata.description,
            owner=document.spec.owner,
            status="unknown",
        )
        db.add(product)
        db.flush()
    else:
        product.name = document.metadata.title
        product.description = document.metadata.description
        product.owner = document.spec.owner

    created = {"resources": 0, "health_checks": 0}

    def account_by_name(name: str) -> ProviderAccount:
        account = db.scalar(select(ProviderAccount).where(ProviderAccount.name == name, ProviderAccount.product_id == product.id))
        if account is None:
            raise ValueError(f"Conexão não encontrada para o produto: {name}")
        return account

    providers = document.spec.providers
    if providers.github:
        account = account_by_name(providers.github.connection)
        for repo in providers.github.repositories:
            existing = db.scalar(select(ProductResource).where(ProductResource.provider_account_id == account.id, ProductResource.resource_type == "repository", ProductResource.external_id == repo.fullName))
            if existing is None:
                db.add(ProductResource(product_id=product.id, provider_account_id=account.id, resource_type="repository", external_id=repo.fullName, name=repo.name, environment="production", url=None, metadata_json={"default_branch": repo.defaultBranch, "path": repo.path}, active=repo.fullName not in PLACEHOLDER_VALUES))
                created["resources"] += 1
    if providers.render:
        account = account_by_name(providers.render.connection)
        for service in providers.render.services:
            existing = db.scalar(select(ProductResource).where(ProductResource.provider_account_id == account.id, ProductResource.resource_type == "render_service", ProductResource.external_id == service.serviceId))
            if existing is None:
                db.add(ProductResource(product_id=product.id, provider_account_id=account.id, resource_type="render_service", external_id=service.serviceId, name=service.name, environment="production", metadata_json={"plan": service.plan}, active=service.serviceId not in PLACEHOLDER_VALUES))
                created["resources"] += 1
            else:
                existing.metadata_json = {**existing.metadata_json, "plan": service.plan}
    if providers.supabase:
        account = account_by_name(providers.supabase.connection)
        for project in providers.supabase.projects:
            existing = db.scalar(select(ProductResource).where(ProductResource.provider_account_id == account.id, ProductResource.resource_type == "supabase_project", ProductResource.external_id == project.projectRef))
            if existing is None:
                db.add(ProductResource(product_id=product.id, provider_account_id=account.id, resource_type="supabase_project", external_id=project.projectRef, name=project.name, environment="production", metadata_json={"plan": project.plan}, active=project.projectRef not in PLACEHOLDER_VALUES))
                created["resources"] += 1
            else:
                existing.metadata_json = {**existing.metadata_json, "plan": project.plan}
    for check in document.spec.healthChecks:
        existing = db.scalar(select(HealthCheck).where(HealthCheck.product_id == product.id, HealthCheck.name == check.name))
        if existing is None:
            db.add(HealthCheck(product_id=product.id, name=check.name, url=check.url, method="GET", expected_status=check.expectedStatus, timeout_seconds=8, active="example.com" not in check.url and "REPLACE_ME" not in check.url))
            created["health_checks"] += 1
    if document.spec.documentation:
        docs = document.spec.documentation.model_dump(exclude_none=True)
        for name, path in docs.items():
            external_id = f"{document.metadata.name}:{name}"
            existing = db.scalar(select(ProductResource).where(ProductResource.product_id == product.id, ProductResource.resource_type == "documentation", ProductResource.external_id == external_id))
            if existing is None:
                db.add(ProductResource(product_id=product.id, provider_account_id=None, resource_type="documentation", external_id=external_id, name=name, environment="production", url=None, metadata_json={"path": path}, active=True))
                created["resources"] += 1
    db.commit()
    return created


def import_catalog_directory(db: Session, directory: str) -> dict[str, Any]:
    base = Path(directory).resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"Diretório de catálogo não encontrado: {base}")
    results: dict[str, Any] = {}
    for path in sorted(base.glob("*.yaml")):
        document = load_catalog_file(path)
        results[path.name] = import_catalog_document(db, document)
    return results
