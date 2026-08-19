from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Product Control API"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # RabbitMQ
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    # Redis (кэш, отдельная БД от celery result backend — там /1)
    REDIS_URL: str

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool

    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    CORS_ORIGINS: list[str] = ["*"]

    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore


settings = get_settings()
