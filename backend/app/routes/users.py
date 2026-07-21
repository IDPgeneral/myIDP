from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.db.models import User
from app.db.session import get_db
from app.schemas.inputs import UserCreate, UserPatch
from app.services.audit import audit

router = APIRouter(tags=["users"])


@router.get("/users")
def list_users(_: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    users = db.scalars(select(User).order_by(User.email)).all()
    return [{"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role, "active": user.active, "last_login_at": user.last_login_at, "created_at": user.created_at} for user in users]


@router.post("/users", status_code=201)
def create_user(payload: UserCreate, current: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Usuário já cadastrado.")
    user = User(email=email, display_name=payload.display_name, role=payload.role, active=payload.active)
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, action="user.create", user=current, after_data={"email": email, "role": user.role, "active": user.active}, success=True)
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role, "active": user.active}


@router.patch("/users/{user_id}")
def patch_user(user_id: str, payload: UserPatch, current: Annotated[CurrentUser, Depends(require_roles("admin"))], db: Annotated[Session, Depends(get_db)]):
    user = db.get(User, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    audit(db, action="user.update", user=current, after_data=payload.model_dump(exclude_unset=True), success=True)
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role, "active": user.active}
