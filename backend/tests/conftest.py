from __future__ import annotations

import os
from collections.abc import Iterator

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "[\"http://testserver\"]")
os.environ.setdefault("SOFTMOBILE_BOOTSTRAP_TOKEN", "test-bootstrap-token")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import settings
from backend.app.database import Base, create_engine_from_url, get_db
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)
from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.main import create_app


@pytest.fixture(scope="session")
def db_engine() -> Iterator:
    """Crea un motor de base de datos aislado para las pruebas."""

    test_url = os.getenv("SOFTMOBILE_TEST_DATABASE", "sqlite:///:memory:")
    engine = create_engine_from_url(test_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    """Entrega una sesión limpia por prueba y garantiza el rollback."""

    Base.metadata.create_all(bind=db_engine)
    with db_engine.connect() as setup_connection:
        create_valor_inventario_view(setup_connection)
        create_movimientos_inventario_view(setup_connection)

    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autocommit=False, autoflush=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        if session.is_active:
            session.rollback()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        with db_engine.connect() as cleanup_connection:
            drop_movimientos_inventario_view(cleanup_connection)
            drop_valor_inventario_view(cleanup_connection)
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """Entrega un cliente de pruebas con la aplicación configurada en memoria."""

    settings.enable_background_scheduler = False
    settings.enable_backup_scheduler = False

    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        if settings.bootstrap_token:
            test_client.headers.update({
                "X-Bootstrap-Token": settings.bootstrap_token,
            })
        yield test_client

    app.dependency_overrides.clear()
