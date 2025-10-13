from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app import database
from backend.app.database import Base, create_engine_from_url, get_db
from backend.app.main import create_app


@pytest.fixture(scope="session")
def db_engine() -> Iterator:
    test_url = os.getenv("SOFTMOBILE_TEST_DATABASE", "sqlite:///:memory:")
    engine = create_engine_from_url(test_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(scope="session")
def app(db_engine, db_session_factory):
    original_engine = database.engine
    original_sessionlocal = database.SessionLocal

    database.engine = db_engine
    database.SessionLocal = db_session_factory

    app = create_app()
    try:
        yield app
    finally:
        database.engine = original_engine
        database.SessionLocal = original_sessionlocal


@pytest.fixture()
def client(app, db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
