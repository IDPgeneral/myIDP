from app.core.config import Settings
from app.integrations.render.client import RenderClient
from app.schemas.common import ActionConfirmation


def test_trigger_deploy_accepts_commit_and_clear_cache(monkeypatch):
    client = RenderClient(Settings(app_env="test", database_url="sqlite://"), "token")
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return {"id": "dep-test", "status": "queued"}

    monkeypatch.setattr(client, "_request", fake_request)
    result = client.trigger_deploy("srv-test", commit_id="abcdef1234567", clear_cache=True)

    assert result == {"id": "dep-test", "status": "queued"}
    assert captured == {
        "method": "POST",
        "path": "/services/srv-test/deploys",
        "json": {"clearCache": "clear", "commitId": "abcdef1234567"},
    }


def test_trigger_deploy_defaults_to_latest_commit_without_cache_clear(monkeypatch):
    client = RenderClient(Settings(app_env="test", database_url="sqlite://"), "token")
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(client, "_request", fake_request)
    client.trigger_deploy("srv-test")

    assert captured["json"] == {"clearCache": "do_not_clear"}


def test_action_confirmation_validates_commit_options():
    payload = ActionConfirmation(confirmation="CONFIRMAR", commit_id="abcdef1", clear_cache=True)
    assert payload.commit_id == "abcdef1"
    assert payload.clear_cache is True
