import pytest
from fastapi import status

from backend.app.config import settings
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


def test_customer_payments_and_summary(client):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Gestion clientes"}

        store_response = client.post(
            "/stores",
            json={
                "name": "Clientes Centro",
                "location": "MX",
                "timezone": "America/Mexico_City",
            },
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-CLI-001",
                "name": "Smartphone Corporativo",
                "quantity": 3,
                "unit_price": 200.0,
                "costo_unitario": 150.0,
                "margen_porcentaje": 10.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={
                "name": "Cliente Financiero",
                "phone": "555-404-5050",
                "customer_type": "corporativo",
                "status": "activo",
                "credit_limit": 1000.0,
            },
            headers=reason_headers,
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        note_response = client.post(
            f"/customers/{customer_id}/notes",
            json={"note": "Seguimiento anual"},
            headers=reason_headers,
        )
        assert note_response.status_code == status.HTTP_200_OK
        assert any(
            entry["note"] == "Seguimiento anual" for entry in note_response.json()["history"]
        )

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "CREDITO",
                "items": [{"device_id": device_id, "quantity": 1}],
                "notes": "Venta a crédito",
            },
            headers={**auth_headers, "X-Reason": "Venta credito clientes"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_data = sale_response.json()

        payment_response = client.post(
            f"/customers/{customer_id}/payments",
            json={
                "amount": 80.0,
                "method": "transferencia",
                "sale_id": sale_data["id"],
                "note": "Abono inicial",
            },
            headers=reason_headers,
        )
        assert payment_response.status_code == status.HTTP_201_CREATED
        payment_data = payment_response.json()
        assert payment_data["details"]["sale_id"] == sale_data["id"]
        assert payment_data["balance_after"] == pytest.approx(sale_data["total_amount"] - 80.0)

        summary_response = client.get(
            f"/customers/{customer_id}/summary", headers=auth_headers
        )
        assert summary_response.status_code == status.HTTP_200_OK
        summary = summary_response.json()

        assert summary["customer"]["id"] == customer_id
        assert summary["totals"]["credit_limit"] == 1000.0
        assert summary["totals"]["outstanding_debt"] == pytest.approx(
            sale_data["total_amount"] - 80.0
        )
        assert summary["totals"]["available_credit"] == pytest.approx(
            1000.0 - (sale_data["total_amount"] - 80.0)
        )

        assert summary["sales"][0]["sale_id"] == sale_data["id"]
        assert summary["sales"][0]["payment_method"] == "CREDITO"
        assert summary["invoices"][0]["sale_id"] == sale_data["id"]
        assert summary["invoices"][0]["invoice_number"].startswith("VENTA-")

        assert summary["payments"][0]["entry_type"] == "payment"
        assert summary["payments"][0]["details"]["applied_amount"] == pytest.approx(80.0)

        ledger_types = {entry["entry_type"] for entry in summary["ledger"]}
        assert {"note", "sale", "payment"}.issubset(ledger_types)
    finally:
        settings.enable_purchases_sales = previous_flag
