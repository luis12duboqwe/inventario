from fastapi import status
from fastapi import status

from backend.app.core.roles import ADMIN, OPERADOR


def _bootstrap_admin(client):
    payload = {
        "username": "repairs_admin",
        "password": "Repairs123*",
        "full_name": "Repairs Admin",
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
    token = token_response.json()["access_token"]
    return token


def _bootstrap_operator(client, admin_token: str | None = None) -> str:
    if admin_token is None:
        admin_token = _bootstrap_admin(client)

    payload = {
        "username": "repairs_operator",
        "password": "RepairOp123*",
        "full_name": "Operador Reparaciones",
        "roles": [OPERADOR],
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_repair_order_flow(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Gestion reparaciones"}

    store_response = client.post(
        "/stores",
        json={"name": "Servicio Centro", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "REP-001",
            "name": "Pantalla Premium",
            "quantity": 10,
            "unit_price": 150.0,
            "costo_unitario": 90.0,
        },
        headers=reason_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={"name": "Cliente Reparaciones", "phone": "555-111-2222"},
        headers=reason_headers,
    )
    assert customer_response.status_code == status.HTTP_201_CREATED
    customer_id = customer_response.json()["id"]

    repair_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "technician_name": "Isaac Técnico",
        "damage_type": "Pantalla rota",
        "device_description": "Smartphone Azul",
        "labor_cost": 200.0,
        "parts": [{"device_id": device_id, "quantity": 2, "unit_cost": 95.0}],
    }
    repair_response = client.post("/repairs", json=repair_payload, headers=reason_headers)
    assert repair_response.status_code == status.HTTP_201_CREATED
    repair_data = repair_response.json()
    assert repair_data["parts_cost"] == 190.0
    assert repair_data["total_cost"] == 390.0
    assert repair_data["status"] == "PENDIENTE"

    devices_after = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    part_record = next(item for item in devices_after.json() if item["id"] == device_id)
    assert part_record["quantity"] == 8

    update_payload = {"status": "LISTO", "labor_cost": 210.0}
    update_response = client.put(
        f"/repairs/{repair_data['id']}", json=update_payload, headers=reason_headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["status"] == "LISTO"
    assert update_response.json()["labor_cost"] == 210.0

    list_response = client.get(
        "/repairs",
        params={"store_id": store_id, "status": "LISTO"},
        headers=auth_headers,
    )
    assert list_response.status_code == status.HTTP_200_OK
    assert any(item["id"] == repair_data["id"] for item in list_response.json())

    pdf_response = client.get(
        f"/repairs/{repair_data['id']}/pdf", headers=auth_headers
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    delete_response = client.delete(
        f"/repairs/{repair_data['id']}", headers=reason_headers
    )
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    devices_final = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    part_final = next(item for item in devices_final.json() if item["id"] == device_id)
    assert part_final["quantity"] == 10


def test_repair_requires_auth_and_reason(client):
    payload = {
        "store_id": 1,
        "technician_name": "Sin Token",
        "damage_type": "Diagnóstico",
        "labor_cost": 50.0,
        "parts": [],
    }
    unauthorized_response = client.post("/repairs", json=payload)
    assert unauthorized_response.status_code == status.HTTP_400_BAD_REQUEST

    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Reparaciones Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "REP-FALTA-RAZON",
            "name": "Modulo Diagnostico",
            "quantity": 4,
            "unit_price": 120.0,
            "costo_unitario": 80.0,
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    reason_missing_response = client.post(
        "/repairs",
        json={
            "store_id": store_id,
            "customer_name": "Cliente Sin Motivo",
            "technician_name": "Tecnico Sin Motivo",
            "damage_type": "Falla General",
            "labor_cost": 150.0,
            "parts": [{"device_id": device_id, "quantity": 1, "unit_cost": 85.0}],
        },
        headers=auth_headers,
    )
    assert reason_missing_response.status_code == status.HTTP_400_BAD_REQUEST

    reason_headers = {**auth_headers, "X-Reason": "Registro Reparacion"}
    repair_response = client.post(
        "/repairs",
        json={
            "store_id": store_id,
            "customer_name": "Cliente Autorizado",
            "technician_name": "Tecnico Autorizado",
            "damage_type": "Cambio de Pantalla",
            "labor_cost": 180.0,
            "parts": [{"device_id": device_id, "quantity": 1, "unit_cost": 90.0}],
        },
        headers=reason_headers,
    )
    assert repair_response.status_code == status.HTTP_201_CREATED


def test_repair_forbidden_for_operator(client):
    admin_token = _bootstrap_admin(client)
    operator_token = _bootstrap_operator(client, admin_token)

    operator_headers = {"Authorization": f"Bearer {operator_token}", "X-Reason": "Intento Operador"}

    list_response = client.get("/repairs", headers={"Authorization": f"Bearer {operator_token}"})
    assert list_response.status_code == status.HTTP_403_FORBIDDEN

    forbidden_response = client.post(
        "/repairs",
        json={
            "store_id": 1,
            "technician_name": "Operador",
            "damage_type": "Sin Permiso",
            "labor_cost": 10.0,
            "parts": [],
        },
        headers=operator_headers,
    )
    assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    store_response = client.post(
        "/stores",
        json={"name": "Reparaciones Centro", "location": "MX", "timezone": "America/Mexico_City"},
        headers=admin_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
