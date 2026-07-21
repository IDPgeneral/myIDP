from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.db.models import HealthCheck
from app.db.session import get_db
from app.services.audit import audit
from app.services.health import HealthCheckService
from app.services.status import latest_health_results

router = APIRouter(tags=["health"])


@router.get("/products/{product_id}/health")
def product_health(product_id: str, _: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    return latest_health_results(db, product_id)


@router.post("/health-checks/{check_id}/run")
def run_health_check(check_id: str, user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    check = db.get(HealthCheck, uuid.UUID(check_id))
    if check is None or not check.active:
        raise HTTPException(status_code=404, detail="Health check não encontrado ou inativo.")
    result = HealthCheckService(db).run(check)
    audit(db, action="health_check.run", user=user, product_id=str(check.product_id), resource_id=str(check.resource_id) if check.resource_id else None, after_data={"status": result.status, "http_status": result.http_status, "response_time_ms": result.response_time_ms}, success=result.status == "healthy")
    return {"id": str(result.id), "status": result.status, "http_status": result.http_status, "response_time_ms": result.response_time_ms, "message": result.message, "checked_at": result.checked_at}
