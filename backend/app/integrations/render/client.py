from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.integrations.base import ExternalProviderError, classify_http_error, safe_json


class RenderClient:
    base_url = "https://api.render.com/v1"

    def __init__(self, settings: Settings, api_key: str):
        self.settings = settings
        self.api_key = api_key

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ExternalProviderError("Render indisponível.", category="provider_unavailable") from exc
        if response.status_code >= 400:
            raise classify_http_error(response, "Render")
        if response.status_code == 204 or not response.content:
            return {}
        return safe_json(response)

    def test_connection(self) -> dict[str, Any]:
        data = self._request("GET", "/services", params={"limit": 1})
        return {"reachable": True, "sample_count": len(data) if isinstance(data, list) else 1}

    def service_snapshot(self, service_id: str) -> dict[str, Any]:
        service = self._request("GET", f"/services/{service_id}")
        deploys = self._request("GET", f"/services/{service_id}/deploys", params={"limit": 10})
        assert isinstance(service, dict)
        deploy_items = deploys if isinstance(deploys, list) else []
        latest_wrapper = deploy_items[0] if deploy_items else {}
        latest = latest_wrapper.get("deploy", latest_wrapper) if isinstance(latest_wrapper, dict) else {}
        return {
            "service": {
                "id": service.get("id"),
                "name": service.get("name"),
                "type": service.get("type"),
                "branch": service.get("branch"),
                "url": service.get("serviceDetails", {}).get("url") or service.get("url"),
                "dashboard_url": f"https://dashboard.render.com/{service_id}",
                "suspended": service.get("suspended"),
                "updated_at": service.get("updatedAt"),
            },
            "last_deploy": {
                "id": latest.get("id"),
                "status": latest.get("status"),
                "commit": latest.get("commit"),
                "created_at": latest.get("createdAt"),
                "started_at": latest.get("startedAt"),
                "finished_at": latest.get("finishedAt"),
                "updated_at": latest.get("updatedAt"),
                "trigger": latest.get("trigger"),
            },
            "recent_deploys": [
                {
                    "id": (item.get("deploy", item) or {}).get("id"),
                    "status": (item.get("deploy", item) or {}).get("status"),
                    "commit": (item.get("deploy", item) or {}).get("commit"),
                    "created_at": (item.get("deploy", item) or {}).get("createdAt"),
                    "finished_at": (item.get("deploy", item) or {}).get("finishedAt"),
                }
                for item in deploy_items
                if isinstance(item, dict)
            ],
        }

    def trigger_deploy(self, service_id: str) -> dict[str, Any] | list[Any]:
        return self._request("POST", f"/services/{service_id}/deploys", json={"clearCache": "do_not_clear"})

    def restart_service(self, service_id: str) -> dict[str, Any] | list[Any]:
        return self._request("POST", f"/services/{service_id}/restart")
