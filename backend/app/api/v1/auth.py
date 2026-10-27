from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.dependencies import DbSession, get_current_user, get_redis
from app.core.exceptions import ForbiddenError
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.audit import log_action


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise ForbiddenError("Identifiants invalides.")
    user.last_login_at = datetime.now(UTC)
    await log_action(db, user, "LOGIN", "user", user.id, request.client.host if request.client else None)
    await db.commit()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id), "role": user.role.value}),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = UUID(str(claims["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise ForbiddenError("Jeton de renouvellement invalide.") from error
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise ForbiddenError("Compte désactivé ou introuvable.")
    redis = get_redis()
    try:
        token_hash = sha256(payload.refresh_token.encode()).hexdigest()
        if await redis.exists(f"revoked:{token_hash}"):
            raise ForbiddenError("Jeton de renouvellement révoqué.")
    finally:
        await redis.aclose()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user_id), "role": user.role.value}),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest) -> None:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.InvalidTokenError as error:
        raise ForbiddenError("Jeton de renouvellement invalide.") from error
    expires_in = max(int(claims["exp"] - datetime.now(UTC).timestamp()), 1)
    redis = get_redis()
    try:
        token_hash = sha256(payload.refresh_token.encode()).hexdigest()
        await redis.setex(f"revoked:{token_hash}", expires_in, "1")
    finally:
        await redis.aclose()


@router.get("/me", response_model=UserRead)
async def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user