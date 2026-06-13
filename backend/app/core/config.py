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
    frontend_dist_dir: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
