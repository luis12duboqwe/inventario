import pytest
from decimal import Decimal
from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN

# Reutilizamos patrón de bootstrap usado en otros tests de clientes.


def _bootstrap_admin(client):
    payload = {
        "username": "ledger_admin",
        "password": "LedgerAdm123*",
        "full_name": "Ledger Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK, token_response.text
    return token_response.json()["access_token"]


def test_customer_ledger_composite_flow(client):
    """Valida la secuencia compuesta del ledger de cliente:
    1. Ajuste manual de saldo inicial.
    2. Venta a crédito que incrementa la deuda.
    3. Pago parcial que reduce la deuda.
    Se verifica el orden cronológico, los balances acumulados y la coherencia de cada entrada.
    """
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Ledger compuesto"}

        # Crear sucursal base
        store_resp = client.post(
            "/stores",
            json={"name": "Ledger Central", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_resp.status_code == status.HTTP_201_CREATED, store_resp.text
        store_id = store_resp.json()["id"]

        # Crear dispositivo para la venta a crédito
        device_resp = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-LED-001",
                "name": "Smartphone Ledger",
                "quantity": 10,
                "unit_price": 300.0,
                "costo_unitario": 210.0,
            },
            headers=auth_headers,
        )
        assert device_resp.status_code == status.HTTP_201_CREATED, device_resp.text
        device_id = device_resp.json()["id"]

        # Crear cliente con límite de crédito suficiente
        customer_resp = client.post(
            "/customers",
            json={
                "name": "Cliente Ledger",
                "phone": "555-909-1010",
                "customer_type": "corporativo",
                "status": "activo",
                "credit_limit": 2000.0,
            },
            headers=reason_headers,
        )
        assert customer_resp.status_code == status.HTTP_201_CREATED, customer_resp.text
        customer_id = customer_resp.json()["id"]

        # 1. Ajuste manual de saldo (de 0 a 200)
        adjust_resp = client.put(
            f"/customers/{customer_id}",
            json={"outstanding_debt": 200.0},
            headers=reason_headers,
        )
        assert adjust_resp.status_code == status.HTTP_200_OK, adjust_resp.text
        assert adjust_resp.json()["outstanding_debt"] == pytest.approx(200.0)

        # 2. Registrar venta a crédito que añade 300 al saldo (total esperado 500)
        sale_resp = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "CREDITO",
                "items": [{"device_id": device_id, "quantity": 1}],
                "notes": "Venta credito compuesta",
            },
            headers={**auth_headers, "X-Reason": "Venta ledger"},
        )
        assert sale_resp.status_code == status.HTTP_201_CREATED, sale_resp.text
        sale_total = sale_resp.json()["total_amount"]
        assert sale_total == pytest.approx(300.0)

        # 3. Registrar pago parcial de 120 (saldo esperado 380)
        payment_resp = client.post(
            f"/customers/{customer_id}/payments",
            json={"amount": 120.0, "method": "transferencia",
                  "sale_id": sale_resp.json()["id"], "note": "Abono parcial"},
            headers=reason_headers,
        )
        assert payment_resp.status_code == status.HTTP_201_CREATED, payment_resp.text
        payment_entry = payment_resp.json()
        assert payment_entry["details"]["applied_amount"] == pytest.approx(
            120.0)
        assert payment_entry["balance_after"] == pytest.approx(380.0)

        # Obtener resumen y ledger
        summary_resp = client.get(
            f"/customers/{customer_id}/summary", headers=auth_headers)
        assert summary_resp.status_code == status.HTTP_200_OK, summary_resp.text
        summary = summary_resp.json()

        # Validar totales finales
        assert summary["totals"]["credit_limit"] == pytest.approx(2000.0)
        assert summary["totals"]["outstanding_debt"] == pytest.approx(380.0)
        assert summary["totals"]["available_credit"] == pytest.approx(1620.0)

        # Extraer ledger (orden DESC por creación); para validar secuencia lo invertimos
        ledger_desc = summary["ledger"]
        assert len(ledger_desc) >= 3, "Debe existir al menos ajuste, venta y pago"
        ledger = list(reversed(ledger_desc))  # Ahora cronológico ascendente

        # Filtrar las tres entradas esperadas
        adjustment_entry = next(
            e for e in ledger if e["entry_type"] == "adjustment")
        sale_entry = next(e for e in ledger if e["entry_type"] == "sale")
        payment_entry_summary = next(
            e for e in ledger if e["entry_type"] == "payment")

        # 1. Ajuste: amount = +200, balance_after = 200
        assert adjustment_entry["amount"] == pytest.approx(200.0)
        assert adjustment_entry["balance_after"] == pytest.approx(200.0)
        assert adjustment_entry["details"]["previous_balance"] == pytest.approx(
            0.0)
        assert adjustment_entry["details"]["new_balance"] == pytest.approx(
            200.0)
        assert adjustment_entry["details"]["difference"] == pytest.approx(
            200.0)

        # 2. Venta: amount = +300, balance_after = 500
        assert sale_entry["amount"] == pytest.approx(300.0)
        assert sale_entry["balance_after"] == pytest.approx(500.0)
        assert sale_entry["reference_type"] == "sale"
        assert sale_entry["reference_id"] == str(sale_resp.json()["id"])

        # 3. Pago: amount = -120, balance_after = 380, applied_amount en details
        assert payment_entry_summary["amount"] == pytest.approx(-120.0)
        assert payment_entry_summary["balance_after"] == pytest.approx(380.0)
        assert payment_entry_summary["details"]["applied_amount"] == pytest.approx(
            120.0)

        # Verificar coherencia de balance acumulado recorriendo cronológicamente
        running = Decimal("0")
        for entry in ledger:
            amt = Decimal(str(entry["amount"]))
            running = (running + amt).quantize(Decimal("0.01"))
            assert running == Decimal(
                str(entry["balance_after"])), f"Balance inconsistente tras {entry['entry_type']}"

    finally:
        settings.enable_purchases_sales = previous_flag
