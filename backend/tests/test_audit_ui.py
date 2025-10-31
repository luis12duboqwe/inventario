from datetime import datetime, timedelta

from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "audit_ui_admin",
        "password": "AuditUI123*",
        "full_name": "Auditora UI",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), payload


def _login(client, username: str, password: str):
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


# // [PACK32-33-BE] Verifica inserción, filtros y exportación de audit_ui.
def test_audit_ui_bulk_list_and_filters(client):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])
    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    now = datetime.utcnow()
    payload = {
        "items": [
            {
                "ts": now.isoformat(),
                "userId": "cashier.1",
                "module": "POS",
                "action": "checkout",
                "entityId": "sale-1001",
                "meta": {"total": 120.5},
            },
            {
                "ts": (now - timedelta(minutes=5)).isoformat(),
                "userId": "manager.1",
                "module": "CUSTOMERS",
                "action": "update",
                "entityId": "customer-55",
                "meta": {"fields": ["status"]},
            },
        ]
    }

    bulk_response = client.post("/api/audit/ui/bulk", json=payload, headers=auth_headers)
    assert bulk_response.status_code == status.HTTP_201_CREATED
    assert bulk_response.json() == {"inserted": 2}

    list_response = client.get(
        "/api/audit/ui",
        params={"limit": 10, "offset": 0},
        headers=auth_headers,
    )
    assert list_response.status_code == status.HTTP_200_OK
    data = list_response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["module"] == "POS"
    assert data["has_more"] is False

    filtered_response = client.get(
        "/api/audit/ui",
        params={"userId": "manager.1"},
        headers=auth_headers,
    )
    assert filtered_response.status_code == status.HTTP_200_OK
    filtered = filtered_response.json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["entity_id"] == "customer-55"

    empty_response = client.get(
        "/api/audit/ui",
        params={"from": (now + timedelta(days=1)).isoformat()},
        headers=auth_headers,
    )
    assert empty_response.status_code == status.HTTP_200_OK
    assert empty_response.json()["total"] == 0


def test_audit_ui_export_csv_and_json(client):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])
    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    event_payload = {
        "items": [
            {
                "ts": datetime.utcnow().isoformat(),
                "userId": admin["username"],
                "module": "POS",
                "action": "hold",
                "entityId": "hold-1",
                "meta": {"status": "on_hold"},
            }
        ]
    }
    bulk_response = client.post("/api/audit/ui/bulk", json=event_payload, headers=auth_headers)
    assert bulk_response.status_code == status.HTTP_201_CREATED

    csv_response = client.get(
        "/api/audit/ui/export",
        params={"format": "csv"},
        headers=auth_headers,
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "hold-1" in csv_response.text

    json_response = client.get(
        "/api/audit/ui/export",
        params={"format": "json", "limit": 5},
        headers=auth_headers,
    )
    assert json_response.status_code == status.HTTP_200_OK
    assert json_response.headers["content-type"].startswith("application/json")
    body = json_response.json()
    assert isinstance(body, list)
    assert body[0]["action"] == "hold"
