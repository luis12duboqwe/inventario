from fastapi import status

from backend.app.core.roles import ADMIN, OPERADOR


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


def _bootstrap_operator(client, admin_token: str | None = None) -> str:
    if admin_token is None:
        admin_token = _bootstrap_admin(client)

    payload = {
        "username": "customers_operator",
        "password": "ClientesOp123*",
        "full_name": "Operador Clientes",
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


def test_customer_crud_flow(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Alta clientes"}

    create_payload = {
        "name": "Empresa Azul",
        "contact_name": "Laura Campos",
        "email": "laura@empresaazul.com",
        "phone": "+52 55 0000 0000",
        "customer_type": "corporativo",
        "status": "activo",
        "credit_limit": 5000.0,
        "history": [{"note": "Cliente corporativo", "timestamp": "2025-02-15T10:00:00"}],
    }
    create_response = client.post("/customers", json=create_payload, headers=headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    customer_id = create_response.json()["id"]
    created_payload = create_response.json()
    assert created_payload["customer_type"] == "corporativo"
    assert created_payload["credit_limit"] == 5000.0

    list_response = client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == status.HTTP_200_OK
    assert any(item["id"] == customer_id for item in list_response.json())

    csv_response = client.get(
        "/customers", headers={"Authorization": f"Bearer {token}"}, params={"export": "csv"}
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert "Empresa Azul" in csv_response.text

    update_payload = {"phone": "+52 55 1111 2222", "status": "inactivo"}
    update_response = client.put(
        f"/customers/{customer_id}", json=update_payload, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["phone"] == "+52 55 1111 2222"
    assert update_response.json()["status"] == "inactivo"

    delete_response = client.delete(f"/customers/{customer_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    list_after_delete = client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert list_after_delete.status_code == status.HTTP_200_OK
    assert all(item["id"] != customer_id for item in list_after_delete.json())


def test_customers_require_reason_and_roles(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    payload = {"name": "Cliente Sin Motivo", "phone": "555-000-0000"}
    response_without_reason = client.post("/customers", json=payload, headers=auth_headers)
    assert response_without_reason.status_code == status.HTTP_400_BAD_REQUEST

    reason_headers = {**auth_headers, "X-Reason": "Registro Clientes"}
    create_response = client.post("/customers", json=payload, headers=reason_headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    customer_id = create_response.json()["id"]

    update_response = client.put(
        f"/customers/{customer_id}",
        json={"notes": "Actualización validada"},
        headers=auth_headers,
    )
    assert update_response.status_code == status.HTTP_400_BAD_REQUEST

    valid_update = client.put(
        f"/customers/{customer_id}",
        json={"notes": "Actualización OK"},
        headers=reason_headers,
    )
    assert valid_update.status_code == status.HTTP_200_OK

    delete_without_reason = client.delete(f"/customers/{customer_id}", headers=auth_headers)
    assert delete_without_reason.status_code == status.HTTP_400_BAD_REQUEST

    delete_response = client.delete(f"/customers/{customer_id}", headers=reason_headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT


def test_customers_operator_forbidden(client):
    admin_token = _bootstrap_admin(client)
    token = _bootstrap_operator(client, admin_token)
    headers = {"Authorization": f"Bearer {token}"}

    list_response = client.get("/customers", headers=headers)
    assert list_response.status_code == status.HTTP_403_FORBIDDEN

    create_response = client.post(
        "/customers",
        json={"name": "Operador Cliente", "phone": "555-101-2020"},
        headers={**headers, "X-Reason": "Intento Operador"},
    )
    assert create_response.status_code == status.HTTP_403_FORBIDDEN
