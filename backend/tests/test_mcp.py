from __future__ import annotations

import asyncio
import time

from mcp.server.auth.provider import AccessToken
from starlette.testclient import TestClient

from app.core.config import Settings
from app.mcp.auth import SupabaseMCPTokenVerifier
from app.mcp.server import build_mcp_server


class FakeTokenVerifier:
    async def verify_token(self, token: str) -> AccessToken | None:
        return AccessToken(
            token=token,
            client_id="chatgpt",
            scopes=["openid", "email"],
            expires_at=int(time.time()) + 600,
            resource="https://idp.example.com/mcp",
            subject="user-1",
        )


def _settings(**overrides):
    values = {
        "app_env": "test",
        "database_url": "sqlite://",
        "backend_url": "https://idp.example.com",
        "supabase_url": "https://project.supabase.co",
        "allowed_admin_emails": "admin@example.com",
        "mcp_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_mcp_exposes_only_three_read_only_tools():
    server = build_mcp_server(_settings(), token_verifier=FakeTokenVerifier())
    tools = asyncio.run(server.list_tools())

    assert [tool.name for tool in tools] == ["list_products", "list_deploys", "get_deploy_logs"]
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is False


def test_mcp_http_publishes_oauth_metadata_and_rejects_anonymous_requests():
    settings = _settings(backend_url="http://testserver")
    server = build_mcp_server(settings, token_verifier=FakeTokenVerifier())
    with TestClient(server.streamable_http_app()) as client:
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        unauthorized = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream", "content-type": "application/json"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            },
        )
        authorized_headers = {
            "authorization": "Bearer valid",
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }
        initialized = client.post(
            "/mcp",
            headers=authorized_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            },
        )
        tools = client.post(
            "/mcp",
            headers={**authorized_headers, "mcp-protocol-version": "2025-11-25"},
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
        )

    assert metadata.status_code == 200
    assert metadata.json() == {
        "resource": "http://testserver/mcp",
        "authorization_servers": ["https://project.supabase.co/auth/v1"],
        "scopes_supported": ["openid", "email"],
        "bearer_methods_supported": ["header"],
    }
    assert unauthorized.status_code == 401
    assert "resource_metadata=" in unauthorized.headers["www-authenticate"]
    assert initialized.status_code == 200
    assert tools.status_code == 200
    assert [tool["name"] for tool in tools.json()["result"]["tools"]] == ["list_products", "list_deploys", "get_deploy_logs"]


def test_mcp_requires_oauth_configuration():
    try:
        build_mcp_server(_settings(supabase_url=""), token_verifier=FakeTokenVerifier())
    except ValueError as exc:
        assert "SUPABASE_URL" in str(exc)
    else:
        raise AssertionError("MCP should reject missing Supabase OAuth configuration")


def test_supabase_token_verifier_accepts_only_allowed_admin(monkeypatch):
    settings = _settings()
    verifier = SupabaseMCPTokenVerifier(settings)
    payload = {
        "email": "admin@example.com",
        "client_id": "chatgpt-client",
        "sub": "user-1",
        "scope": "openid email profile",
        "exp": int(time.time()) + 600,
    }
    monkeypatch.setattr(verifier, "_decode", lambda _: payload)

    access = asyncio.run(verifier.verify_token("token"))

    assert access is not None
    assert access.client_id == "chatgpt-client"
    assert access.scopes == ["email", "openid", "profile"]
    assert access.claims == {"email": "admin@example.com"}

    payload["email"] = "other@example.com"
    assert asyncio.run(verifier.verify_token("token")) is None
