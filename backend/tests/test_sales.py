from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable

import json
import pytest
from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "ventas_admin",
        "password": "Ventas123*",
        "full_name": "Ventas Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def _create_user(client, auth_headers, *, username: str, roles: list[str]) -> str:
    response = client.post(
        "/users",
        json={
            "username": username,
            "password": "ClaveSegura123*",
            "full_name": "Usuario Movimiento",
            "roles": roles,
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": username, "password": "ClaveSegura123*"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_complete_sale_return_flow_requires_valid_role(client, db_session):
    settings.enable_purchases_sales = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        admin_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Permisos", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=admin_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-ROL-001",
                "name": "Terminal Corporativa",
                "quantity": 3,
                "unit_price": 320.0,
                "costo_unitario": 200.0,
                "margen_porcentaje": 18.0,
            },
            headers={**admin_headers, "X-Reason": "Alta inventario roles"},
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        invitado_token = _create_user(
            client,
            admin_headers,
            username="invitado_sales@test.io",
            roles=["INVITADO"],
        )
        operator_token = _create_user(
            client,
            admin_headers,
            username="operador_sales@test.io",
            roles=["OPERADOR"],
        )

        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 2}],
        }

        unauthenticated = client.post(
            "/sales",
            json=sale_payload,
            headers={"X-Reason": "Intento sin token"},
        )
        assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED

        guest_attempt = client.post(
            "/sales",
            json=sale_payload,
            headers={
                "Authorization": f"Bearer {invitado_token}",
                "X-Reason": "Intento sin rol",
            },
        )
        assert guest_attempt.status_code == status.HTTP_403_FORBIDDEN

        operator_headers = {
            "Authorization": f"Bearer {operator_token}",
            "X-Reason": "Venta completa autorizada",
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers=operator_headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        devices_after_sale = client.get(
            f"/stores/{store_id}/devices", headers=admin_headers)
        sold_device = next(
            item
            for item in _extract_items(devices_after_sale.json())
            if item["id"] == device_id
        )
        assert sold_device["quantity"] == 1

        return_response = client.post(
            "/sales/returns",
            json={
                "sale_id": sale_id,
                "items": [
                    {
                        "device_id": device_id,
                        "quantity": 2,
                        "reason": "Cliente devuelve compra completa",
                    }
                ],
            },
            headers={**operator_headers, "X-Reason": "Devolucion completa"},
        )
        assert return_response.status_code == status.HTTP_200_OK
        assert len(return_response.json()) == 1

        restored_devices = client.get(
            f"/stores/{store_id}/devices", headers=admin_headers)
        restored_device = next(
            item
            for item in _extract_items(restored_devices.json())
            if item["id"] == device_id
        )
        assert restored_device["quantity"] == 3
    finally:
        settings.enable_purchases_sales = False


def test_concurrent_sales_produce_conflict_when_inventory_runs_out(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}",
                   "X-Reason": "Ventas simultaneas"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Concurrencia", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-CONC-001",
                "name": "Scanner 2D",
                "quantity": 1,
                "unit_price": 180.0,
                "costo_unitario": 120.0,
                "margen_porcentaje": 10.0,
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
        }

        first_sale = client.post("/sales", json=sale_payload, headers=headers)
        assert first_sale.status_code == status.HTTP_201_CREATED

        second_sale = client.post("/sales", json=sale_payload, headers=headers)
        assert second_sale.status_code == status.HTTP_409_CONFLICT
        assert "Inventario" in second_sale.json()["detail"]

        final_device = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        assert final_device.quantity == 0
    finally:
        settings.enable_purchases_sales = previous_flag


def test_sale_and_return_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Ventas Norte", "location": "MX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-VENTA-001",
        "name": "Tablet Pro",
        "quantity": 5,
        "unit_price": 500.0,
        "costo_unitario": 350.0,
        "margen_porcentaje": 20.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "payment_method": "TARJETA",
        "discount_percent": 10.0,
        "items": [{"device_id": device_id, "quantity": 2}],
    }
    sale_response = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta mostrador"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    assert sale_data["payment_method"] == "TARJETA"
    # 2 units * 500.0 unit_price * 0.9 discount = 900.0
    assert sale_data["total_amount"] == 900.0

    devices_after_sale = client.get(
        f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after_sale.status_code == status.HTTP_200_OK
    device_after_sale = next(
        item
        for item in _extract_items(devices_after_sale.json())
        if item["id"] == device_id
    )
    assert device_after_sale["quantity"] == 3

    return_payload = {
        "sale_id": sale_data["id"],
        "items": [{"device_id": device_id, "quantity": 1, "reason": "Cliente arrepentido"}],
    }
    return_response = client.post(
        "/sales/returns",
        json=return_payload,
        headers={**auth_headers, "X-Reason": "Devolucion cliente"},
    )
    assert return_response.status_code == status.HTTP_200_OK
    assert len(return_response.json()) == 1

    sale_return_record = db_session.execute(
        select(models.SaleReturn).where(
            models.SaleReturn.sale_id == sale_data["id"])
    ).scalar_one()
    assert sale_return_record.reason == "Cliente arrepentido"
    assert sale_return_record.sale_id == sale_data["id"]

    devices_post_return = client.get(
        f"/stores/{store_id}/devices", headers=auth_headers)
    device_post_return = next(
        item
        for item in _extract_items(devices_post_return.json())
        if item["id"] == device_id
    )
    assert device_post_return["quantity"] == 4

    invalid_return = client.post(
        "/sales/returns",
        json={"sale_id": sale_data["id"], "items": [
            {"device_id": device_id, "quantity": 5, "reason": "Exceso"}]},
        headers={**auth_headers, "X-Reason": "Devolucion invalida"},
    )
    assert invalid_return.status_code == status.HTTP_409_CONFLICT

    settings.enable_purchases_sales = False


def test_sale_with_identifiers_marks_device_as_sold_and_cancel_restores(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal IMEI", "location": "MX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "IMEI-0001",
            "name": "Smartphone Elite",
            "quantity": 1,
            "unit_price": 800.0,
            "costo_unitario": 500.0,
            "margen_porcentaje": 25.0,
            "imei": "356789012345678",
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_response = client.post(
        "/sales",
        json={"store_id": store_id, "items": [
            {"device_id": device_id, "quantity": 1}]},
        headers={**auth_headers, "X-Reason": "Venta IMEI"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_id = sale_response.json()["id"]

    device_record = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert device_record.quantity == 0
    assert device_record.estado == "vendido"

    duplicate_sale = client.post(
        "/sales",
        json={"store_id": store_id, "items": [
            {"device_id": device_id, "quantity": 1}]},
        headers={**auth_headers, "X-Reason": "Intento duplicado"},
    )
    assert duplicate_sale.status_code == status.HTTP_409_CONFLICT

    cancel_response = client.post(
        f"/sales/{sale_id}/cancel",
        headers={**auth_headers, "X-Reason": "Cliente se arrepiente"},
    )
    assert cancel_response.status_code == status.HTTP_200_OK

    refreshed_device = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert refreshed_device.quantity == 1
    assert refreshed_device.estado == "disponible"

    movements = list(
        db_session.execute(
            select(models.InventoryMovement).where(
                models.InventoryMovement.device_id == device_id)
        ).scalars()
    )
    assert len(movements) == 2
    assert movements[0].movement_type == models.MovementType.OUT
    assert movements[1].movement_type == models.MovementType.IN

    settings.enable_purchases_sales = False


def test_cancel_sale_generates_credit_note_for_reported_invoice(client, db_session):
    settings.enable_purchases_sales = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Reporte", "location": "HN",
                  "timezone": "America/Tegucigalpa"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "INV-REP-01",
                "name": "Impresora Fiscal",
                "quantity": 2,
                "unit_price": 450.0,
                "costo_unitario": 300.0,
                "margen_porcentaje": 15.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={
                "name": "Cliente Reportado",
                "phone": "504-2213-0000",
                "customer_type": "corporativo",
                "status": "activo",
                "tax_id": "08011999000140",
                "credit_limit": 0.0,
            },
            headers={**auth_headers, "X-Reason": "Alta cliente fiscal"},
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers={**auth_headers, "X-Reason": "Venta fiscal"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_record = db_session.execute(
            select(models.Sale).where(models.Sale.id == sale_id)
        ).scalar_one()
        sale_record.invoice_reported = True
        sale_record.invoice_reported_at = datetime.utcnow()
        db_session.commit()

        cancel_response = client.post(
            f"/sales/{sale_id}/cancel",
            headers={**auth_headers, "X-Reason": "Anulación fiscal"},
        )
        assert cancel_response.status_code == status.HTTP_200_OK
        cancelled = cancel_response.json()
        assert cancelled["status"].upper() == "CANCELADA"
        assert cancelled["invoice_reported"] is False
        assert cancelled["invoice_annulled_at"] is not None
        assert cancelled["invoice_credit_note_code"]

        credit_note_record = db_session.execute(
            select(models.StoreCredit).where(
                models.StoreCredit.customer_id == customer_id)
        ).scalar_one()
        assert credit_note_record.code == cancelled["invoice_credit_note_code"]
        # Preserves explicit unit_price of 450.0 (not recalculated from cost+margin)
        assert float(credit_note_record.issued_amount) == pytest.approx(450.0)
    finally:
        settings.enable_purchases_sales = False


def test_sales_history_search_filters(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Historial", "location": "MX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    customer = models.Customer(
        name="Cliente Historial",
        phone="5550001122",
        customer_type="minorista",
        status="activo",
        credit_limit=Decimal("0"),
        outstanding_debt=Decimal("0"),
        history=[],
    )
    db_session.add(customer)
    db_session.commit()
    customer_id = customer.id  # Guardar el ID antes de que se desvincu le

    device_payload = {
        "sku": "SKU-HIST-001",
        "name": "Lector QR",
        "quantity": 3,
        "unit_price": 450.0,
        "costo_unitario": 280.0,
        "margen_porcentaje": 18.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_response = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"device_id": device_id, "quantity": 1}],
            "notes": "Ticket preferente",
        },
        headers={**auth_headers, "X-Reason": "Venta historial"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    sale_id = sale_data["id"]

    sale_record = db_session.execute(
        select(models.Sale).where(models.Sale.id == sale_id)
    ).scalar_one()
    sale_record.created_at = datetime(2025, 2, 1, 10, 30, tzinfo=timezone.utc)
    sale_record.customer_name = "Cliente Historial"
    db_session.commit()

    qr_payload = json.dumps(
        {
            "sale_id": sale_id,
            "doc": f"FAC-{sale_id:06d}",
            "total": f"{sale_data['total_amount']:.2f}",
            "issued_at": sale_record.created_at.isoformat(),
            "type": "ticket",
        }
    )

    combined_response = client.get(
        "/sales/history/search",
        params={
            "ticket": f"TCK-{sale_id:06d}",
            "date": "2025-02-01",
            "customer": "Historial",
            "qr": qr_payload,
        },
        headers=auth_headers,
    )
    assert combined_response.status_code == status.HTTP_200_OK
    payload = combined_response.json()
    assert payload["by_ticket"][0]["id"] == sale_id
    assert payload["by_qr"][0]["id"] == sale_id
    assert any(item["id"] == sale_id for item in payload["by_customer"])
    assert any(item["id"] == sale_id for item in payload["by_date"])

    empty_response = client.get(
        "/sales/history/search",
        params={"ticket": "999999"},
        headers=auth_headers,
    )
    assert empty_response.status_code == status.HTTP_200_OK
    assert empty_response.json()["by_ticket"] == []

    settings.enable_purchases_sales = False


def test_sale_update_adjusts_inventory_and_records_movements(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Centro", "location": "MX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_a = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-A",
            "name": "Auriculares",
            "quantity": 5,
            "unit_price": 50.0,
            "costo_unitario": 20.0,
            "margen_porcentaje": 15.0,
        },
        headers=auth_headers,
    )
    device_b = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-B",
            "name": "Cargador",
            "quantity": 6,
            "unit_price": 30.0,
            "costo_unitario": 10.0,
            "margen_porcentaje": 20.0,
        },
        headers=auth_headers,
    )
    assert device_a.status_code == status.HTTP_201_CREATED
    assert device_b.status_code == status.HTTP_201_CREATED
    device_a_id = device_a.json()["id"]
    device_b_id = device_b.json()["id"]

    sale_response = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [
                {"device_id": device_a_id, "quantity": 2},
                {"device_id": device_b_id, "quantity": 1},
            ],
        },
        headers={**auth_headers, "X-Reason": "Venta inicial"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_id = sale_response.json()["id"]

    update_response = client.put(
        f"/sales/{sale_id}",
        json={
            "payment_method": "TARJETA",
            "discount_percent": 5.0,
            "items": [
                {"device_id": device_a_id, "quantity": 1},
                {"device_id": device_b_id, "quantity": 3},
            ],
        },
        headers={**auth_headers, "X-Reason": "Actualizacion venta"},
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_sale = update_response.json()
    assert updated_sale["payment_method"] == "TARJETA"
    assert sorted(item["device_id"] for item in updated_sale["items"]) == sorted(
        [device_a_id, device_b_id])

    device_a_record = db_session.execute(
        select(models.Device).where(models.Device.id == device_a_id)
    ).scalar_one()
    device_b_record = db_session.execute(
        select(models.Device).where(models.Device.id == device_b_id)
    ).scalar_one()
    assert device_a_record.quantity == 4
    assert device_b_record.quantity == 3

    movements = list(
        db_session.execute(
            select(models.InventoryMovement)
            .where(models.InventoryMovement.store_id == store_id)
            .order_by(models.InventoryMovement.created_at.asc())
        ).scalars()
    )
    assert any(movement.quantity == 2 and movement.device_id ==
               device_a_id for movement in movements)
    assert any(movement.quantity == 1 and movement.device_id ==
               device_b_id for movement in movements)
    assert any(
        movement.quantity == 1
        and movement.device_id == device_a_id
        and movement.movement_type == models.MovementType.OUT
        for movement in movements
    )
    assert any(
        movement.quantity == 3
        and movement.device_id == device_b_id
        and movement.movement_type == models.MovementType.OUT
        for movement in movements
    )

    settings.enable_purchases_sales = False


def test_sales_filters_and_exports(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Filtros", "location": "CDMX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente Filtros",
            "email": "cliente@example.com",
            "phone": "555-200-3000",
        },
        headers={**auth_headers, "X-Reason": "Alta cliente filtros"},
    )
    assert customer_response.status_code == status.HTTP_201_CREATED
    customer_id = customer_response.json()["id"]

    device_a = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "FILTRO-1001",
            "name": "Smartphone Filtro",
            "quantity": 4,
            "unit_price": 650.0,
            "costo_unitario": 400.0,
            "imei": "990000862471854",
        },
        headers=auth_headers,
    )
    assert device_a.status_code == status.HTTP_201_CREATED
    device_a_id = device_a.json()["id"]

    device_b = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "FILTRO-2002",
            "name": "Accesorio Filtro",
            "quantity": 6,
            "unit_price": 120.0,
            "costo_unitario": 60.0,
        },
        headers=auth_headers,
    )
    assert device_b.status_code == status.HTTP_201_CREATED
    device_b_id = device_b.json()["id"]

    sale_one = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_a_id, "quantity": 1}],
        },
        headers={**auth_headers, "X-Reason": "Venta filtros 1"},
    )
    assert sale_one.status_code == status.HTTP_201_CREATED
    sale_one_id = sale_one.json()["id"]

    sale_two = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "TARJETA",
            "items": [{"device_id": device_b_id, "quantity": 2}],
            "notes": "Venta interna",
        },
        headers={**auth_headers, "X-Reason": "Venta filtros 2"},
    )
    assert sale_two.status_code == status.HTTP_201_CREATED
    sale_two_id = sale_two.json()["id"]

    # Ajustar fecha de la segunda venta para probar filtros de rango
    db_sale_two = db_session.execute(
        select(models.Sale).where(models.Sale.id == sale_two_id)
    ).scalar_one()
    db_sale_two.created_at = db_sale_two.created_at - timedelta(days=5)
    db_session.commit()

    list_all = client.get(
        "/sales",
        params={"store_id": store_id, "limit": 200, "offset": 0},
        headers=auth_headers,
    )
    assert list_all.status_code == status.HTTP_200_OK
    list_all_items = _extract_items(list_all.json())
    assert {sale["id"]
            for sale in list_all_items} == {sale_one_id, sale_two_id}

    list_by_customer = client.get(
        "/sales",
        params={"customer_id": customer_id, "limit": 200, "offset": 0},
        headers=auth_headers,
    )
    assert list_by_customer.status_code == status.HTTP_200_OK
    list_by_customer_items = _extract_items(list_by_customer.json())
    assert len(list_by_customer_items) == 1
    assert list_by_customer_items[0]["customer_id"] == customer_id

    today_iso = datetime.utcnow().date().isoformat()
    list_recent = client.get(
        "/sales",
        params={"date_from": today_iso, "limit": 200, "offset": 0},
        headers=auth_headers,
    )
    assert list_recent.status_code == status.HTTP_200_OK
    list_recent_items = _extract_items(list_recent.json())
    assert len(list_recent_items) == 1
    assert list_recent_items[0]["id"] == sale_one_id

    list_by_user = client.get(
        "/sales",
        params={"performed_by_id": user_id, "limit": 200, "offset": 0},
        headers=auth_headers,
    )
    assert list_by_user.status_code == status.HTTP_200_OK
    list_by_user_items = _extract_items(list_by_user.json())
    assert len(list_by_user_items) == 2

    list_by_query = client.get(
        "/sales",
        params={"q": "FILTRO-1001", "limit": 200, "offset": 0},
        headers=auth_headers,
    )
    assert list_by_query.status_code == status.HTTP_200_OK
    list_by_query_items = _extract_items(list_by_query.json())
    assert len(list_by_query_items) == 1
    assert list_by_query_items[0]["id"] == sale_one_id

    export_without_reason = client.get(
        "/sales/export/pdf", headers=auth_headers)
    assert export_without_reason.status_code == status.HTTP_400_BAD_REQUEST

    export_pdf = client.get(
        "/sales/export/pdf",
        headers={**auth_headers, "X-Reason": "Reporte ventas"},
    )
    assert export_pdf.status_code == status.HTTP_200_OK
    assert export_pdf.headers["content-type"] == "application/pdf"
    assert len(export_pdf.content) > 0

    export_excel = client.get(
        "/sales/export/xlsx",
        headers={**auth_headers, "X-Reason": "Reporte ventas"},
    )
    assert export_excel.status_code == status.HTTP_200_OK
    assert export_excel.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
    assert len(export_excel.content) > 0

    settings.enable_purchases_sales = False


def test_credit_sale_rejected_when_limit_exceeded(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Control credito"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Credito", "location": "MX",
              "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-CREDITO-001",
            "name": "Laptop Corporativa",
            "quantity": 2,
            "unit_price": 150.0,
            "costo_unitario": 100.0,
            "margen_porcentaje": 15.0,
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente Crédito Limitado",
            "phone": "555-202-3030",
            "credit_limit": 100.0,
            "customer_type": "corporativo",
            "status": "activo",
        },
        headers=reason_headers,
    )
    assert customer_response.status_code == status.HTTP_201_CREATED
    customer_id = customer_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "CREDITO",
        "items": [{"device_id": device_id, "quantity": 1}],
    }
    blocked_sale = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta credito"},
    )
    assert blocked_sale.status_code == status.HTTP_409_CONFLICT
    assert (
        blocked_sale.json()["detail"]
        == "El cliente excede el límite de crédito disponible."
    )

    pos_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "CREDITO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": True,
    }
    blocked_pos_sale = client.post(
        "/pos/sale",
        json=pos_payload,
        headers={**auth_headers, "X-Reason": "POS credito"},
    )
    assert blocked_pos_sale.status_code == status.HTTP_409_CONFLICT
    assert (
        blocked_pos_sale.json()["detail"]
        == "El cliente excede el límite de crédito disponible."
    )

    devices_response = client.get(
        f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_response.status_code == status.HTTP_200_OK
    device_record = next(
        item for item in _extract_items(devices_response.json()) if item["id"] == device_id
    )
    assert device_record["quantity"] == 2

    settings.enable_purchases_sales = False


def test_sales_endpoints_require_feature_flag(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}",
               "X-Reason": "Verificar flag"}

    try:
        settings.enable_purchases_sales = False
        list_response = client.get("/sales", headers=headers)
        assert list_response.status_code == status.HTTP_404_NOT_FOUND

        payload = {
            "store_id": 1,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": 1, "quantity": 1}],
        }
        create_response = client.post("/sales", json=payload, headers=headers)
        assert create_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = previous_flag


def test_sale_rejects_when_quantity_exceeds_stock(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}",
                   "X-Reason": "Venta excedida"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Venta", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "VENTA-ESCASA",
                "name": "Smartphone Limitado",
                "quantity": 1,
                "unit_price": 1000.0,
                "costo_unitario": 750.0,
                "margen_porcentaje": 20.0,
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        response = client.post(
            "/sales",
            json={"store_id": store_id, "items": [
                {"device_id": device_id, "quantity": 3}]},
            headers=headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()[
            "detail"] == "Inventario insuficiente para la venta."

        refreshed_device = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        assert refreshed_device.quantity == 1
    finally:
        settings.enable_purchases_sales = previous_flag


def test_sale_rejects_when_device_is_already_sold(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}",
                   "X-Reason": "Venta IMEI vendida"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal IMEI Vendida", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "IMEI-VENDIDO-01",
                "name": "Smartphone Vendido",
                "quantity": 1,
                "unit_price": 900.0,
                "costo_unitario": 650.0,
                "margen_porcentaje": 18.0,
                "imei": "990000862471854",
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        device_record = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        device_record.estado = "vendido"
        db_session.commit()

        response = client.post(
            "/sales",
            json={"store_id": store_id, "items": [
                {"device_id": device_id, "quantity": 1}]},
            headers=headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()[
            "detail"] == "El dispositivo ya fue vendido y no está disponible."
    finally:
        settings.enable_purchases_sales = previous_flag


def test_sale_audit_logs_include_reason(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}"}

    try:
        store_response = client.post(
            "/stores",
            json={"name": "Ventas Centro", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=base_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_payload = {
            "sku": "AUD-VENT-001",
            "name": "Smartphone Auditor",
            "quantity": 4,
            "unit_price": 420.0,
            "costo_unitario": 300.0,
            "margen_porcentaje": 15.0,
        }
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers={**base_headers, "X-Reason": "Alta inventario auditoria"},
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_reason = "Venta auditada"
        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers={**base_headers, "X-Reason": sale_reason},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_log = db_session.execute(
            select(models.AuditLog)
            .where(
                models.AuditLog.action == "sale_registered",
                models.AuditLog.entity_type == "sale",
                models.AuditLog.entity_id == str(sale_id),
            )
            .order_by(models.AuditLog.created_at.desc())
        ).scalars().first()
        assert sale_log is not None
        sale_details = json.loads(sale_log.details)
        assert sale_details["reason"] == sale_reason

        return_reason = "Devolucion auditoria"
        return_payload = {
            "sale_id": sale_id,
            "items": [{"device_id": device_id, "quantity": 1, "reason": "Cliente detecta falla"}],
        }
        return_response = client.post(
            "/sales/returns",
            json=return_payload,
            headers={**base_headers, "X-Reason": return_reason},
        )
        assert return_response.status_code == status.HTTP_200_OK

        return_log = db_session.execute(
            select(models.AuditLog)
            .where(
                models.AuditLog.action == "sale_return_registered",
                models.AuditLog.entity_type == "sale",
                models.AuditLog.entity_id == str(sale_id),
            )
            .order_by(models.AuditLog.created_at.desc())
        ).scalars().first()
        assert return_log is not None
        return_details = json.loads(return_log.details)
        assert return_details["reason"] == return_reason
    finally:
        settings.enable_purchases_sales = previous_flag
