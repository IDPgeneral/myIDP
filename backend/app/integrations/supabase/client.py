from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.integrations.base import ExternalProviderError, classify_http_error, safe_json


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

    def project_snapshot(self, project_ref: str) -> dict[str, Any]:
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
                "database": project.get("database", {}),
                "created_at": project.get("created_at"),
                "dashboard_url": f"https://supabase.com/dashboard/project/{project_ref}",
            },
            "health": health,
        }
