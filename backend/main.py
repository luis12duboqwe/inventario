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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.routing import APIRoute
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def _import_module_with_fallback(module_name: str, candidate_path: Path) -> object:
    """Importa ``module_name`` con una ruta alternativa si el paquete no existe."""

    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if not candidate_path.exists():
            raise

        spec = importlib.util.spec_from_file_location(module_name, candidate_path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensivo
            raise ModuleNotFoundError(
                f"No se pudo preparar el cargador para {module_name}."
            ) from exc

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("softmobile.bootstrap")


class Settings(BaseSettings):
    """Configuración base del backend Softmobile 2025 v2.2.0."""

    db_path: str = "database/softmobile.db"
    api_port: int = 8000
    debug: bool = True
    secret_key: str | None = None
    access_token_expire_minutes: int | None = None

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )


settings = Settings()
BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ROOT_DIR: Final[Path] = BASE_DIR.parent
FRONTEND_DIST: Final[Path] = ROOT_DIR / "frontend" / "dist"
DATABASE_FILE: Final[Path] = BASE_DIR / settings.db_path
FAVICON_FALLBACK_SVG: Final[str] = dedent(
    """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Softmobile">
        <defs>
            <linearGradient id="sm2025-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#38bdf8" />
                <stop offset="100%" stop-color="#0ea5e9" />
            </linearGradient>
        </defs>
        <rect width="64" height="64" rx="14" fill="#0f172a" />
        <path
            d="M18 42c4.2-9.6 10.4-14.4 18.6-14.4 4.2 0 7.6 1 10.8 3.4l-4.4 4.6c-2-1.6-3.8-2.2-6.2-2.2-4.6 0-8 2.6-10.2 8h17.4l-2.2 6.6H17z"
            fill="url(#sm2025-gradient)"
        />
        <circle cx="22" cy="20" r="6" fill="#38bdf8" />
    </svg>
    """
).strip()

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

os.environ.setdefault("SOFTMOBILE_DATABASE_URL", f"sqlite:///{DATABASE_FILE}")
if settings.secret_key:
    os.environ.setdefault("SOFTMOBILE_SECRET_KEY", settings.secret_key)
if settings.access_token_expire_minutes is not None:
    os.environ.setdefault(
        "SOFTMOBILE_TOKEN_MINUTES", str(settings.access_token_expire_minutes)
    )

_database_module = _import_module_with_fallback(
    "backend.database", CURRENT_DIR / "database" / "__init__.py"
)

# Utilizamos las utilidades de base de datos centralizadas para asegurar la tabla ``users``.
db_utils_module = _import_module_with_fallback("backend.db", CURRENT_DIR / "db.py")
core_main_module = _import_module_with_fallback(
    "backend.app.main", CURRENT_DIR / "app" / "main.py"
)

init_db = getattr(db_utils_module, "init_db")
create_core_app = getattr(core_main_module, "create_app")

app = create_core_app()


def _discover_modules(package: str, directory: Path) -> Iterable[str]:
    """Devuelve el listado de módulos Python disponibles en ``directory``."""

    for module_path in sorted(directory.glob("*.py")):
        if module_path.name == "__init__.py":
            continue
        yield f"{package}.{module_path.stem}"


def _collect_existing_signatures(target_app: FastAPI) -> set[tuple[str, str]]:
    """Obtiene las firmas (ruta, método) ya registradas en la aplicación."""

    signatures: set[tuple[str, str]] = set()
    for route in target_app.router.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = route.methods or {"GET"}
        for method in methods:
            signatures.add((route.path, method.upper()))
    return signatures


def _include_routers(target_app: FastAPI) -> None:
    """Importa dinámicamente los routers definidos en ``backend.routes``."""

    routes_dir = BASE_DIR / "routes"
    if not routes_dir.exists():
        LOGGER.warning("El directorio de rutas %s no existe", routes_dir)
        return

    imported = 0
    existing_signatures = _collect_existing_signatures(target_app)
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

        router_signatures: set[tuple[str, str]] = set()
        filtered_routes = []
        for route in list(router.routes):
            if not isinstance(route, APIRoute):
                filtered_routes.append(route)
                continue
            methods = route.methods or {"GET"}
            signature_conflict = False
            for method in methods:
                signature = (route.path, method.upper())
                if signature in existing_signatures:
                    LOGGER.info(
                        "Ruta %s %s ya registrada; se omitirá al montar %s.",
                        method,
                        route.path,
                        module,
                    )
                    signature_conflict = True
                    break
            if signature_conflict:
                continue
            for method in methods:
                router_signatures.add((route.path, method.upper()))
            filtered_routes.append(route)

        if not router_signatures:
            LOGGER.info(
                "Se omitió el router %s porque todas sus rutas ya existían.", module
            )
            continue

        router.routes[:] = filtered_routes
        target_app.include_router(router)
        existing_signatures.update(router_signatures)
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

        favicon_candidates = (
            FRONTEND_DIST / "favicon.ico",
            FRONTEND_DIST / "favicon.svg",
            FRONTEND_DIST / "favicon.png",
        )
        favicon_path = next((path for path in favicon_candidates if path.exists()), None)

        if favicon_path is not None:
            media_type_map = {
                ".ico": "image/x-icon",
                ".svg": "image/svg+xml",
                ".png": "image/png",
            }
            favicon_media_type = media_type_map.get(
                favicon_path.suffix.lower(),
                "application/octet-stream",
            )

            @target_app.get("/favicon.ico", include_in_schema=False)
            async def read_frontend_favicon() -> FileResponse:
                """Devuelve el favicon compilado del frontend."""

                return FileResponse(favicon_path, media_type=favicon_media_type)
        else:

            @target_app.get("/favicon.ico", include_in_schema=False)
            async def read_frontend_favicon_placeholder() -> Response:
                """Evita respuestas 404 cuando el favicon no existe en la compilación."""

                return Response(
                    content=FAVICON_FALLBACK_SVG,
                    media_type="image/svg+xml",
                    status_code=200,
                )
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
        """Entrega un favicon mínimo cuando no existe compilación del frontend."""

        return Response(content=FAVICON_FALLBACK_SVG, media_type="image/svg+xml")


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
    LOGGER.info("Tablas de autenticación verificadas/creadas en %s", DATABASE_FILE)

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
