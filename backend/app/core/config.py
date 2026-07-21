from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Internal Developer Portal"
    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/idp"

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    auth_disabled: bool = False

    allowed_admin_emails: str = ""
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    github_app_id: str = ""
    github_app_private_key: str = ""
    github_api_version: str = "2026-03-10"

    sync_enabled: bool = False
    sync_health_interval_minutes: int = 5
    sync_github_interval_minutes: int = 10
    sync_render_interval_minutes: int = 5
    sync_supabase_interval_minutes: int = 15
    sync_catalog_interval_minutes: int = 30

    http_timeout_seconds: float = 15.0
    health_default_timeout_seconds: float = 8.0
    catalog_directory: str = "../catalog"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.allowed_admin_emails.split(",")
            if email.strip()
        }

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [*self.cors_origins.split(","), self.frontend_url]
        return list(dict.fromkeys(origin.strip().rstrip("/") for origin in origins if origin.strip()))

    @property
    def normalized_github_private_key(self) -> str:
        return self.github_app_private_key.replace("\\n", "\n")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
