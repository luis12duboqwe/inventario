"""Punto de entrada del backend Softmobile 2025 v2.2.0."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from textwrap import dedent
from typing import Final, Iterable


CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_MODULE_NAME = "backend.database"

_database_spec = importlib.util.find_spec(DATABASE_MODULE_NAME)
if _database_spec is None:
    _database_file = CURRENT_DIR / "database" / "__init__.py"
    if not _database_file.exists():
        msg = (
            "No se encontró el módulo de base de datos esperado en "
            f"{_database_file}."
        )
        raise ModuleNotFoundError(msg)

    _database_spec = importlib.util.spec_from_file_location(
        DATABASE_MODULE_NAME,
        _database_file,
    )
    if _database_spec is None or _database_spec.loader is None:
        msg = "No se pudo preparar el cargador para 'backend.database'."
        raise ModuleNotFoundError(msg)

    _database_module = importlib.util.module_from_spec(_database_spec)
    sys.modules[DATABASE_MODULE_NAME] = _database_module
    _database_spec.loader.exec_module(_database_module)
else:
    _database_module = importlib.import_module(DATABASE_MODULE_NAME)

init_db = getattr(_database_module, "init_db")

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
BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ROOT_DIR: Final[Path] = BASE_DIR.parent
FRONTEND_DIST: Final[Path] = ROOT_DIR / "frontend" / "dist"
DATABASE_FILE: Final[Path] = BASE_DIR / settings.db_path

FALLBACK_FRONTEND_HTML: Final[str] = dedent(
    """
    <!DOCTYPE html>
    <html lang="es">
        <head>
            <meta charset="utf-8" />
            <title>Softmobile 2025 v2.2.0</title>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
                :root {
                    color-scheme: dark;
                    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background: radial-gradient(circle at 20% 20%, #101926, #060a11);
                    color: #e6f1ff;
                }

                body {
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    padding: 2rem;
                }

                .card {
                    background: rgba(12, 24, 38, 0.88);
                    border: 1px solid rgba(0, 173, 238, 0.4);
                    border-radius: 16px;
                    box-shadow: 0 12px 45px rgba(0, 0, 0, 0.45);
                    max-width: 520px;
                    width: 100%;
                    padding: 2.5rem 2rem;
                }

                h1 {
                    margin: 0 0 1rem;
                    font-size: 1.9rem;
                    line-height: 1.2;
                    color: #3dd9ff;
                    text-shadow: 0 0 12px rgba(61, 217, 255, 0.65);
                }

                p {
                    margin: 0 0 1.25rem;
                    font-size: 1rem;
                    line-height: 1.6;
                    color: rgba(230, 241, 255, 0.92);
                }

                code {
                    font-family: 'Fira Code', Consolas, 'Courier New', monospace;
                    background: rgba(0, 173, 238, 0.08);
                    border-radius: 6px;
                    padding: 0.15rem 0.35rem;
                    color: #7ee8ff;
                }
            </style>
        </head>
        <body>
            <main class="card">
                <h1>Softmobile 2025 v2.2.0</h1>
                <p>
                    La compilación del frontend aún no está disponible en esta instancia.
                    Para acceder a la interfaz completa ejecuta
                    <code>npm --prefix frontend run build</code> y vuelve a iniciar el
                    servidor. Mientras tanto puedes interactuar con la API mediante la
                    ruta <code>/api</code> o la documentación interactiva en
                    <code>/docs</code>.
                </p>
                <p>
                    Si este entorno es de desarrollo recuerda mantener compatibilidad
                    total con Softmobile 2025 v2.2.0 sin modificar la versión declarada.
                </p>
            </main>
        </body>
    </html>
    """
).strip()

app = FastAPI(title="Softmobile 2025 API", version="v2.2.0", debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _discover_modules(package: str, directory: Path) -> Iterable[str]:
    """Devuelve el listado de módulos Python disponibles en ``directory``."""

    for module_path in sorted(directory.glob("*.py")):
        if module_path.name == "__init__.py":
            continue
        yield f"{package}.{module_path.stem}"


def _include_routers(target_app: FastAPI) -> None:
    """Importa dinámicamente los routers definidos en ``backend.routes``."""

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
        LOGGER.warning(
            "No se montó ninguna ruta personalizada en la API principal",
        )


def _ensure_database_file(database_path: Path) -> None:
    """Crea el archivo SQLite si no existe previamente."""

    if database_path.exists():
        return

    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch()
    LOGGER.info("Se creó la base de datos SQLite en %s", database_path)


def _validate_database_connection(database_path: Path) -> None:
    """Valida que la base de datos SQLite sea accesible."""

    try:
        engine = create_engine(f"sqlite:///{database_path}")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:  # pragma: no cover - validación de arranque
        LOGGER.error(
            "No fue posible validar la base de datos SQLite: %s",
            exc,
        )


def _mount_frontend(target_app: FastAPI) -> None:
    """Monta la compilación del frontend si está disponible."""

    if FRONTEND_DIST.exists():
        target_app.mount(
            "/",
            StaticFiles(directory=FRONTEND_DIST, html=True),
            name="frontend",
        )
        LOGGER.info("Frontend montado desde %s", FRONTEND_DIST)
        return

    LOGGER.info(
        "No se encontró compilación del frontend; se habilitará una vista de respaldo"
    )

    @target_app.get("/", include_in_schema=False)
    async def read_fallback_frontend() -> HTMLResponse:
        """Devuelve un panel informativo cuando el frontend no está compilado."""

        return HTMLResponse(content=FALLBACK_FRONTEND_HTML)

    @target_app.get("/favicon.ico", include_in_schema=False)
    async def read_favicon_placeholder() -> Response:
        """Evita respuestas 404 para el favicon por defecto."""

        return Response(status_code=204)


@app.get("/api", tags=["estado"])
async def read_status() -> dict[str, str]:
    """Devuelve el estado base de la API para verificaciones rápidas."""

    return {"message": "API online ✅ - Softmobile 2025 v2.2.0"}


@app.on_event("startup")
async def bootstrap_environment() -> None:
    """Prepara el entorno mínimo requerido para ejecutar el backend."""

    _ensure_database_file(DATABASE_FILE)
    _validate_database_connection(DATABASE_FILE)
    init_db()

    for directory_name in ("models", "routes"):
        directory_path = BASE_DIR / directory_name
        if not directory_path.exists():
            LOGGER.warning(
                "Directorio %s no encontrado; verifica la configuración de %s.",
                directory_path,
                directory_name,
            )

    _mount_frontend(app)


def get_application() -> FastAPI:
    """Permite obtener la instancia principal de FastAPI."""

    return app


_include_routers(app)

__all__ = ["app", "get_application", "settings"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=settings.api_port,
        reload=settings.debug,
    )
