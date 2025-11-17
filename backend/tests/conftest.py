from __future__ import annotations

import os
from collections.abc import Iterator
from urllib.parse import urlsplit
import tempfile

from typing import Callable, Generator, Any

# Configurar variables de entorno ANTES de cualquier importación del backend
# para evitar errores de validación en Settings()
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "[\"http://testserver\"]")
# // [PACK28-tests]
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("SOFTMOBILE_BOOTSTRAP_TOKEN", "test-bootstrap-token")

# Ahora sí importar desde el backend después de configurar el entorno
from backend.app.main import create_app
from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)
from backend.app.database import Base, create_engine_from_url, get_db, engine as app_engine
from backend.app.config import settings
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
import pytest


pytest.importorskip(
    "fastapi",
    reason="La suite backend requiere fastapi para instanciar la aplicación de pruebas.",
)


@pytest.fixture(scope="session")
def db_engine() -> Iterator:
    """Crea un motor de base de datos aislado para toda la sesión de pruebas."""

    test_url = os.getenv("SOFTMOBILE_TEST_DATABASE", "sqlite:///:memory:")
    engine = create_engine_from_url(test_url)

    Base.metadata.create_all(bind=engine)
    with engine.connect() as setup_connection:
        create_valor_inventario_view(setup_connection)
        create_movimientos_inventario_view(setup_connection)

    try:
        yield engine
    finally:
        with engine.connect() as teardown_connection:
            drop_movimientos_inventario_view(teardown_connection)
            drop_valor_inventario_view(teardown_connection)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    """Entrega una sesión limpia por prueba reconstruyendo el esquema."""

    connection = db_engine.connect()

    def _reset_database_schema() -> None:
        try:
            drop_movimientos_inventario_view(connection)
        except Exception:
            connection.rollback()
        try:
            drop_valor_inventario_view(connection)
        except Exception:
            connection.rollback()

        Base.metadata.drop_all(bind=connection)
        Base.metadata.create_all(bind=connection)

        create_valor_inventario_view(connection)
        create_movimientos_inventario_view(connection)

    _reset_database_schema()

    session_factory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        _reset_database_schema()
        connection.close()


@pytest.fixture(scope="session")
def app_schema() -> Iterator[None]:
    """Garantiza que la app principal cuente con el esquema mínimo para pruebas ligeras."""

    Base.metadata.create_all(bind=app_engine)
    with app_engine.connect() as connection:
        create_valor_inventario_view(connection)
        create_movimientos_inventario_view(connection)

    yield None

    with app_engine.connect() as connection:
        drop_movimientos_inventario_view(connection)
        drop_valor_inventario_view(connection)
    Base.metadata.drop_all(bind=app_engine)


@pytest.fixture(scope="session")
def app(app_schema) -> Iterator:
    """Instancia la aplicación FastAPI una vez para toda la sesión de pruebas."""

    original_scheduler = settings.enable_background_scheduler
    original_backup_scheduler = settings.enable_backup_scheduler
    original_backup_dir = settings.backup_directory
    backup_tmp_dir = tempfile.TemporaryDirectory()

    settings.enable_background_scheduler = False
    settings.enable_backup_scheduler = False
    settings.backup_directory = backup_tmp_dir.name

    application = create_app()

    yield application

    application.dependency_overrides.clear()
    settings.enable_background_scheduler = original_scheduler
    settings.enable_backup_scheduler = original_backup_scheduler
    settings.backup_directory = original_backup_dir
    backup_tmp_dir.cleanup()


def _inject_reason_header(test_client: TestClient) -> None:
    sensitive_get_prefixes = ("/pos", "/reports", "/customers")
    original_request = test_client.request

    def _sanitize_ascii(value: str) -> str:
        # Convierte a ASCII seguro para cabeceras HTTP WSGI, eliminando acentos/símbolos
        try:
            import unicodedata

            normalized = unicodedata.normalize("NFKD", value)
            return normalized.encode("ascii", "ignore").decode("ascii")
        except Exception:
            # Fallback conservador
            return value.encode("ascii", "ignore").decode("ascii")

    def request_with_reason(method: str, url: str, *args, **kwargs):
        provided_headers = kwargs.pop("headers", None) or {}
        merged_headers = {**test_client.headers, **provided_headers}

        # Normaliza cualquier X-Reason entrante a ASCII para evitar UnicodeEncodeError en WSGI
        for key in list(merged_headers.keys()):
            if key.lower() == "x-reason" and isinstance(merged_headers[key], str):
                merged_headers[key] = _sanitize_ascii(merged_headers[key])

        path = urlsplit(url).path
        if method.upper() == "GET" and path.startswith(sensitive_get_prefixes):
            # Solo auto-inyectar motivo si la request NO está autenticada (para no interferir
            # con pruebas que validan el 400 por falta de motivo en rutas export).
            has_auth = any(k.lower() == "authorization" for k in merged_headers)
            if not has_auth and not any(key.lower() == "x-reason" for key in merged_headers):
                merged_headers["X-Reason"] = "Consulta automatizada pruebas"
        kwargs["headers"] = merged_headers
        return original_request(method, url, *args, **kwargs)

    test_client.request = request_with_reason  # type: ignore[assignment]


def _with_override(app, override: Callable[[], Generator[Any, None, None]]):
    app.dependency_overrides[get_db] = override
    return app


@pytest.fixture()
def client(app, db_session: Session) -> Iterator[TestClient]:
    """Entrega un cliente de pruebas que reutiliza la app y la sesión transaccional."""

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    _with_override(app, override_get_db)

    with TestClient(app) as test_client:
        if settings.bootstrap_token:
            test_client.headers.update({
                "X-Bootstrap-Token": settings.bootstrap_token,
            })
        _inject_reason_header(test_client)
        yield test_client

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def light_client(app) -> Iterator[TestClient]:
    """Cliente ligero que evita inicializar la sesión de base de datos para pruebas simples."""

    def override_get_db():
        yield None

    _with_override(app, override_get_db)

    with TestClient(app) as test_client:
        if settings.bootstrap_token:
            test_client.headers.update({
                "X-Bootstrap-Token": settings.bootstrap_token,
            })
        _inject_reason_header(test_client)
        yield test_client

    app.dependency_overrides.pop(get_db, None)
