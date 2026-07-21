from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.integrations.base import ExternalProviderError, classify_http_error, safe_json
from app.integrations.usage import find_number, overall_usage_status, usage_metric

MEBIBYTE = 1024 * 1024
GIBIBYTE = 1024 * MEBIBYTE


class SupabaseManagementClient:
    base_url = "https://api.supabase.com"

    def __init__(self, settings: Settings, management_token: str):
        self.settings = settings
        self.management_token = management_token

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        headers = {"Authorization": f"Bearer {self.management_token}", "Accept": "application/json"}
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ExternalProviderError("Supabase indisponível.", category="provider_unavailable") from exc
        if response.status_code >= 400:
            raise classify_http_error(response, "Supabase")
        return safe_json(response)

    def test_connection(self) -> dict[str, Any]:
        data = self._request("GET", "/v1/projects")
        return {"reachable": True, "project_count": len(data) if isinstance(data, list) else 0}

    def _optional(self, method: str, path: str, **kwargs: Any) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        try:
            return self._request(method, path, **kwargs), None
        except ExternalProviderError as exc:
            return None, exc.category

    def _project_usage(self, project_ref: str, plan: str | None) -> dict[str, Any]:
        query_result, query_error = self._optional(
            "POST",
            f"/v1/projects/{project_ref}/database/query/read-only",
            json={
                "query": (
                    "select pg_database_size(current_database()) as database_size_bytes, "
                    "coalesce((select sum((metadata->>'size')::bigint) from storage.objects), 0) as storage_size_bytes"
                ),
                "parameters": [],
            },
        )
        disk_util, disk_error = self._optional("GET", f"/v1/projects/{project_ref}/config/disk/util")
        disk_config, disk_config_error = self._optional("GET", f"/v1/projects/{project_ref}/config/disk")
        api_counts, api_error = self._optional("GET", f"/v1/projects/{project_ref}/analytics/endpoints/usage.api-requests-count")

        database_size = find_number(query_result, ["database_size_bytes", "database_size"])
        if database_size is None:
            database_size = find_number(disk_util, ["database_size_bytes", "database_size"])
        storage_size = find_number(query_result, ["storage_size_bytes", "storage_size"])
        disk_used = find_number(disk_util, ["used_bytes", "disk_used_bytes", "usage_bytes", "used"])
        disk_limit = find_number(disk_config, ["size_bytes", "disk_size_bytes", "capacity_bytes"])
        if disk_used is None:
            disk_used_gb = find_number(disk_util, ["used_gb", "disk_used_gb", "usage_gb"])
            disk_used = disk_used_gb * GIBIBYTE if disk_used_gb is not None else None
        if disk_limit is None:
            disk_limit_gb = find_number(disk_config, ["size_gb", "disk_size_gb", "capacity_gb", "size"])
            disk_limit = disk_limit_gb * GIBIBYTE if disk_limit_gb is not None else None
        api_requests = find_number(api_counts, ["count", "requests", "request_count", "total_requests", "api_requests", "total"])

        is_free = (plan or "").lower() == "free"
        metrics = [
            usage_metric("database_size", "Tamanho do banco", value=database_size, limit=500 * MEBIBYTE if is_free else None, unit="bytes", source="read_only_sql" if query_result else "provider_api"),
            usage_metric("storage_size", "Storage", value=storage_size, limit=GIBIBYTE if is_free else None, unit="bytes", scope="organization" if is_free else "resource", source="read_only_sql"),
            usage_metric("disk", "Disco provisionado", value=disk_used, limit=disk_limit, unit="bytes"),
            usage_metric("api_requests", "Requisições de API", value=api_requests, limit=None, unit="requisições", period="provider_window"),
        ]
        if is_free:
            metrics.extend(
                [
                    usage_metric("egress", "Egress", value=None, limit=5 * GIBIBYTE, unit="bytes", scope="organization", period="billing_cycle", source="plan_limit"),
                    usage_metric("mau", "Usuários ativos mensais", value=None, limit=50_000, unit="MAU", scope="organization", period="billing_cycle", source="plan_limit"),
                    usage_metric("edge_invocations", "Edge Function invocations", value=None, limit=500_000, unit="invocações", scope="organization", period="billing_cycle", source="plan_limit"),
                    usage_metric("realtime_messages", "Mensagens Realtime", value=None, limit=2_000_000, unit="mensagens", scope="organization", period="billing_cycle", source="plan_limit"),
                    usage_metric("realtime_connections", "Pico de conexões Realtime", value=None, limit=200, unit="conexões", scope="organization", period="billing_cycle", source="plan_limit"),
                ]
            )
        unavailable = [name for name, error in (("database_query", query_error), ("disk_util", disk_error), ("disk_config", disk_config_error), ("api_requests", api_error)) if error]
        return {
            "status": overall_usage_status(metrics),
            "captured_at": datetime.now(UTC).isoformat(),
            "plan": plan or "unknown",
            "metrics": metrics,
            "unavailable": unavailable,
        }

    def project_snapshot(self, project_ref: str, plan: str | None = None) -> dict[str, Any]:
        project = self._request("GET", f"/v1/projects/{project_ref}")
        assert isinstance(project, dict)
        health: dict[str, Any] | list[Any]
        try:
            health = self._request(
                "GET",
                f"/v1/projects/{project_ref}/health",
                params={"services": ["auth", "db", "rest", "storage", "realtime"], "timeout_ms": 5000},
            )
        except ExternalProviderError as exc:
            health = {"status": "unknown", "message": str(exc)}
        return {
            "project": {
                "id": project.get("id"),
                "ref": project.get("ref") or project_ref,
                "name": project.get("name"),
                "organization_id": project.get("organization_id"),
                "region": project.get("region"),
                "status": project.get("status"),
                "plan": plan or "unknown",
                "database": project.get("database", {}),
                "created_at": project.get("created_at"),
                "dashboard_url": f"https://supabase.com/dashboard/project/{project_ref}",
            },
            "health": health,
            "usage": self._project_usage(project_ref, plan),
        }
