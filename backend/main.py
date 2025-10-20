"""Creado por Codex el 2025-10-20."""

from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("softmobile.bootstrap")


class Settings(BaseSettings):
    """Configuración base del backend Softmobile 2025 v2.2.0."""

    db_path: str = "database/softmobile.db"
    api_port: int = 8000
    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

app = FastAPI(title="Softmobile 2025", debug=settings.debug)

"""Creado por Codex el 2025-10-20 como punto de entrada base para Softmobile 2025 v2.2.0."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.staticfiles import StaticFiles

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
FRONTEND_DIST: Final[Path] = BASE_DIR.parent / "frontend" / "dist"
DATABASE_FILE: Final[Path] = BASE_DIR / "database" / "softmobile.db"
LOGGER = logging.getLogger("softmobile.bootstrap")

app = FastAPI(title="Softmobile 2025 API", version="v2.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def api_status() -> dict[str, str]:
    """Expone el estado básico del API."""

    return {"message": "API online ✅ - Softmobile 2025 v2.2.0"}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    LOGGER.warning("No se encontró el directorio de frontend en %s", FRONTEND_DIST)


def _discover_modules(package: str, directory: Path) -> Iterable[str]:
    for module_path in sorted(directory.glob("*.py")):
        if module_path.name == "__init__.py":
            continue
        yield f"{package}.{module_path.stem}"

def _include_routers(target_app: FastAPI) -> None:
    routes_dir = BASE_DIR / "routes"
    if not routes_dir.exists():
        LOGGER.warning("El directorio de rutas %s no existe", routes_dir)
        return

    imported = 0
    for module in _discover_modules("backend.routes", routes_dir):
        try:
            router_module = importlib.import_module(module)
        except ModuleNotFoundError:  # pragma: no cover - inicialización dinámica
            LOGGER.warning("No se pudo importar el módulo de rutas %s", module)
            continue

        router = getattr(router_module, "router", None)
        if router is None:
            LOGGER.warning("El módulo %s no define un objeto 'router'", module)
            continue

        target_app.include_router(router)
        imported += 1

    if imported == 0:
        LOGGER.warning("No se montó ninguna ruta personalizada en la API principal")


_include_routers(app)


def _ensure_database_file() -> None:
    database_path = BASE_DIR / settings.db_path
    if not database_path.exists():
        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_path.touch()
        LOGGER.info("Se creó la base de datos SQLite en %s", database_path)


_ensure_database_file()

MODELS_DIR = BASE_DIR / "models"
if not any(MODELS_DIR.glob("*.py")):
    LOGGER.warning("No se encontraron modelos definidos en %s", MODELS_DIR)


__all__ = ["app", "settings"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=settings.api_port,
        reload=settings.debug,
    )
@app.get("/api", tags=["estado"])
async def read_status() -> dict[str, str]:
    """Devuelve el estado base de la API para verificaciones rápidas."""
    return {"message": "API online ✅ - Softmobile 2025 v2.2.0"}


@app.on_event("startup")
async def bootstrap_environment() -> None:
    """Prepara la carpeta de base de datos y registra advertencias operativas."""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATABASE_FILE.exists():
        DATABASE_FILE.touch()
        LOGGER.info("Base de datos SQLite inicial creada en %s", DATABASE_FILE)
    try:
        engine = create_engine(f"sqlite:///{DATABASE_FILE}")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:  # pragma: no cover - validación de arranque
        LOGGER.error("No fue posible validar la base de datos SQLite: %s", exc)
    for directory_name in ("models", "routes"):
        directory_path = BASE_DIR / directory_name
        if not directory_path.exists():
            LOGGER.warning(
                "Directorio %s no encontrado; verifica la configuración de %s.",
                directory_path,
                directory_name,
            )
    if FRONTEND_DIST.exists():
        app.mount(
            "/",
            StaticFiles(directory=FRONTEND_DIST, html=True),
            name="frontend",
        )
        LOGGER.info("Frontend montado desde %s", FRONTEND_DIST)
    else:
        LOGGER.warning(
            "No se encontró la carpeta de compilación del frontend en %s.",
            FRONTEND_DIST,
        )


def get_application() -> FastAPI:
    """Permite obtener la instancia principal de FastAPI."""
    return app


__all__ = ["app", "get_application"]
