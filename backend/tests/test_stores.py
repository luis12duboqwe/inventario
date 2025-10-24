import pytest
from fastapi import status

from backend.app.config import settings

from backend.app.core.roles import ADMIN, OPERADOR


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion de prueba"}


def _create_operator_token(client, admin_headers: dict[str, str]) -> str:
    payload = {
        "username": "mov_operator",
        "password": "MovOperador123*",
        "full_name": "Operador Inventario",
        "roles": [OPERADOR],
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"Authorization": admin_headers["Authorization"]},
    )
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_inventory_flow(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-001", "name": "Galaxy S24", "quantity": 5, "unit_price": 15000.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    low_stock_payload = {"sku": "SKU-LOW", "name": "Moto G", "quantity": 2, "unit_price": 4500.0}
    low_stock_response = client.post(
        f"/stores/{store_id}/devices", json=low_stock_payload, headers=headers
    )
    assert low_stock_response.status_code == status.HTTP_201_CREATED
    low_stock_id = low_stock_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 10,
        "comentario": "Inventario inicial",
    }
    movement_headers = {**headers, "X-Reason": movement_payload["comentario"]}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers=movement_headers,
    )
    assert movement_response.status_code == status.HTTP_201_CREATED
    movement_data = movement_response.json()
    assert movement_data["producto_id"] == device_id
    assert movement_data["sucursal_destino_id"] == store_id

    summary_response = client.get("/inventory/summary", headers=headers)
    assert summary_response.status_code == status.HTTP_200_OK
    summary_payload = summary_response.json()
    summary_items = summary_payload["items"]
    assert summary_items[0]["total_items"] == 17
    assert summary_items[0]["total_value"] == 15 * 15000.0 + 2 * 4500.0
    assert any(device["unit_price"] == 15000.0 for device in summary_items[0]["devices"])
    assert any(device["inventory_value"] == 2 * 4500.0 for device in summary_items[0]["devices"])

    sync_response = client.post("/sync/run", json={"store_id": store_id}, headers=headers)
    assert sync_response.status_code == status.HTTP_200_OK

    logs_response = client.get("/reports/audit", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    logs_items = logs_response.json()["items"]
    assert any(log["action"] == "inventory_movement" for log in logs_items)

    metrics_response = client.get("/reports/metrics", headers=headers)
    assert metrics_response.status_code == status.HTTP_200_OK
    metrics = metrics_response.json()
    assert metrics["totals"]["total_units"] == 17
    assert metrics["totals"]["total_value"] == summary_items[0]["total_value"]
    assert metrics["top_stores"][0]["store_id"] == store_id
    low_stock_devices = metrics["low_stock_devices"]
    assert any(device["device_id"] == low_stock_id for device in low_stock_devices)
    audit_alerts = metrics["audit_alerts"]
    assert audit_alerts["total"] == audit_alerts["critical"] + audit_alerts["warning"] + audit_alerts["info"]
    assert audit_alerts["has_alerts"] == (
        audit_alerts["critical"] > 0 or audit_alerts["warning"] > 0
    )
    assert isinstance(audit_alerts["highlights"], list)


def test_device_filters_by_search_and_state(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    devices = [
        {
            "sku": "SKU-IPHONE",
            "name": "iPhone 15 Pro",
            "quantity": 4,
            "unit_price": 32500.0,
            "imei": "490154203237518",
            "modelo": "iPhone 15 Pro",
            "estado_comercial": "A",
        },
        {
            "sku": "SKU-MOTO",
            "name": "Moto Edge 50",
            "quantity": 6,
            "unit_price": 14500.0,
            "serial": "MOTO-EDGE-50-XYZ",
            "estado_comercial": "B",
        },
        {
            "sku": "SKU-GALAXY",
            "name": "Galaxy S24",
            "quantity": 8,
            "unit_price": 28999.0,
            "modelo": "Galaxy S24",
            "estado_comercial": "nuevo",
        },
    ]

    for payload in devices:
        create_response = client.post(f"/stores/{store_id}/devices", json=payload, headers=headers)
        assert create_response.status_code == status.HTTP_201_CREATED

    search_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"search": "iphone"},
    )
    assert search_response.status_code == status.HTTP_200_OK
    search_payload = search_response.json()
    search_results = search_payload["items"]
    assert len(search_results) == 1
    assert search_results[0]["sku"] == "SKU-IPHONE"

    estado_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"estado": "B"},
    )
    assert estado_response.status_code == status.HTTP_200_OK
    estado_payload = estado_response.json()
    estado_results = estado_payload["items"]
    assert len(estado_results) == 1
    assert all(device["estado_comercial"] == "B" for device in estado_results)

    mixed_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"search": "galaxy", "estado": "nuevo"},
    )
    assert mixed_response.status_code == status.HTTP_200_OK
    mixed_payload = mixed_response.json()
    mixed_results = mixed_payload["items"]
    assert len(mixed_results) == 1
    assert mixed_results[0]["sku"] == "SKU-GALAXY"

    invalid_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"estado": "Z"},
    )
    assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_requires_authentication(client) -> None:
    store_payload = {"name": "Sucursal Sin Token"}
    response = client.post("/stores", json=store_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_inventory_movement_rejects_negative_stock(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Inventario", "location": "GDL", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-NEG", "name": "Tablet Pro", "quantity": 3, "unit_price": 4500.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "salida",
        "cantidad": 5,
        "comentario": "Solicitud no permitida",
    }

    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers={**headers, "X-Reason": movement_payload["comentario"]},
    )
    assert movement_response.status_code == status.HTTP_409_CONFLICT
    assert "Stock insuficiente" in movement_response.json()["detail"]


def test_inventory_movement_requires_comment_length(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Comentarios", "location": "MTY", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-CMT", "name": "Router", "quantity": 4, "unit_price": 1200.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 1,
        "comentario": "hey",
    }

    response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers={**headers, "X-Reason": "Operacion de prueba"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = response.json()["detail"]
    assert any(
        "El comentario debe tener al menos 5 caracteres." in error.get("msg", "")
        for error in detail
    )


def test_inventory_movement_requires_comment_matching_reason(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Motivos", "location": "LEON", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-MTV", "name": "Monitor", "quantity": 4, "unit_price": 5200.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "salida",
        "cantidad": 1,
        "comentario": "Salida controlada",
    }

    response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = response.json()["detail"]
    assert detail["code"] == "reason_comment_mismatch"
    assert "coincidir" in detail["message"]


def test_manual_adjustment_triggers_alerts(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Ajustes", "location": "PUE", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-AJUSTE", "name": "Scanner", "quantity": 12, "unit_price": 2800.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    adjustment_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "ajuste",
        "cantidad": 2,
        "comentario": "Ajuste conteo fisico",
    }
    adjustment_headers = {**headers, "X-Reason": adjustment_payload["comentario"]}
    adjustment_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=adjustment_payload,
        headers=adjustment_headers,
    )
    assert adjustment_response.status_code == status.HTTP_201_CREATED

    devices_response = client.get(f"/stores/{store_id}/devices", headers=headers)
    assert devices_response.status_code == status.HTTP_200_OK
    devices = devices_response.json()["items"]
    adjusted = next(device for device in devices if device["id"] == device_id)
    assert adjusted["quantity"] == adjustment_payload["cantidad"]

    logs_response = client.get("/reports/audit", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    logs = logs_response.json()["items"]
    device_logs = {
        log["action"]: log
        for log in logs
        if log["entity_type"] == "device" and log["entity_id"] == str(device_id)
    }

    assert "inventory_movement" in device_logs
    assert adjustment_payload["comentario"] in device_logs["inventory_movement"]["details"]

    assert "inventory_adjustment_alert" in device_logs
    adjustment_details = device_logs["inventory_adjustment_alert"]["details"].lower()
    assert "inconsistencia" in adjustment_details
    assert device_logs["inventory_adjustment_alert"]["severity"] == "warning"

    assert "inventory_low_stock_alert" in device_logs
    low_stock_log = device_logs["inventory_low_stock_alert"]
    assert low_stock_log["severity"] == "critical"
    assert f"umbral={settings.inventory_low_stock_threshold}" in low_stock_log["details"]


def test_inventory_movement_response_includes_required_fields(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Campos", "location": "PUE", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-CAMP", "name": "Switch", "quantity": 2, "unit_price": 950.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 1,
        "comentario": "Ingreso manual",
    }

    response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers={**headers, "X-Reason": movement_payload["comentario"]},
    )
    assert response.status_code == status.HTTP_201_CREATED

    payload = response.json()
    for key in [
        "id",
        "producto_id",
        "tipo_movimiento",
        "cantidad",
        "fecha",
        "usuario",
        "sucursal_origen",
        "sucursal_destino",
        "comentario",
    ]:
        assert key in payload, f"Falta el campo obligatorio {key}"

    assert payload["usuario"] == "Admin General"
    assert payload["sucursal_destino"] == store_payload["name"]


def test_operator_can_register_movements_but_not_view_inventory(client) -> None:
    admin_headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Operador", "location": "GDL", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=admin_headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-OP-001", "name": "Scanner", "quantity": 5, "unit_price": 2500.0}
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=admin_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    operator_token = _create_operator_token(client, admin_headers)

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "salida",
        "cantidad": 1,
        "comentario": "Registrar salida",
    }
    operator_headers = {"Authorization": f"Bearer {operator_token}", "X-Reason": movement_payload["comentario"]}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers=operator_headers,
    )
    assert movement_response.status_code == status.HTTP_201_CREATED
    movement_data = movement_response.json()
    assert movement_data["producto_id"] == device_id
    assert movement_data["sucursal_origen_id"] == store_id

    summary_response = client.get(
        "/inventory/summary",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert summary_response.status_code == status.HTTP_403_FORBIDDEN

    devices_response = client.get(
        f"/stores/{store_id}/devices",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert devices_response.status_code == status.HTTP_403_FORBIDDEN


def test_sale_updates_inventory_value(client) -> None:
    settings.enable_purchases_sales = True
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Ventas", "location": "QRO", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-VENTA", "name": "Smartwatch", "quantity": 10, "unit_price": 1000.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "items": [
            {"device_id": device_id, "quantity": 2},
        ],
        "payment_method": "EFECTIVO",
    }

    sale_response = client.post("/sales", json=sale_payload, headers=headers)
    assert sale_response.status_code == status.HTTP_201_CREATED

    device_list = client.get(f"/stores/{store_id}/devices", headers=headers)
    assert device_list.status_code == status.HTTP_200_OK
    devices = device_list.json()["items"]
    assert any(device["id"] == device_id and device["quantity"] == 8 for device in devices)

    store_detail = client.get(f"/stores/{store_id}", headers=headers)
    assert store_detail.status_code == status.HTTP_200_OK
    assert store_detail.json()["inventory_value"] == pytest.approx(8000.0)


def test_store_update_changes_core_fields(client) -> None:
    headers = _auth_headers(client)

    create_payload = {
        "name": "Sucursal Centro",
        "location": "CDMX",
        "timezone": "America/Mexico_City",
        "code": "SUC-010",
    }
    store_response = client.post("/stores", json=create_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    update_payload = {
        "name": "Sucursal Centro Renovada",
        "location": "Av. Reforma 123",
        "status": "inactiva",
        "code": "SUC-011",
        "timezone": "America/Bogota",
    }
    update_response = client.put(
        f"/stores/{store_id}", json=update_payload, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()
    assert data["name"] == update_payload["name"]
    assert data["location"] == update_payload["location"]
    assert data["status"] == "inactiva"
    assert data["code"] == update_payload["code"]
    assert data["timezone"] == update_payload["timezone"]

    detail_response = client.get(f"/stores/{store_id}", headers=headers)
    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert detail["status"] == "inactiva"
    assert detail["code"] == update_payload["code"]
    assert detail["location"] == update_payload["location"]
