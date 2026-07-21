from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    owner: str = Field(min_length=2, max_length=120)


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    status: str | None = None
    owner: str | None = Field(default=None, min_length=2, max_length=120)


class ProviderAccountCreate(BaseModel):
    provider: Literal["github", "render", "supabase"]
    name: str = Field(min_length=3, max_length=120)
    product_id: str
    credential_ref: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")
    external_account_id: str | None = None


class ProviderAccountPatch(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    credential_ref: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{2,127}$")
    external_account_id: str | None = None
    status: str | None = None


class ResourceCreate(BaseModel):
    provider_account_id: str | None = None
    resource_type: Literal["repository", "render_service", "supabase_project", "health_endpoint", "documentation", "domain"]
    external_id: str = Field(min_length=1, max_length=300)
    name: str = Field(min_length=1, max_length=160)
    environment: Literal["production", "staging", "development"] = "production"
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    @field_validator("metadata")
    @classmethod
    def reject_secret_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"token", "secret", "password", "api_key", "private_key", "service_role_key", "connection_string"}
        keys = {str(key).lower() for key in value}
        if keys & forbidden:
            raise ValueError("Metadados não podem conter credenciais.")
        return value


class ResourcePatch(BaseModel):
    name: str | None = None
    environment: Literal["production", "staging", "development"] | None = None
    url: str | None = None
    metadata: dict[str, Any] | None = None
    active: bool | None = None


class UserCreate(BaseModel):
    email: str
    display_name: str | None = None
    role: Literal["viewer", "admin"] = "viewer"
    active: bool = True


class UserPatch(BaseModel):
    display_name: str | None = None
    role: Literal["viewer", "admin"] | None = None
    active: bool | None = None
