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


def test_method_not_allowed_returns_405(client: TestClient) -> None:
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "El método no está permitido para este endpoint.",
        }
    }
    # The Allow header documents the verbs accepted by the route.
    assert response.headers == {"Allow": "GET"}
