from functools import lru_cache
import json
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SAAJD"
    env: str = "development"
    database_url: str = "postgresql+asyncpg://saajd:saajd@localhost:5432/saajd"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: SecretStr = SecretStr("development-only-change-this-secret-32-chars")
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_minutes: int = Field(default=10080, gt=0)
    max_garde_a_vue_hours: int = Field(default=48, gt=0)
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "saajd"
    minio_secret_key: SecretStr = SecretStr("replace-me")
    minio_bucket: str = "saajd-documents"
    minio_secure: bool = False
    llm_provider: str = "none"
    llm_api_key: SecretStr | None = None
    llm_model: str = ""
    llm_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    enable_docs: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not isinstance(parsed, list) or not all(isinstance(origin, str) for origin in parsed):
            raise ValueError("CORS_ORIGINS doit être une liste JSON ou une liste séparée par des virgules.")
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()