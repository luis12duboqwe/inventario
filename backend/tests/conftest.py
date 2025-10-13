"""Pytest fixtures for API tests using the minimal HTTP layer."""
from collections.abc import Generator

import pytest

from app.http import TestClient
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
