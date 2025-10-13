"""Application configuration for Softmobile."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global configuration values loaded from environment variables."""

    project_name: str = "Softmobile Inventory API"
    api_v1_str: str = "/api/v1"
    sqlite_db_file: Path = Field(default=Path("softmobile.db"), description="Archivo SQLite local")

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Return the SQLAlchemy connection string for the local database."""
        return f"sqlite:///{self.sqlite_db_file}"

    class Config:
        env_prefix = "softmobile_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
