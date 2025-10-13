from __future__ import annotations

def test_health_endpoint_registered(client) -> None:
    routes = [route for route in client.app.routes if getattr(route, "path", None) == "/health"]

    assert routes, "El endpoint /health debe estar registrado"
    assert "GET" in routes[0].methods


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
