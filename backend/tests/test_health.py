"""Basic smoke tests for the minimal API."""
from app.http import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"].startswith("Softmobile")
