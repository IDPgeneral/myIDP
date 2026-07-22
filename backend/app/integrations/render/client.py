from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx

from app.core.config import Settings
from app.integrations.base import ExternalProviderError, classify_http_error, safe_json
from app.integrations.usage import overall_usage_status, series_value, usage_metric


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

    def _service_usage(self, service_id: str, plan: str | None) -> dict[str, Any]:
        now = datetime.now(UTC)
        params = {
            "resource": service_id,
            "startTime": (now - timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
            "endTime": now.isoformat().replace("+00:00", "Z"),
            "resolutionSeconds": 900,
        }
        endpoints: dict[str, tuple[str, Literal["latest", "max", "sum"]]] = {
            "cpu": ("/metrics/cpu", "max"),
            "cpu_limit": ("/metrics/cpu-limit", "latest"),
            "memory": ("/metrics/memory", "max"),
            "memory_limit": ("/metrics/memory-limit", "latest"),
            "bandwidth": ("/metrics/bandwidth", "sum"),
            "disk": ("/metrics/disk-usage", "max"),
            "disk_limit": ("/metrics/disk-capacity", "latest"),
        }
        values: dict[str, tuple[float | None, str]] = {}
        unavailable: list[str] = []
        for key, (path, aggregation) in endpoints.items():
            try:
                payload = self._request("GET", path, params=params)
                values[key] = series_value(payload, aggregation=aggregation)
            except ExternalProviderError:
                values[key] = (None, "")
                unavailable.append(key)

        cpu, cpu_unit = values["cpu"]
        cpu_limit, cpu_limit_unit = values["cpu_limit"]
        memory, memory_unit = values["memory"]
        memory_limit, memory_limit_unit = values["memory_limit"]
        bandwidth, bandwidth_unit = values["bandwidth"]
        disk, disk_unit = values["disk"]
        disk_limit, disk_limit_unit = values["disk_limit"]
        metrics = [
            usage_metric("cpu", "CPU (pico em 24h)", value=cpu, limit=cpu_limit, unit=cpu_unit or cpu_limit_unit or "CPU", period="24h"),
            usage_metric("memory", "Memória (pico em 24h)", value=memory, limit=memory_limit, unit=memory_unit or memory_limit_unit or "bytes", period="24h"),
            usage_metric("bandwidth", "Tráfego de saída (24h)", value=bandwidth, limit=None, unit=bandwidth_unit or "bytes", period="24h"),
            usage_metric("disk", "Disco persistente", value=disk, limit=disk_limit, unit=disk_unit or disk_limit_unit or "bytes"),
        ]
        if (plan or "").lower() == "free":
            metrics.append(
                usage_metric(
                    "free_instance_hours",
                    "Horas de instância grátis",
                    value=None,
                    limit=750,
                    unit="h/mês",
                    scope="workspace",
                    period="calendar_month",
                    source="plan_limit",
                    description="Cota compartilhada por todos os Web Services grátis do workspace; a API pública não informa o consumo mensal.",
                )
            )
        return {
            "status": overall_usage_status(metrics),
            "captured_at": now.isoformat(),
            "metrics": metrics,
            "unavailable": unavailable,
        }

    def service_snapshot(self, service_id: str, plan: str | None = None) -> dict[str, Any]:
        service = self._request("GET", f"/services/{service_id}")
        deploys = self._request("GET", f"/services/{service_id}/deploys", params={"limit": 10})
        assert isinstance(service, dict)
        service_details = service.get("serviceDetails", {})
        if not isinstance(service_details, dict):
            service_details = {}
        detected_plan = str(service_details.get("plan") or plan or "unknown")
        deploy_items = deploys if isinstance(deploys, list) else []
        latest_wrapper = deploy_items[0] if deploy_items else {}
        latest = latest_wrapper.get("deploy", latest_wrapper) if isinstance(latest_wrapper, dict) else {}
        return {
            "service": {
                "id": service.get("id"),
                "name": service.get("name"),
                "type": service.get("type"),
                "branch": service.get("branch"),
                "url": service_details.get("url") or service.get("url"),
                "plan": detected_plan,
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
            "usage": self._service_usage(service_id, detected_plan),
        }

    def trigger_deploy(
        self,
        service_id: str,
        *,
        commit_id: str | None = None,
        clear_cache: bool = False,
    ) -> dict[str, Any] | list[Any]:
        payload = {"clearCache": "clear" if clear_cache else "do_not_clear"}
        if commit_id:
            payload["commitId"] = commit_id
        return self._request("POST", f"/services/{service_id}/deploys", json=payload)

    def retrieve_deploy(self, service_id: str, deploy_id: str) -> dict[str, Any] | list[Any]:
        return self._request("GET", f"/services/{service_id}/deploys/{deploy_id}")

    def restart_service(self, service_id: str) -> dict[str, Any] | list[Any]:
        return self._request("POST", f"/services/{service_id}/restart")
