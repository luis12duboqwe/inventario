"""Basic smoke tests for the API."""
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """The health endpoint should respond with status ok."""

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient) -> None:
    """Root endpoint should return a friendly message."""

    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"].startswith("Softmobile")
