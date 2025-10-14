from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "customers_admin",
        "password": "Clientes123*",
        "full_name": "Clientes Admin",
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


def test_customer_crud_flow(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Alta clientes"}

    create_payload = {
        "name": "Empresa Azul",
        "contact_name": "Laura Campos",
        "email": "laura@empresaazul.com",
        "phone": "+52 55 0000 0000",
        "history": [{"note": "Cliente corporativo", "timestamp": "2025-02-15T10:00:00"}],
    }
    create_response = client.post("/customers", json=create_payload, headers=headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    customer_id = create_response.json()["id"]

    list_response = client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == status.HTTP_200_OK
    assert any(item["id"] == customer_id for item in list_response.json())

    csv_response = client.get(
        "/customers", headers={"Authorization": f"Bearer {token}"}, params={"export": "csv"}
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert "Empresa Azul" in csv_response.text

    update_payload = {"phone": "+52 55 1111 2222"}
    update_response = client.put(
        f"/customers/{customer_id}", json=update_payload, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["phone"] == "+52 55 1111 2222"

    delete_response = client.delete(f"/customers/{customer_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    list_after_delete = client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert list_after_delete.status_code == status.HTTP_200_OK
    assert all(item["id"] != customer_id for item in list_after_delete.json())
