from decimal import Decimal

from decimal import Decimal

from fastapi import status
from sqlalchemy import select, text

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "compras_admin",
        "password": "Compras123*",
        "full_name": "Compras Admin",
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


def test_purchase_receipt_and_return_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operacion de compra"}

    store_response = client.post(
        "/stores",
        json={"name": "Compras Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-COMP-001",
        "name": "Smartphone corporativo",
        "quantity": 10,
        "unit_price": 1500.0,
        "costo_unitario": 1000.0,
        "margen_porcentaje": 15.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    order_payload = {
        "store_id": store_id,
        "supplier": "Proveedor Mayorista",
        "items": [
            {"device_id": device_id, "quantity_ordered": 10, "unit_cost": 850.0},
        ],
    }
    order_response = client.post("/purchases", json=order_payload, headers=auth_headers)
    assert order_response.status_code == status.HTTP_201_CREATED
    order_id = order_response.json()["id"]

    partial_receive = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 5}]},
        headers={**auth_headers, "X-Reason": "Recepcion parcial"},
    )
    assert partial_receive.status_code == status.HTTP_200_OK
    partial_data = partial_receive.json()
    assert partial_data["status"] == "PARCIAL"

    devices_after_partial = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after_partial.status_code == status.HTTP_200_OK
    stored_device = next(item for item in devices_after_partial.json() if item["id"] == device_id)
    assert stored_device["quantity"] == 15
    assert Decimal(str(stored_device["costo_unitario"])) == Decimal("950.00")

    complete_receive = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 5}]},
        headers={**auth_headers, "X-Reason": "Recepcion final"},
    )
    assert complete_receive.status_code == status.HTTP_200_OK
    assert complete_receive.json()["status"] == "COMPLETADA"

    return_response = client.post(
        f"/purchases/{order_id}/returns",
        json={"device_id": device_id, "quantity": 2, "reason": "Equipo danado"},
        headers={**auth_headers, "X-Reason": "Devolucion proveedor"},
    )
    assert return_response.status_code == status.HTTP_200_OK

    inventory_after_return = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert inventory_after_return.status_code == status.HTTP_200_OK
    device_post_return = next(item for item in inventory_after_return.json() if item["id"] == device_id)
    assert device_post_return["quantity"] == 18

    movements = list(
        db_session.execute(
            select(models.InventoryMovement)
            .where(models.InventoryMovement.device_id == device_id)
            .order_by(models.InventoryMovement.created_at)
        ).scalars()
    )
    assert len(movements) == 3
    received_movements = [m for m in movements if m.movement_type == models.MovementType.IN]
    assert {movement.quantity for movement in received_movements} == {5}
    for movement in received_movements:
        assert movement.performed_by_id == user_id
        assert movement.comment is not None and "Proveedor Mayorista" in movement.comment
        assert "Recepción OC" in movement.comment
    return_movement = next(m for m in movements if m.movement_type == models.MovementType.OUT)
    assert return_movement.quantity == 2
    assert return_movement.performed_by_id == user_id
    assert "Devolución proveedor" in return_movement.comment
    assert "Proveedor Mayorista" in return_movement.comment

    legacy_rows = db_session.execute(
        text(
            """
            SELECT tipo_movimiento, cantidad, comentario, usuario_id
            FROM movimientos_inventario
            WHERE producto_id = :device_id
            ORDER BY fecha
            """
        ),
        {"device_id": device_id},
    ).mappings().all()
    assert len(legacy_rows) == len(movements)
    assert {row["tipo_movimiento"] for row in legacy_rows} == {
        movement.movement_type.value for movement in movements
    }
    assert all(row["usuario_id"] == user_id for row in legacy_rows)
    assert any("Proveedor Mayorista" in row["comentario"] for row in legacy_rows)

    settings.enable_purchases_sales = False


def test_purchase_cancellation_reverts_inventory_and_records_movement(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Motivo compras"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Serial", "location": "GDL", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-SERIAL-01",
            "name": "Equipo con serie",
            "quantity": 0,
            "unit_price": 2500.0,
            "costo_unitario": 2000.0,
            "margen_porcentaje": 10.0,
            "serial": "SERIE-UNICA-001",
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    order_payload = {
        "store_id": store_id,
        "supplier": "Proveedor Serializado",
        "items": [
            {"device_id": device_id, "quantity_ordered": 1, "unit_cost": 1800.0},
        ],
    }
    order_response = client.post("/purchases", json=order_payload, headers=auth_headers)
    assert order_response.status_code == status.HTTP_201_CREATED
    order_id = order_response.json()["id"]

    receive_response = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 1}]},
        headers={**auth_headers, "X-Reason": "Recepcion serial"},
    )
    assert receive_response.status_code == status.HTTP_200_OK

    device_record = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert device_record.quantity == 1

    cancel_response = client.post(
        f"/purchases/{order_id}/cancel",
        headers={**auth_headers, "X-Reason": "Proveedor cancela"},
    )
    assert cancel_response.status_code == status.HTTP_200_OK
    assert cancel_response.json()["status"] == "CANCELADA"

    updated_device = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert updated_device.quantity == 0
    assert Decimal(str(updated_device.costo_unitario)) == Decimal("0.00")

    movements = list(
        db_session.execute(
            select(models.InventoryMovement)
            .where(models.InventoryMovement.device_id == device_id)
            .order_by(models.InventoryMovement.created_at)
        ).scalars()
    )
    assert len(movements) == 2
    reversal = next(m for m in movements if m.movement_type == models.MovementType.OUT)
    assert reversal.quantity == 1
    assert reversal.performed_by_id == user_id
    assert "Reversión OC" in reversal.comment
    assert "Proveedor Serializado" in reversal.comment
    assert "Serie: SERIE-UNICA-001" in reversal.comment

    settings.enable_purchases_sales = False


def test_purchase_records_and_vendor_statistics(client, db_session):
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Gestion compras"}

    vendor_response = client.post(
        "/purchases/vendors",
        json={
            "nombre": "Proveedor Integrado",
            "telefono": "555-0101",
            "correo": "ventas@integrado.mx",
            "direccion": "Av. Central 101",
            "tipo": "Mayorista",
        },
        headers=base_headers,
    )
    assert vendor_response.status_code == status.HTTP_201_CREATED
    vendor_id = vendor_response.json()["id_proveedor"]

    store_response = client.post(
        "/stores",
        json={"name": "Compras Norte", "location": "MTY", "timezone": "America/Mexico_City"},
        headers=base_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "PRC-001",
            "name": "Equipo corporativo",
            "quantity": 5,
            "unit_price": 1500.0,
            "costo_unitario": 900.0,
            "margen_porcentaje": 20.0,
        },
        headers=base_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    record_payload = {
        "proveedor_id": vendor_id,
        "forma_pago": "TRANSFERENCIA",
        "impuesto_tasa": 0.16,
        "items": [
            {"producto_id": device_id, "cantidad": 3, "costo_unitario": 850.0},
            {"producto_id": device_id, "cantidad": 1, "costo_unitario": 800.0},
        ],
    }
    record_response = client.post(
        "/purchases/records",
        json=record_payload,
        headers=base_headers,
    )
    assert record_response.status_code == status.HTTP_201_CREATED
    record = record_response.json()
    assert record["proveedor_id"] == vendor_id
    assert Decimal(str(record["total"])) > Decimal(str(record["subtotal"]))
    assert len(record["items"]) == 2

    list_response = client.get(
        "/purchases/records",
        params={"proveedor_id": vendor_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    listed = list_response.json()
    assert any(entry["id_compra"] == record["id_compra"] for entry in listed)

    history_response = client.get(
        f"/purchases/vendors/{vendor_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_response.status_code == status.HTTP_200_OK
    history_payload = history_response.json()
    assert history_payload["proveedor"]["id_proveedor"] == vendor_id
    assert history_payload["registros"] >= 1

    csv_response = client.get(
        "/purchases/vendors/export/csv",
        headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte proveedores"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"] == "text/csv"

    pdf_response = client.get(
        "/purchases/records/export/pdf",
        headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte compras"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    excel_response = client.get(
        "/purchases/records/export/xlsx",
        headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte compras"},
    )
    assert excel_response.status_code == status.HTTP_200_OK
    assert (
        excel_response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    stats_response = client.get(
        "/purchases/statistics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stats_response.status_code == status.HTTP_200_OK
    stats_payload = stats_response.json()
    assert stats_payload["compras_registradas"] >= 1
    assert stats_payload["total"] >= float(record["total"])

    status_response = client.post(
        f"/purchases/vendors/{vendor_id}/status",
        json={"estado": "inactivo"},
        headers=base_headers,
    )
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["estado"].lower() == "inactivo"

    settings.enable_purchases_sales = False
