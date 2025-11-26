from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "integrations_admin",
        "password": "Integraciones123*",
        "full_name": "Integraciones QA",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_list_integrations_requires_auth(client):
    response = client.get("/integrations")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_integrations_returns_metadata(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/integrations", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list) and payload

    zapier_entry = next(item for item in payload if item["slug"] == "zapier")
    assert zapier_entry["credential"]["token_hint"]
    assert zapier_entry["health"]["status"] in {"operational", "degraded", "offline"}


def test_integration_detail_and_rotation_flow(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    detail_response = client.get("/integrations/zapier", headers=auth_headers)
    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert detail["auth_type"] == "api_key"
    assert detail["features"]

    missing_reason = client.post("/integrations/zapier/rotate", headers=auth_headers)
    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST

    rotation_response = client.post(
        "/integrations/zapier/rotate",
        headers={**auth_headers, "X-Reason": "Rotacion programada Zapier"},
    )
    assert rotation_response.status_code == status.HTTP_200_OK
    rotation = rotation_response.json()
    assert len(rotation["token"]) >= 40
    assert rotation["credential"]["token_hint"] == rotation["token"][-4:]


def test_update_integration_health(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    payload = {"status": "degraded", "message": "Timeout al consumir webhook"}

    missing_reason = client.post(
        "/integrations/erp_sync/health", headers=auth_headers, json=payload
    )
    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST

    health_response = client.post(
        "/integrations/erp_sync/health",
        headers={**auth_headers, "X-Reason": "Sondeo ERP nocturno"},
        json=payload,
    )
    assert health_response.status_code == status.HTTP_200_OK
    health = health_response.json()
    assert health["status"] == "degraded"
    assert health["message"] == "Timeout al consumir webhook"
    assert health["checked_at"] is not None

    refreshed_detail = client.get("/integrations/erp_sync", headers=auth_headers)
    assert refreshed_detail.status_code == status.HTTP_200_OK
    refreshed_payload = refreshed_detail.json()
    assert refreshed_payload["health"]["status"] == "degraded"
    assert refreshed_payload["health"]["message"] == "Timeout al consumir webhook"


def test_unknown_integration_returns_404(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    not_found_detail = client.get("/integrations/unknown", headers=headers)
    assert not_found_detail.status_code == status.HTTP_404_NOT_FOUND

    rotate_response = client.post(
        "/integrations/unknown/rotate",
        headers={**headers, "X-Reason": "Intento controlado"},
    )
    assert rotate_response.status_code == status.HTTP_404_NOT_FOUND

    health_response = client.post(
        "/integrations/unknown/health",
        headers={**headers, "X-Reason": "Intento controlado"},
        json={"status": "offline"},
    )
    assert health_response.status_code == status.HTTP_404_NOT_FOUND
