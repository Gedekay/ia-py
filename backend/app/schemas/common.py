from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)