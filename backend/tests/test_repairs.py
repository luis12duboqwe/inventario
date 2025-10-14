from fastapi import status
from fastapi import status

from backend.app.core.roles import ADMIN


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
