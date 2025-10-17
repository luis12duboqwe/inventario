from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO

import pytest
from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


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
    return {"Authorization": f"Bearer {token}"}


def test_inventory_csv_requires_reason(client) -> None:
    headers = _auth_headers(client)

    response = client.get("/reports/inventory/csv", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Reason header requerido"


def test_inventory_csv_snapshot(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SM-001",
        "name": "Smartphone Elite",
        "quantity": 4,
        "unit_price": 12000,
        "imei": "123456789012345",
        "serial": "SN-0001",
        "marca": "Softmobile",
        "modelo": "Elite X",
        "color": "Negro",
        "capacidad_gb": 256,
        "proveedor": "Proveedor Uno",
        "costo_unitario": 8500,
        "margen_porcentaje": 30,
        "garantia_meses": 24,
        "lote": "L-001",
        "fecha_compra": "2024-01-20",
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    csv_response = client.get(
        "/reports/inventory/csv",
        headers={**headers, "X-Reason": "Conciliacion inventario"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")

    content = csv_response.content.decode("utf-8")
    assert "Inventario corporativo" in content
    assert "SM-001" in content
    assert "Smartphone Elite" in content
    assert "IMEI" in content
    assert "123456789012345" in content
    assert "Elite X" in content
    assert "Proveedor Uno" in content
    assert "8500.00" in content
    assert "30.00" in content
    assert "TOTAL SUCURSAL" in content
    assert "VALOR CONTABLE" in content
    assert "Resumen corporativo" in content
    assert "Inventario consolidado registrado (MXN)" in content
    assert "Inventario consolidado calculado (MXN)" in content

    reader = csv.reader(StringIO(content))
    rows = list(reader)
    header_row = next(row for row in rows if row and row[0] == "SKU")
    device_row = next(row for row in rows if row and row[0] == "SM-001")
    total_row = next(row for row in rows if row and row[0] == "TOTAL SUCURSAL")

    assert len(header_row) == 18
    assert header_row.count("IMEI") == 1
    assert header_row.count("Serie") == 1
    assert header_row.count("Garantía (meses)") == 1
    assert len(device_row) == len(header_row)
    assert len(total_row) == len(header_row)

    imei_index = header_row.index("IMEI")
    serie_index = header_row.index("Serie")
    garantia_index = header_row.index("Garantía (meses)")
    valor_total_index = header_row.index("Valor total")

    assert device_row[imei_index] == "123456789012345"
    assert device_row[serie_index] == "SN-0001"
    assert device_row[garantia_index] == "24"
    assert device_row[valor_total_index] == "48000.00"
    assert total_row[valor_total_index] == "48000.00"


def test_inventory_supplier_batches_overview(client) -> None:
    headers = _auth_headers(client)
    reason_headers = {**headers, "X-Reason": "Registro de lotes"}

    store_payload = {"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    other_store_payload = {"name": "Sucursal Sur", "location": "GDL", "timezone": "America/Mexico_City"}
    other_store_response = client.post("/stores", json=other_store_payload, headers=headers)
    assert other_store_response.status_code == status.HTTP_201_CREATED
    other_store_id = other_store_response.json()["id"]

    device_payload = {"sku": "SM-100", "name": "Smartphone Corporativo", "quantity": 10}
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    supplier_payload = {
        "name": "Componentes del Norte",
        "contact_name": "Laura Díaz",
    }
    supplier_response = client.post(
        "/suppliers",
        json=supplier_payload,
        headers=reason_headers,
    )
    assert supplier_response.status_code == status.HTTP_201_CREATED
    supplier_id = supplier_response.json()["id"]

    other_supplier_payload = {"name": "Tecnología Sur", "contact_name": "Óscar Peña"}
    other_supplier_response = client.post(
        "/suppliers",
        json=other_supplier_payload,
        headers=reason_headers,
    )
    assert other_supplier_response.status_code == status.HTTP_201_CREATED
    other_supplier_id = other_supplier_response.json()["id"]

    first_batch_payload = {
        "model_name": "Smartphone Corporativo",
        "batch_code": "L-2024-01",
        "unit_cost": 800,
        "quantity": 20,
        "purchase_date": "2024-01-15",
        "store_id": store_id,
        "device_id": device_id,
    }
    second_batch_payload = {
        "model_name": "Smartphone Corporativo",
        "batch_code": "L-2024-02",
        "unit_cost": 820,
        "quantity": 15,
        "purchase_date": "2024-02-10",
        "store_id": store_id,
        "device_id": device_id,
    }

    other_store_batch_payload = {
        "model_name": "Accesorio Sur",
        "batch_code": "S-2024-01",
        "unit_cost": 500,
        "quantity": 5,
        "purchase_date": "2024-02-05",
        "store_id": other_store_id,
    }

    create_first = client.post(
        f"/suppliers/{supplier_id}/batches",
        json=first_batch_payload,
        headers=reason_headers,
    )
    assert create_first.status_code == status.HTTP_201_CREATED

    create_second = client.post(
        f"/suppliers/{supplier_id}/batches",
        json=second_batch_payload,
        headers=reason_headers,
    )
    assert create_second.status_code == status.HTTP_201_CREATED

    client.post(
        f"/suppliers/{other_supplier_id}/batches",
        json=other_store_batch_payload,
        headers=reason_headers,
    )

    overview_response = client.get(
        f"/reports/inventory/supplier-batches?store_id={store_id}&limit=3",
        headers=headers,
    )
    assert overview_response.status_code == status.HTTP_200_OK
    overview = overview_response.json()
    assert len(overview) == 1

    supplier_entry = overview[0]
    assert supplier_entry["supplier_id"] == supplier_id
    assert supplier_entry["supplier_name"] == "Componentes del Norte"
    assert supplier_entry["batch_count"] == 2
    assert supplier_entry["total_quantity"] == 35
    assert pytest.approx(supplier_entry["total_value"], rel=1e-4) == 800 * 20 + 820 * 15
    assert supplier_entry["latest_batch_code"] == "L-2024-02"
    assert supplier_entry["latest_purchase_date"] == "2024-02-10"


def test_inventory_current_and_value_reports(client) -> None:
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Reporte Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "REP-001",
        "name": "Router Empresarial",
        "quantity": 8,
        "unit_price": 3200,
        "costo_unitario": 2100,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    current_response = client.get("/reports/inventory/current", headers=headers)
    assert current_response.status_code == status.HTTP_200_OK
    current_payload = current_response.json()
    assert current_payload["totals"]["devices"] >= 1
    assert any(store["store_name"] == "Reporte Centro" for store in current_payload["stores"])

    value_response = client.get("/reports/inventory/value", headers=headers)
    assert value_response.status_code == status.HTTP_200_OK
    value_payload = value_response.json()
    assert any(entry["store_name"] == "Reporte Centro" for entry in value_payload["stores"])

    csv_response = client.get(
        "/reports/inventory/value/csv",
        headers={**headers, "X-Reason": "Exportar valoracion"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert "Reporte Centro" in csv_response.text


def test_inventory_movements_report_and_csv(client) -> None:
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Movimientos Norte", "location": "MTY", "timezone": "America/Monterrey"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "MOV-100",
        "name": "Switch Gestionable",
        "quantity": 12,
        "unit_price": 1800,
        "costo_unitario": 1200,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_headers = {**headers, "X-Reason": "Ajuste inicial"}
    entrada_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 5,
        "comentario": "Ajuste inicial",
        "tienda_destino_id": store_id,
        "unit_cost": 1250,
    }
    entrada_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=entrada_payload,
        headers=movement_headers,
    )
    assert entrada_response.status_code == status.HTTP_201_CREATED

    salida_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "salida",
        "cantidad": 3,
        "comentario": "Salida por venta",
        "tienda_destino_id": store_id,
        "unit_cost": 1800,
    }
    salida_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=salida_payload,
        headers={**headers, "X-Reason": "Salida por venta"},
    )
    assert salida_response.status_code == status.HTTP_201_CREATED

    today = datetime.utcnow().date()
    movements_response = client.get(
        "/reports/inventory/movements",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=headers,
    )
    assert movements_response.status_code == status.HTTP_200_OK
    report = movements_response.json()
    assert report["resumen"]["total_movimientos"] >= 2
    assert any(entry["tipo_movimiento"] == "entrada" for entry in report["resumen"]["por_tipo"])

    csv_response = client.get(
        "/reports/inventory/movements/csv",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers={**headers, "X-Reason": "Exportar movimientos"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert "Movimientos de inventario" in csv_response.text


def test_inventory_top_products_report_and_csv(client) -> None:
    headers = _auth_headers(client)
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        store_response = client.post(
            "/stores",
            json={"name": "Ventas Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_payload = {
            "sku": "VENT-001",
            "name": "Smartphone Corporativo",
            "quantity": 6,
            "unit_price": 9500,
            "costo_unitario": 7000,
        }
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_payload = {
            "store_id": store_id,
            "payment_method": "TARJETA",
            "items": [{"device_id": device_id, "quantity": 2}],
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers={**headers, "X-Reason": "Venta corporativa"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        report_response = client.get(
            "/reports/inventory/top-products",
            headers=headers,
        )
        assert report_response.status_code == status.HTTP_200_OK
        report = report_response.json()
        assert report["total_unidades"] >= 2
        assert any(item["sku"] == "VENT-001" for item in report["items"])

        csv_response = client.get(
            "/reports/inventory/top-products/csv",
            headers={**headers, "X-Reason": "Exportar productos"},
        )
        assert csv_response.status_code == status.HTTP_200_OK
        assert "Smartphone Corporativo" in csv_response.text
    finally:
        settings.enable_purchases_sales = previous_flag

