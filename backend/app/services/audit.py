from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.logging import correlation_id_var, sanitize_payload
from app.db.models import AuditLog


def audit(
    db: Session,
    *,
    action: str,
    user: CurrentUser | None = None,
    product_id: str | None = None,
    provider_account_id: str | None = None,
    resource_id: str | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    success: bool,
    error: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=uuid.UUID(user.id) if user and user.id.count("-") == 4 else None,
        product_id=uuid.UUID(product_id) if product_id else None,
        provider_account_id=uuid.UUID(provider_account_id) if provider_account_id else None,
        resource_id=uuid.UUID(resource_id) if resource_id else None,
        action=action,
        before_data=sanitize_payload(before_data) if before_data else None,
        after_data=sanitize_payload(after_data) if after_data else None,
        success=success,
        error=error,
        correlation_id=correlation_id_var.get() or None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
