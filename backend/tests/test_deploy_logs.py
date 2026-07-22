from __future__ import annotations

import pytest

from app.core.config import Settings
from app.db.models import Product, ProductResource, ProviderAccount
from app.integrations.render.client import RenderClient
from app.services.deploy_logs import DeployLogReader


def _seed_render_service(db):
    product = Product(name="MILU", slug="milu-software", owner="owner", status="unknown")
    db.add(product)
    db.flush()
    account = ProviderAccount(
        provider="render",
        name="render-milu",
        product_id=product.id,
        credential_ref="RENDER_API_KEY_MILU",
        status="connected",
        connection_status="connected",
    )
    db.add(account)
    db.flush()
    resource = ProductResource(
        product_id=product.id,
        provider_account_id=account.id,
        resource_type="render_service",
        external_id="srv-test",
        name="backend",
        environment="production",
        active=True,
    )
    db.add(resource)
    db.commit()


def test_list_products_returns_only_catalog_aliases(db):
    _seed_render_service(db)
    result = DeployLogReader(db, Settings(app_env="test", database_url="sqlite://")).list_products()

    assert result == {
        "products": [{"slug": "milu-software", "name": "MILU", "services": ["backend"]}],
        "read_only": True,
    }


def test_get_latest_deploy_logs_uses_bound_service_and_redacts_secrets(db, monkeypatch):
    _seed_render_service(db)
    monkeypatch.setenv("RENDER_API_KEY_MILU", "render-secret")
    captured = {}

    def fake_list_deploys(self, service_id, *, limit=10):
        assert self.api_key == "render-secret"
        assert service_id == "srv-test"
        return [
            {
                "deploy": {
                    "id": "dep-abc123",
                    "status": "build_failed",
                    "createdAt": "2026-07-22T12:00:00Z",
                    "startedAt": "2026-07-22T12:01:00Z",
                    "finishedAt": "2026-07-22T12:03:00Z",
                    "commit": {"id": "abc", "message": "fix build"},
                }
            }
        ]

    def fake_retrieve_service(self, service_id):
        assert service_id == "srv-test"
        return {"id": service_id, "ownerId": "tea-owner"}

    def fake_list_logs(self, **kwargs):
        captured.update(kwargs)
        return {
            "hasMore": False,
            "logs": [
                {"timestamp": "2026-07-22T12:02:00Z", "message": "DATABASE_URL=postgresql://u:p@db/x"},
                {"timestamp": "2026-07-22T12:02:01Z", "message": "Authorization: Bearer abc.def.ghi"},
            ],
        }

    monkeypatch.setattr(RenderClient, "list_deploys", fake_list_deploys)
    monkeypatch.setattr(RenderClient, "retrieve_service", fake_retrieve_service)
    monkeypatch.setattr(RenderClient, "list_logs", fake_list_logs)

    settings = Settings(app_env="test", database_url="sqlite://", mcp_max_log_lines=50)
    result = DeployLogReader(db, settings).get_deploy_logs("MILU-SOFTWARE", "BACKEND", limit=500)

    assert result["deploy"]["id"] == "dep-abc123"
    assert result["read_only"] is True
    assert result["pagination"]["has_more"] is False
    assert result["logs"][0]["message"] == "DATABASE_URL=[REDACTED]"
    assert result["logs"][1]["message"] == "Authorization: Bearer [REDACTED]"
    assert captured["owner_id"] == "tea-owner"
    assert captured["service_id"] == "srv-test"
    assert captured["limit"] == 50
    assert captured["start_time"].isoformat() == "2026-07-22T11:56:00+00:00"
    assert captured["end_time"].isoformat() == "2026-07-22T12:08:00+00:00"


def test_get_deploy_logs_rejects_unbound_service(db):
    _seed_render_service(db)
    reader = DeployLogReader(db, Settings(app_env="test", database_url="sqlite://"))

    with pytest.raises(ValueError, match="Serviço Render não encontrado"):
        reader.get_deploy_logs("milu-software", "frontend")


def test_page_window_accepts_only_cursors_inside_deploy_window():
    from datetime import UTC, datetime

    deploy_start = datetime(2026, 7, 22, 12, tzinfo=UTC)
    deploy_end = datetime(2026, 7, 22, 13, tzinfo=UTC)
    assert DeployLogReader._page_window(
        deploy_start,
        deploy_end,
        page_start_time="2026-07-22T12:15:00Z",
        page_end_time="2026-07-22T12:45:00Z",
    ) == (
        datetime(2026, 7, 22, 12, 15, tzinfo=UTC),
        datetime(2026, 7, 22, 12, 45, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="juntos"):
        DeployLogReader._page_window(deploy_start, deploy_end, page_start_time="2026-07-22T12:15:00Z", page_end_time=None)
    with pytest.raises(ValueError, match="fora"):
        DeployLogReader._page_window(
            deploy_start,
            deploy_end,
            page_start_time="2026-07-22T11:00:00Z",
            page_end_time="2026-07-22T12:15:00Z",
        )


def test_render_list_logs_uses_build_only_filters(monkeypatch):
    client = RenderClient(Settings(app_env="test", database_url="sqlite://"), "token")
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"logs": []}

    monkeypatch.setattr(client, "_request", fake_request)
    from datetime import UTC, datetime

    client.list_logs(
        owner_id="tea-owner",
        service_id="srv-test",
        start_time=datetime(2026, 7, 22, 12, tzinfo=UTC),
        end_time=datetime(2026, 7, 22, 13, tzinfo=UTC),
        text="npm error",
        limit=999,
    )

    assert captured["method"] == "GET"
    assert captured["path"] == "/logs"
    assert captured["params"]["ownerId"] == "tea-owner"
    assert captured["params"]["resource"] == ["srv-test"]
    assert captured["params"]["type"] == ["build"]
    assert captured["params"]["direction"] == "forward"
    assert captured["params"]["text"] == ["npm error"]
    assert captured["params"]["limit"] == 100
