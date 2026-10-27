from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings


password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=expires_minutes or get_settings().access_token_expire_minutes)
    return jwt.encode({**data, "iat": now, "exp": expires, "type": "access"}, get_settings().jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=get_settings().refresh_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": expires, "type": "refresh"}, get_settings().jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(token, get_settings().jwt_secret.get_secret_value(), algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Type de jeton invalide.")
    return payload