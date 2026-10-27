from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.user import Role
from app.schemas.common import ORMModel


class UserCreate(ORMModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    full_name: str = Field(min_length=2, max_length=200)
    role: Role = Role.ENQUETEUR


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


class UserRoleUpdate(ORMModel):
    role: Role