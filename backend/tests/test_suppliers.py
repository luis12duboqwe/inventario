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
