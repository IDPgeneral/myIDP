from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.core.config import Settings, get_settings
from app.core.logging import sanitized_error
from app.db.session import get_db
from app.services.audit import audit
from app.services.catalog import import_catalog_directory, load_catalog_file

router = APIRouter(tags=["catalog"])


@router.post("/catalog/import")
def import_catalog(user: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    try:
        result = import_catalog_directory(db, settings.catalog_directory)
        audit(db, action="catalog.import", user=user, after_data=result, success=True)
        return {"status": "success", "files": result}
    except Exception as exc:
        error = sanitized_error(exc)
        audit(db, action="catalog.import", user=user, success=False, error=error)
        raise HTTPException(status_code=422, detail=error) from exc


@router.get("/catalog/validate")
def validate_catalog(_: Annotated[CurrentUser, Depends(require_roles("admin"))], settings: Annotated[Settings, Depends(get_settings)]):
    base = Path(settings.catalog_directory).resolve()
    results = []
    for path in sorted(base.glob("*.yaml")):
        try:
            document = load_catalog_file(path)
            results.append({"file": path.name, "valid": True, "product": document.metadata.name})
        except Exception as exc:
            results.append({"file": path.name, "valid": False, "error": sanitized_error(exc)})
    return results
