from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core import auth
from app.core.config import Settings


def test_supabase_es256_token_uses_project_jwks(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "https://project.supabase.co/auth/v1",
            "aud": "authenticated",
            "sub": "00000000-0000-0000-0000-000000000001",
            "email": "admin@example.com",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )

    class SigningKey:
        key = private_key.public_key()

    class JwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SigningKey()

    monkeypatch.setattr(auth, "_supabase_jwks_client", lambda _url: JwksClient())
    payload = auth._decode_supabase_token(token, Settings(supabase_url="https://project.supabase.co"))

    assert payload["email"] == "admin@example.com"
    assert payload["aud"] == "authenticated"
