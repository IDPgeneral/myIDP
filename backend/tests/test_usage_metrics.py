from app.core.config import Settings
from app.integrations.render.client import RenderClient
from app.integrations.supabase.client import GIBIBYTE, MEBIBYTE, SupabaseManagementClient
from app.integrations.usage import metric_status, series_value


def test_metric_thresholds():
    assert metric_status(74, 100) == "ok"
    assert metric_status(75, 100) == "warning"
    assert metric_status(90, 100) == "critical"
    assert metric_status(None, 100) == "unknown"


def test_render_series_normalization():
    payload = [
        {
            "labels": [{"field": "resource", "value": "srv-test"}],
            "values": [
                {"timestamp": "2026-07-21T10:00:00Z", "value": 0.25},
                {"timestamp": "2026-07-21T11:00:00Z", "value": 0.75},
            ],
            "unit": "CPU",
        }
    ]
    assert series_value(payload, aggregation="max") == (0.75, "CPU")
    assert series_value(payload, aggregation="latest") == (0.75, "CPU")
    assert series_value(payload, aggregation="sum") == (1.0, "CPU")


def test_render_usage_is_best_effort_and_marks_free_workspace_quota(monkeypatch):
    client = RenderClient(Settings(app_env="test", database_url="sqlite://"), "token")
    request_params = []

    def fake_request(method, path, **kwargs):
        request_params.append(kwargs["params"])
        values = {
            "/metrics/cpu": 0.8,
            "/metrics/cpu-limit": 1,
            "/metrics/memory": 400,
            "/metrics/memory-limit": 512,
            "/metrics/bandwidth": 10,
            "/metrics/disk-usage": 20,
            "/metrics/disk-capacity": 100,
        }
        return [{"values": [{"timestamp": "2026-07-21T11:00:00Z", "value": values[path]}], "unit": "bytes" if "memory" in path or "disk" in path or "bandwidth" in path else "CPU"}]

    monkeypatch.setattr(client, "_request", fake_request)
    usage = client._service_usage("srv-test", "free")
    assert usage["status"] == "warning"
    assert next(metric for metric in usage["metrics"] if metric["key"] == "cpu")["percentage"] == 80
    hours = next(metric for metric in usage["metrics"] if metric["key"] == "free_instance_hours")
    assert hours["limit"] == 750
    assert hours["scope"] == "workspace"
    assert len(request_params) == 7
    assert all(params["resource"] == "srv-test" for params in request_params)
    assert all(isinstance(params["startTime"], str) and params["startTime"].endswith("Z") for params in request_params)
    assert all(isinstance(params["endTime"], str) and params["endTime"].endswith("Z") for params in request_params)


def test_supabase_free_quotas_use_read_only_sizes(monkeypatch):
    client = SupabaseManagementClient(Settings(app_env="test", database_url="sqlite://"), "token")

    def fake_optional(method, path, **kwargs):
        if path.endswith("database/query/read-only"):
            return [{"database_size_bytes": 250 * MEBIBYTE, "storage_size_bytes": 256 * MEBIBYTE}], None
        if path.endswith("config/disk/util"):
            return {"used_bytes": 300 * MEBIBYTE}, None
        if path.endswith("config/disk"):
            return {"size_bytes": GIBIBYTE}, None
        return {"count": 1234}, None

    monkeypatch.setattr(client, "_optional", fake_optional)
    usage = client._project_usage("project-ref", "free")
    database = next(metric for metric in usage["metrics"] if metric["key"] == "database_size")
    storage = next(metric for metric in usage["metrics"] if metric["key"] == "storage_size")
    assert database["percentage"] == 50
    assert storage["limit"] == GIBIBYTE
    assert usage["unavailable"] == []
