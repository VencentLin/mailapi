from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MailAPI"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://mailapi:mailapi@localhost:5432/mailapi"
    redis_url: str = "redis://localhost:6379/0"
    run_migrations: bool = False
    secret_key: str = "change-me"
    token_encryption_key: str = "change-me-encryption-key"
    access_token_expire_minutes: int = 60 * 24
    init_admin_username: str | None = None
    init_admin_password: str | None = None
    init_admin_email: str | None = None
    frontend_dist_dir: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
