"""Pytest fixtures for API tests."""
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.db.base_class import Base
from app.main import app
from app import models  # noqa: F401 ensure models import

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"  # pragma: no mutate


def _create_test_session() -> Generator[Session, None, None]:
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, Any, None]:
    """Return a test client with a temporary database."""

    app.dependency_overrides[get_db] = _create_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
