"""Application configuration for Softmobile."""
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Global configuration values loaded from environment variables."""

    project_name: str = "Softmobile Inventory API"
    api_v1_str: str = "/api/v1"
    sqlite_db_file: Path = Field(default=Path("softmobile.db"), description="Archivo SQLite local")
    enable_bundles: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_BUNDLES", "SOFTMOBILE_ENABLE_BUNDLES"),
        description="Activa el manejo de paquetes y combos vinculados al inventario.",
    )
    enable_dte: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_DTE", "SOFTMOBILE_ENABLE_DTE"),
        description="Habilita la emisión de documentos tributarios electrónicos (DTE).",
    )
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "SOFTMOBILE_DATABASE_URL",
            "softmobile_database_url",
        ),
        description="Cadena de conexión proporcionada por el entorno.",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Return the SQLAlchemy connection string for the local database."""

        if self.database_url:
            return self.database_url

        sqlite_path = self.sqlite_db_file
        if not sqlite_path.is_absolute():
            sqlite_path = (Path.cwd() / sqlite_path).resolve()

        return URL.create("sqlite", database=str(sqlite_path)).render_as_string(
            hide_password=False
        )

    class Config:
        env_prefix = "softmobile_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
