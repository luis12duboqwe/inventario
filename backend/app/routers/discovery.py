"""Endpoints para facilitar la detección del servidor en redes LAN."""
from __future__ import annotations

import ipaddress
import logging
import socket
from pathlib import Path

from fastapi import APIRouter
from sqlalchemy.engine.url import make_url

from .. import schemas
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _detect_lan_host() -> str:
    if settings.lan_advertised_host:
        return settings.lan_advertised_host
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            return str(ipaddress.ip_address(local_ip))
    except OSError:
        return "127.0.0.1"


def _resolve_port() -> int:
    return int(settings.lan_advertised_port or 8000)


def _summarize_database() -> schemas.LanDatabaseSummary:
    try:
        parsed = make_url(settings.database_url)
    except Exception as exc:
        logger.warning(
            f"Error al analizar URL de base de datos para discovery: {exc}",
            exc_info=True
        )
        return schemas.LanDatabaseSummary(
            engine="desconocido",
            location="sin datos",
            writable=False,
            shared_over_lan=False,
        )

    engine = parsed.get_backend_name() or "desconocido"
    if engine.startswith("sqlite"):
        location = parsed.database or "memoria"
        display_path = location
        is_memory = "memory" in str(location).lower()
        try:
            display_path = str(Path(location).resolve())
        except (TypeError, OSError):
            display_path = location
        return schemas.LanDatabaseSummary(
            engine="sqlite",
            location=display_path,
            writable=not is_memory,
            shared_over_lan=not is_memory,
        )

    host = parsed.host or "localhost"
    database = parsed.database or ""
    label = host if not database else f"{host}/{database}"
    return schemas.LanDatabaseSummary(
        engine=engine,
        location=label,
        writable=True,
        shared_over_lan=True,
    )


@router.get("/lan", response_model=schemas.LanDiscoveryResponse)
def discover_lan_server() -> schemas.LanDiscoveryResponse:  # noqa: ANN201
    """Entrega pistas de conexión para terminales dentro de la LAN."""

    host = _detect_lan_host()
    port = _resolve_port()
    protocol = "http"
    database_summary = _summarize_database()

    api_base_url = f"{protocol}://{host}:{port}/api"
    notes: list[str] = []

    if not settings.lan_discovery_enabled:
        notes.append(
            "El administrador desactivó el descubrimiento automático; habilita SOFTMOBILE_LAN_DISCOVERY_ENABLED=1 para compartir la ruta.",
        )

    if database_summary.engine == "sqlite":
        notes.append(
            "SQLite se comparte desde el servidor; mantén el archivo en una carpeta accesible para copias de seguridad locales.",
        )
    else:
        notes.append(
            "PostgreSQL puede residir en el mismo host LAN; expón sólo la interfaz interna y usa credenciales locales.",
        )

    return schemas.LanDiscoveryResponse(
        enabled=settings.lan_discovery_enabled,
        host=host,
        port=port,
        protocol=protocol,
        api_base_url=api_base_url,
        database=database_summary,
        notes=notes,
    )
