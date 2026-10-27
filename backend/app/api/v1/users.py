from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.core.dependencies import DbSession, require_role
from app.core.exceptions import NotFoundError
from app.core.security import hash_password
from app.models.user import Role, User
from app.schemas.user import UserCreate, UserRead, UserRoleUpdate, UserUpdate
from app.services.audit import log_action


router = APIRouter(prefix="/users", tags=["users"])
AdminUser = Annotated[User, Depends(require_role([Role.ADMIN]))]


@router.get("", response_model=list[UserRead])
async def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(await db.scalars(select(User).order_by(User.created_at.desc())))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: DbSession, admin: AdminUser) -> User:
    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await log_action(db, admin, "USER_CREATED", "user", user.id)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_role(user_id: UUID, payload: UserRoleUpdate, db: DbSession, admin: AdminUser) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")
    user.role = payload.role
    await log_action(db, admin, "USER_ROLE_UPDATED", "user", user.id)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: UUID, payload: UserUpdate, db: DbSession, admin: AdminUser) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await log_action(db, admin, "USER_UPDATED", "user", user.id)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(user_id: UUID, db: DbSession, admin: AdminUser) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")
    user.is_active = False
    await log_action(db, admin, "USER_DEACTIVATED", "user", user.id)
    await db.commit()