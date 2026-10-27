from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = ["http://localhost:3000"]
    enable_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()