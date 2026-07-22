from __future__ import annotations

import asyncio
import time
from typing import Any

import jwt
from mcp.server.auth.provider import AccessToken

from app.core.auth import _supabase_jwks_client
from app.core.config import Settings


class SupabaseMCPTokenVerifier:
    """Validate Supabase OAuth access tokens and restrict access to IDP admins."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = await asyncio.to_thread(self._decode, token)
        except (jwt.PyJWTError, ValueError):
            return None

        email = str(payload.get("email") or "").strip().lower()
        if not email or email not in self.settings.admin_email_set:
            return None
        client_id = str(payload.get("client_id") or "").strip()
        subject = str(payload.get("sub") or payload.get("user_id") or "").strip()
        if not client_id or not subject:
            return None
        scopes = self._scopes(payload)
        if not {"openid", "email"}.issubset(scopes):
            return None
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int) or expires_at <= int(time.time()):
            return None
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=sorted(scopes),
            expires_at=expires_at,
            resource=self.settings.effective_mcp_resource_url,
            subject=subject,
            claims={"email": email},
        )

    def _decode(self, token: str) -> dict[str, Any]:
        signing_key = _supabase_jwks_client(self.settings.supabase_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=["authenticated", self.settings.effective_mcp_resource_url],
            issuer=self.settings.supabase_auth_issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
        )

    @staticmethod
    def _scopes(payload: dict[str, Any]) -> set[str]:
        raw = payload.get("scope") or payload.get("scopes") or ""
        if isinstance(raw, str):
            return {value for value in raw.split() if value}
        if isinstance(raw, list):
            return {str(value) for value in raw if value}
        return set()
