from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import correlation_id_var, sanitize_payload, sanitized_error
from app.core.security import CredentialResolver, CredentialUnavailable
from app.db.models import Product, ProductResource, ProviderAccount, ResourceSnapshot, SyncRun
from app.integrations.base import ExternalProviderError
from app.integrations.github.client import GitHubClient
from app.integrations.render.client import RenderClient
from app.integrations.supabase.client import SupabaseManagementClient


class SyncBusyError(RuntimeError):
    pass


class LockRegistry:
    def __init__(self) -> None:
        self._registry_lock = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def get(self, key: str) -> threading.Lock:
        with self._registry_lock:
            return self._locks.setdefault(key, threading.Lock())


LOCKS = LockRegistry()


class SyncCoordinator:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.credentials = CredentialResolver()

    def _new_run(
        self,
        target_type: str,
        *,
        target_id: str | None = None,
        product_id: str | None = None,
        provider_account_id: str | None = None,
        resource_id: str | None = None,
        provider: str | None = None,
    ) -> SyncRun:
        run = SyncRun(
            target_type=target_type,
            target_id=target_id,
            product_id=uuid.UUID(product_id) if product_id else None,
            provider_account_id=uuid.UUID(provider_account_id) if provider_account_id else None,
            resource_id=uuid.UUID(resource_id) if resource_id else None,
            provider=provider,
            status="running",
            correlation_id=correlation_id_var.get() or None,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _finish(self, run: SyncRun, status: str, error: str | None = None) -> SyncRun:
        run.status = status
        run.error = error
        run.finished_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _snapshot(self, resource: ProductResource, provider: str, snapshot_type: str, payload: dict[str, Any], status: str) -> None:
        summary = payload
        snapshot = ResourceSnapshot(
            provider=provider,
            snapshot_type=snapshot_type,
            resource_id=resource.id,
            status=status,
            summary=sanitize_payload(summary),
            payload_sanitized=sanitize_payload(payload),
        )
        self.db.add(snapshot)
        self.db.commit()

    def _client(self, account: ProviderAccount) -> Any:
        credential = self.credentials.resolve(account)
        if account.provider == "github":
            return GitHubClient(self.settings, credential)
        if account.provider == "render":
            return RenderClient(self.settings, credential)
        if account.provider == "supabase":
            return SupabaseManagementClient(self.settings, credential)
        raise ExternalProviderError("Provedor não suportado.", category="not_configured")

    def test_account(self, account: ProviderAccount) -> dict[str, Any]:
        try:
            result = self._client(account).test_connection()
            account.status = "connected"
            account.connection_status = "connected"
            account.last_error = None
            account.last_validated_at = datetime.now(UTC)
            self.db.commit()
            return result
        except (CredentialUnavailable, ExternalProviderError) as exc:
            account.status = getattr(exc, "category", "not_configured")
            account.connection_status = account.status
            account.last_error = sanitized_error(exc)
            account.last_validated_at = datetime.now(UTC)
            self.db.commit()
            raise

    def sync_resource(self, resource: ProductResource) -> SyncRun:
        if resource.provider_account_id is None:
            run = self._new_run("resource", target_id=str(resource.id), product_id=str(resource.product_id), resource_id=str(resource.id))
            return self._finish(run, "skipped", "Recurso sem conta de provedor.")
        account = self.db.get(ProviderAccount, resource.provider_account_id)
        if account is None or account.product_id != resource.product_id:
            run = self._new_run("resource", target_id=str(resource.id), product_id=str(resource.product_id), resource_id=str(resource.id))
            return self._finish(run, "error", "Vínculo de conta inválido.")
        lock = LOCKS.get(f"resource:{resource.id}")
        if not lock.acquire(blocking=False):
            raise SyncBusyError("Já existe sincronização em andamento para este recurso.")
        run = self._new_run(
            "resource",
            target_id=str(resource.id),
            product_id=str(resource.product_id),
            provider_account_id=str(account.id),
            resource_id=str(resource.id),
            provider=account.provider,
        )
        try:
            client = self._client(account)
            if account.provider == "github" and resource.resource_type == "repository":
                payload = client.repository_snapshot(resource.external_id)
                self._snapshot(resource, "github", "github_repository", payload, "healthy")
            elif account.provider == "render" and resource.resource_type == "render_service":
                payload = client.service_snapshot(resource.external_id, plan=str(resource.metadata_json.get("plan") or "unknown"))
                deploy_status = str((payload.get("last_deploy") or {}).get("status") or "unknown")
                status_value = "healthy" if deploy_status in {"live", "succeeded", "success"} else "degraded" if deploy_status != "unknown" else "unknown"
                if (payload.get("usage") or {}).get("status") == "critical":
                    status_value = "degraded"
                self._snapshot(resource, "render", "render_service", payload, status_value)
            elif account.provider == "supabase" and resource.resource_type == "supabase_project":
                payload = client.project_snapshot(resource.external_id, plan=str(resource.metadata_json.get("plan") or "unknown"))
                project_status = str((payload.get("project") or {}).get("status") or "unknown").upper()
                status_value = "healthy" if project_status in {"ACTIVE_HEALTHY", "ACTIVE"} else "degraded"
                if (payload.get("usage") or {}).get("status") == "critical":
                    status_value = "degraded"
                self._snapshot(resource, "supabase", "supabase_project", payload, status_value)
            else:
                return self._finish(run, "skipped", "Tipo de recurso incompatível com o provedor.")
            account.status = "connected"
            account.connection_status = "connected"
            account.last_error = None
            account.last_sync_at = datetime.now(UTC)
            self.db.commit()
            return self._finish(run, "success")
        except (CredentialUnavailable, ExternalProviderError, Exception) as exc:
            category = getattr(exc, "category", "not_configured" if isinstance(exc, CredentialUnavailable) else "error")
            account.status = category
            account.connection_status = category
            account.last_error = sanitized_error(exc)
            account.last_sync_at = datetime.now(UTC)
            self.db.commit()
            return self._finish(run, "error", sanitized_error(exc))
        finally:
            lock.release()

    def sync_account(self, account: ProviderAccount) -> SyncRun:
        lock = LOCKS.get(f"account:{account.id}")
        if not lock.acquire(blocking=False):
            raise SyncBusyError("Já existe sincronização em andamento para esta conexão.")
        run = self._new_run(
            "provider_account",
            target_id=str(account.id),
            product_id=str(account.product_id),
            provider_account_id=str(account.id),
            provider=account.provider,
        )
        failures = 0
        try:
            resources = self.db.scalars(
                select(ProductResource).where(ProductResource.provider_account_id == account.id, ProductResource.active.is_(True))
            ).all()
            if not resources:
                self.test_account(account)
            for resource in resources:
                child = self.sync_resource(resource)
                if child.status == "error":
                    failures += 1
            return self._finish(run, "partial" if failures else "success", f"{failures} recurso(s) falharam." if failures else None)
        except (CredentialUnavailable, ExternalProviderError) as exc:
            return self._finish(run, "error", sanitized_error(exc))
        finally:
            lock.release()

    def sync_product(self, product: Product) -> SyncRun:
        run = self._new_run("product", target_id=str(product.id), product_id=str(product.id))
        failures = 0
        accounts = self.db.scalars(select(ProviderAccount).where(ProviderAccount.product_id == product.id)).all()
        for account in accounts:
            try:
                child = self.sync_account(account)
                if child.status in {"error", "partial"}:
                    failures += 1
            except SyncBusyError:
                failures += 1
        return self._finish(run, "partial" if failures else "success", f"{failures} conexão(ões) com falha." if failures else None)

    def sync_all(self) -> SyncRun:
        run = self._new_run("all")
        failures = 0
        products = self.db.scalars(select(Product)).all()
        for product in products:
            child = self.sync_product(product)
            if child.status in {"error", "partial"}:
                failures += 1
        return self._finish(run, "partial" if failures else "success", f"{failures} produto(s) com falha." if failures else None)
