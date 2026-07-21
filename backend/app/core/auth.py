from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import correlation_id_var
from app.db.models import AuditLog, User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    role: str
    display_name: str | None = None


def _audit_login(db: Session, user: User | None, success: bool, error: str | None = None) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action="login",
            success=success,
            error=error,
            correlation_id=correlation_id_var.get() or None,
        )
    )
    db.commit()


@lru_cache(maxsize=4)
def _supabase_jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json", lifespan=600)


def _decode_supabase_token(token: str, settings: Settings) -> dict:
    try:
        if settings.supabase_url:
            issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
            signing_key = _supabase_jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["exp", "sub"]},
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Autenticação do IDP não configurada.")
    except HTTPException:
        raise
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida ou expirada.") from exc


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_idp_test_email: Annotated[str | None, Header()] = None,
    x_idp_test_role: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if settings.app_env == "test" and x_idp_test_email:
        return CurrentUser(id="00000000-0000-0000-0000-000000000001", email=x_idp_test_email, role=x_idp_test_role or "viewer")

    if settings.auth_disabled:
        user = CurrentUser(id="public", email="acesso-direto", role="admin", display_name="Acesso direto")
        request.state.current_user = user
        return user

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória.")

    payload = _decode_supabase_token(credentials.credentials, settings)
    email = str(payload.get("email") or payload.get("user_metadata", {}).get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem e-mail autorizado.")

    user = db.scalar(select(User).where(User.email == email))
    if user is None and email in settings.admin_email_set:
        user = User(email=email, display_name=payload.get("user_metadata", {}).get("full_name"), role="admin", active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    if user is None or not user.active:
        _audit_login(db, user, False, "E-mail não autorizado.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="E-mail não autorizado para este portal.")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    request.state.current_user = user
    return CurrentUser(id=str(user.id), email=user.email, role=user.role, display_name=user.display_name)


def require_roles(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente.")
        return user

    return dependency
