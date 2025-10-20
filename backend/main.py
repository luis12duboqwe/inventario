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
