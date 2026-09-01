from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PWA Autonomía Económica Femenina"
    app_env: str = "development"
    database_url: str = (
        "mysql+pymysql://pwa_app:change_me@localhost:3306/"
        "pwa_autonomia?charset=utf8mb4"
    )
    content_encryption_key: str = "replace-with-a-fernet-key"
    jwt_secret: str = "replace-with-at-least-32-random-characters"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    access_token_ttl_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    audio_max_retention_hours: int = Field(default=24, ge=1, le=24)
    soft_delete_purge_days: int = Field(default=30, ge=1, le=90)
    audit_retention_days: int = Field(default=365, ge=90, le=730)
    security_log_retention_days: int = Field(default=90, ge=30, le=365)
    default_currency: str = "BOB"
    default_timezone: str = "America/La_Paz"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
