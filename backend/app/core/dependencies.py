from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import Role, User
from app.storage.minio_client import get_minio_client


bearer_scheme = HTTPBearer(auto_error=True)
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise ForbiddenError("Jeton d'accès invalide.") from error
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise ForbiddenError("Compte désactivé ou introuvable.")
    return user


def require_role(roles: list[Role]) -> Callable[..., User]:
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


def get_minio() -> Minio:
    return get_minio_client()


def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)