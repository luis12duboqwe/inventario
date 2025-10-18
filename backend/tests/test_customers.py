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


def test_customer_debt_cannot_exceed_credit_limit(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Control credito clientes"}

    invalid_payload = {
        "name": "Cliente Sobreendeudado",
        "phone": "555-600-7000",
        "credit_limit": 300.0,
        "outstanding_debt": 320.0,
    }
    invalid_response = client.post(
        "/customers",
        json=invalid_payload,
        headers=reason_headers,
    )
    assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert (
        "límite de crédito" in invalid_response.json()["detail"].lower()
    )

    create_response = client.post(
        "/customers",
        json={
            "name": "Cliente Controlado",
            "phone": "555-101-3030",
            "credit_limit": 500.0,
            "outstanding_debt": 300.0,
        },
        headers=reason_headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    customer_id = create_response.json()["id"]

    exceeds_response = client.put(
        f"/customers/{customer_id}",
        json={"outstanding_debt": 620.0},
        headers=reason_headers,
    )
    assert exceeds_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    valid_adjustment = client.put(
        f"/customers/{customer_id}",
        json={"outstanding_debt": 450.0},
        headers=reason_headers,
    )
    assert valid_adjustment.status_code == status.HTTP_200_OK
    assert valid_adjustment.json()["outstanding_debt"] == pytest.approx(450.0)

    lower_limit_response = client.put(
        f"/customers/{customer_id}",
        json={"credit_limit": 400.0},
        headers=reason_headers,
    )
    assert lower_limit_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    reduce_debt_response = client.put(
        f"/customers/{customer_id}",
        json={"outstanding_debt": 350.0},
        headers=reason_headers,
    )
    assert reduce_debt_response.status_code == status.HTTP_200_OK
    assert reduce_debt_response.json()["outstanding_debt"] == pytest.approx(350.0)

    final_limit_response = client.put(
        f"/customers/{customer_id}",
        json={"credit_limit": 400.0},
        headers=reason_headers,
    )
    assert final_limit_response.status_code == status.HTTP_200_OK
    assert final_limit_response.json()["credit_limit"] == pytest.approx(400.0)


def test_customer_manual_debt_adjustment_creates_ledger_entry(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Ajuste saldo clientes"}

    create_response = client.post(
        "/customers",
        json={
            "name": "Cliente Ajuste",
            "phone": "555-303-4040",
            "credit_limit": 800.0,
        },
        headers=reason_headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    customer_id = create_response.json()["id"]

    update_response = client.put(
        f"/customers/{customer_id}",
        json={"outstanding_debt": 250.0},
        headers=reason_headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    payload = update_response.json()
    assert payload["outstanding_debt"] == pytest.approx(250.0)
    assert payload["history"]
    assert payload["history"][-1]["note"].startswith("Ajuste manual de saldo")

    summary_response = client.get(
        f"/customers/{customer_id}/summary",
        headers=auth_headers,
    )
    assert summary_response.status_code == status.HTTP_200_OK
    ledger_entries = summary_response.json()["ledger"]
    adjustment_entry = next(
        entry for entry in ledger_entries if entry["entry_type"] == "adjustment"
    )
    assert adjustment_entry["amount"] == pytest.approx(250.0)
    assert adjustment_entry["balance_after"] == pytest.approx(250.0)
    assert adjustment_entry["details"]["previous_balance"] == pytest.approx(0.0)
    assert adjustment_entry["details"]["new_balance"] == pytest.approx(250.0)
    assert adjustment_entry["details"]["difference"] == pytest.approx(250.0)
    assert adjustment_entry["note"].startswith("Ajuste manual de saldo")


def test_customer_filters_and_reports(client):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Panel clientes"}

        store_response = client.post(
            "/stores",
            json={"name": "Clientes Norte", "location": "MX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-CLI-100",
                "name": "Tablet Ejecutiva",
                "quantity": 10,
                "unit_price": 300.0,
                "costo_unitario": 220.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        moroso_response = client.post(
            "/customers",
            json={
                "name": "Cliente Moroso",
                "phone": "555-777-8888",
                "status": "moroso",
                "credit_limit": 500.0,
                "outstanding_debt": 280.0,
            },
            headers=reason_headers,
        )
        assert moroso_response.status_code == status.HTTP_201_CREATED
        moroso_id = moroso_response.json()["id"]

        frecuente_response = client.post(
            "/customers",
            json={
                "name": "Cliente Frecuente",
                "phone": "555-666-5555",
                "customer_type": "corporativo",
                "credit_limit": 1500.0,
            },
            headers=reason_headers,
        )
        assert frecuente_response.status_code == status.HTTP_201_CREATED
        frecuente_id = frecuente_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": frecuente_id,
                "payment_method": "CREDITO",
                "items": [{"device_id": device_id, "quantity": 2}],
            },
            headers={**auth_headers, "X-Reason": "Venta clientes"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        filtered_status = client.get(
            "/customers",
            params={"status": "moroso"},
            headers=auth_headers,
        )
        assert filtered_status.status_code == status.HTTP_200_OK
        assert len(filtered_status.json()) == 1
        assert filtered_status.json()[0]["id"] == moroso_id

        filtered_type = client.get(
            "/customers",
            params={"customer_type": "corporativo"},
            headers=auth_headers,
        )
        assert filtered_type.status_code == status.HTTP_200_OK
        assert any(item["id"] == frecuente_id for item in filtered_type.json())

        filtered_debt = client.get(
            "/customers",
            params={"has_debt": "true"},
            headers=auth_headers,
        )
        assert filtered_debt.status_code == status.HTTP_200_OK
        ids_with_debt = {item["id"] for item in filtered_debt.json()}
        assert moroso_id in ids_with_debt
        assert frecuente_id in ids_with_debt

        dashboard_response = client.get(
            "/customers/dashboard",
            params={"months": 6, "top_limit": 5},
            headers=auth_headers,
        )
        assert dashboard_response.status_code == status.HTTP_200_OK, dashboard_response.json()
        payload = dashboard_response.json()
        assert payload["months"] == 6
        assert payload["delinquent_summary"]["customers_with_debt"] >= 1
        assert payload["top_customers"], "Debe existir al menos un cliente frecuente en el ranking"
    finally:
        settings.enable_purchases_sales = previous_flag


def test_customer_portfolio_exports(client):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Reportes clientes"}

        store_response = client.post(
            "/stores",
            json={"name": "Clientes Sur", "location": "MX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-CLI-200",
                "name": "Laptop Premium",
                "quantity": 5,
                "unit_price": 900.0,
                "costo_unitario": 700.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        cliente_response = client.post(
            "/customers",
            json={
                "name": "Cliente Reporte",
                "phone": "555-123-9090",
                "customer_type": "corporativo",
                "credit_limit": 2500.0,
                "outstanding_debt": 600.0,
                "status": "moroso",
            },
            headers=reason_headers,
        )
        assert cliente_response.status_code == status.HTTP_201_CREATED
        customer_id = cliente_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "CREDITO",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers={**auth_headers, "X-Reason": "Venta reporte"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        json_response = client.get(
            "/reports/customers/portfolio",
            params={"category": "delinquent", "limit": 10},
            headers=auth_headers,
        )
        assert json_response.status_code == status.HTTP_200_OK
        data = json_response.json()
        assert data["category"] == "delinquent"
        assert any(item["customer_id"] == customer_id for item in data["items"])

        pdf_response = client.get(
            "/reports/customers/portfolio",
            params={"category": "delinquent", "export": "pdf"},
            headers=reason_headers,
        )
        assert pdf_response.status_code == status.HTTP_200_OK
        assert pdf_response.headers["content-type"] == "application/pdf"

        xlsx_response = client.get(
            "/reports/customers/portfolio",
            params={"category": "frequent", "export": "xlsx"},
            headers=reason_headers,
        )
        assert xlsx_response.status_code == status.HTTP_200_OK
        assert (
            xlsx_response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    finally:
        settings.enable_purchases_sales = previous_flag
