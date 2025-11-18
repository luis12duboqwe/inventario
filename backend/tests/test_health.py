from __future__ import annotations

def test_health_endpoint_registered(light_client) -> None:
    routes = [
        route
        for route in light_client.app.routes
        if getattr(route, "path", None) == "/health"
    ]

    assert routes, "El endpoint /health debe estar registrado"
    assert "GET" in routes[0].methods


def test_health_endpoint_returns_ok(light_client) -> None:
    response = light_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
