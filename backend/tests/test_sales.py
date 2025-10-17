from datetime import datetime, timedelta

from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


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
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_sale_and_return_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Ventas Norte", "location": "MX", "timezone": "America/Mexico_City"},
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
    assert sale_data["total_amount"] == 900.0

    devices_after_sale = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after_sale.status_code == status.HTTP_200_OK
    device_after_sale = next(item for item in devices_after_sale.json() if item["id"] == device_id)
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

    devices_post_return = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    device_post_return = next(item for item in devices_post_return.json() if item["id"] == device_id)
    assert device_post_return["quantity"] == 4

    invalid_return = client.post(
        "/sales/returns",
        json={"sale_id": sale_data["id"], "items": [{"device_id": device_id, "quantity": 5, "reason": "Exceso"}]},
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
        json={"name": "Sucursal IMEI", "location": "MX", "timezone": "America/Mexico_City"},
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
        json={"store_id": store_id, "items": [{"device_id": device_id, "quantity": 1}]},
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
        json={"store_id": store_id, "items": [{"device_id": device_id, "quantity": 1}]},
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
            select(models.InventoryMovement).where(models.InventoryMovement.device_id == device_id)
        ).scalars()
    )
    assert len(movements) == 2
    assert movements[0].movement_type == models.MovementType.OUT
    assert movements[1].movement_type == models.MovementType.IN

    settings.enable_purchases_sales = False


def test_sale_update_adjusts_inventory_and_records_movements(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Centro", "location": "MX", "timezone": "America/Mexico_City"},
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
    assert sorted(item["device_id"] for item in updated_sale["items"]) == sorted([device_a_id, device_b_id])

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
    assert any(movement.quantity == 2 and movement.device_id == device_a_id for movement in movements)
    assert any(movement.quantity == 1 and movement.device_id == device_b_id for movement in movements)
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
        json={"name": "Sucursal Filtros", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={"name": "Cliente Filtros", "email": "cliente@example.com"},
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

    list_all = client.get(f"/sales?store_id={store_id}", headers=auth_headers)
    assert list_all.status_code == status.HTTP_200_OK
    assert {sale["id"] for sale in list_all.json()} == {sale_one_id, sale_two_id}

    list_by_customer = client.get(
        f"/sales?customer_id={customer_id}", headers=auth_headers
    )
    assert list_by_customer.status_code == status.HTTP_200_OK
    assert len(list_by_customer.json()) == 1
    assert list_by_customer.json()[0]["customer_id"] == customer_id

    today_iso = datetime.utcnow().date().isoformat()
    list_recent = client.get(
        f"/sales?date_from={today_iso}", headers=auth_headers
    )
    assert list_recent.status_code == status.HTTP_200_OK
    assert len(list_recent.json()) == 1
    assert list_recent.json()[0]["id"] == sale_one_id

    list_by_user = client.get(
        f"/sales?performed_by_id={user_id}", headers=auth_headers
    )
    assert list_by_user.status_code == status.HTTP_200_OK
    assert len(list_by_user.json()) == 2

    list_by_query = client.get("/sales", params={"q": "FILTRO-1001"}, headers=auth_headers)
    assert list_by_query.status_code == status.HTTP_200_OK
    assert len(list_by_query.json()) == 1
    assert list_by_query.json()[0]["id"] == sale_one_id

    export_without_reason = client.get("/sales/export/pdf", headers=auth_headers)
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
