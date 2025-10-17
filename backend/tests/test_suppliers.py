import pytest
from fastapi import status

from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "suppliers_admin",
        "password": "Suppliers123*",
        "full_name": "Suppliers Admin",
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


def test_supplier_crud_flow(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Alta proveedores"}

    create_payload = {
        "name": "Refacciones Globales",
        "contact_name": "Pilar Ortega",
        "email": "pilar@refacciones.com",
        "phone": "+52 81 1234 5678",
    }
    create_response = client.post("/suppliers", json=create_payload, headers=headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    supplier_id = create_response.json()["id"]

    list_response = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == status.HTTP_200_OK
    assert any(item["id"] == supplier_id for item in list_response.json())

    csv_response = client.get(
        "/suppliers", headers={"Authorization": f"Bearer {token}"}, params={"export": "csv"}
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert "Refacciones Globales" in csv_response.text

    update_payload = {"notes": "Proveedor prioritario"}
    update_response = client.put(
        f"/suppliers/{supplier_id}", json=update_payload, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["notes"] == "Proveedor prioritario"

    delete_response = client.delete(f"/suppliers/{supplier_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    list_after_delete = client.get("/suppliers", headers={"Authorization": f"Bearer {token}"})
    assert list_after_delete.status_code == status.HTTP_200_OK
    assert all(item["id"] != supplier_id for item in list_after_delete.json())


def test_supplier_batches_and_inventory_value(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Gestion de lotes"}

    store_payload = {
        "name": "Sucursal Centro",
        "location": "CDMX",
        "timezone": "America/Mexico_City",
    }
    store_response = client.post("/stores", json=store_payload, headers=auth_headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SM-001",
        "name": "Smartphone Ejecutivo",
        "quantity": 10,
        "unit_price": 1200,
        "costo_unitario": 1000,
        "margen_porcentaje": 20,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=reason_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    supplier_payload = {
        "name": "Componentes del Norte",
        "contact_name": "Laura Díaz",
        "email": "compras@cdn.mx",
    }
    supplier_response = client.post(
        "/suppliers",
        json=supplier_payload,
        headers=reason_headers,
    )
    assert supplier_response.status_code == status.HTTP_201_CREATED
    supplier_id = supplier_response.json()["id"]

    batch_payload = {
        "model_name": "Smartphone Ejecutivo",
        "batch_code": "L-2024-01",
        "unit_cost": 800,
        "quantity": 50,
        "purchase_date": "2024-02-01",
        "notes": "Compra inicial del trimestre",
        "store_id": store_id,
        "device_id": device_id,
    }
    batch_response = client.post(
        f"/suppliers/{supplier_id}/batches",
        json=batch_payload,
        headers=reason_headers,
    )
    assert batch_response.status_code == status.HTTP_201_CREATED
    batch_id = batch_response.json()["id"]
    assert batch_response.json()["unit_cost"] == pytest.approx(800.0)

    store_detail = client.get(f"/stores/{store_id}", headers=auth_headers)
    assert store_detail.status_code == status.HTTP_200_OK
    assert store_detail.json()["inventory_value"] == pytest.approx(9600.0)

    list_batches = client.get(
        f"/suppliers/{supplier_id}/batches",
        headers=auth_headers,
    )
    assert list_batches.status_code == status.HTTP_200_OK
    assert len(list_batches.json()) == 1

    update_batch = client.put(
        f"/suppliers/batches/{batch_id}",
        json={"unit_cost": 820},
        headers=reason_headers,
    )
    assert update_batch.status_code == status.HTTP_200_OK
    assert update_batch.json()["unit_cost"] == pytest.approx(820.0)

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 5,
        "comentario": "Reposicion programada",
        "unit_cost": 900,
    }
    movement_headers = {**auth_headers, "X-Reason": movement_payload["comentario"]}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers=movement_headers,
    )
    assert movement_response.status_code == status.HTTP_201_CREATED
    movement_data = movement_response.json()
    assert movement_data["store_inventory_value"] == pytest.approx(15000.0)
    assert movement_data["unit_cost"] == pytest.approx(900.0)
    assert movement_data["producto_id"] == device_id

    store_after_movement = client.get(f"/stores/{store_id}", headers=auth_headers)
    assert store_after_movement.status_code == status.HTTP_200_OK
    assert store_after_movement.json()["inventory_value"] == pytest.approx(15000.0)

    delete_batch = client.delete(
        f"/suppliers/batches/{batch_id}",
        headers=reason_headers,
    )
    assert delete_batch.status_code == status.HTTP_204_NO_CONTENT

    batches_after_delete = client.get(
        f"/suppliers/{supplier_id}/batches",
        headers=auth_headers,
    )
    assert batches_after_delete.status_code == status.HTTP_200_OK
    assert batches_after_delete.json() == []
