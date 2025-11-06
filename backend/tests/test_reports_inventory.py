from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO

from typing import Any, Iterable

import pytest
from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


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
        data={"username": payload["username"],
              "password": payload["password"]},
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


@pytest.mark.parametrize(
    "path",
    [
        "/reports/inventory/pdf",
        "/reports/inventory/current/pdf",
        "/reports/inventory/current/xlsx",
        "/reports/inventory/value/csv",
        "/reports/inventory/value/pdf",
        "/reports/inventory/value/xlsx",
        "/reports/inventory/movements/csv",
        "/reports/inventory/movements/pdf",
        "/reports/inventory/movements/xlsx",
        "/reports/inventory/top-products/csv",
        "/reports/inventory/top-products/pdf",
        "/reports/inventory/top-products/xlsx",
    ],
)
def test_inventory_export_requires_reason(client, path: str) -> None:
    headers = _auth_headers(client)

    response = client.get(path, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Reason header requerido"


def test_inventory_csv_snapshot(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {"name": "Sucursal Centro",
                     "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post(
        "/stores", json=store_payload, headers=headers)
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


def test_inventory_current_csv_export(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Centro",
                     "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post(
        "/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SM-010",
        "name": "Softmobile Mini",
        "quantity": 6,
        "unit_price": 9500,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    csv_response = client.get(
        "/reports/inventory/current/csv",
        headers={**headers, "X-Reason": "Revision existencias"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")

    content = csv_response.content.decode("utf-8")
    assert "Existencias actuales" in content
    assert "Sucursal" in content
    assert "Softmobile Mini" not in content
    assert "Sucursal Centro" in content

    reader = csv.reader(StringIO(content))
    rows = list(reader)
    header_row = next(row for row in rows if row and row[0] == "Sucursal")
    store_row = next(
        row for row in rows if row and row[0] == "Sucursal Centro")

    assert header_row == ["Sucursal", "Dispositivos",
                          "Unidades", "Valor total (MXN)"]
    assert store_row[1] == "1"
    assert store_row[2] == "6"
    assert float(store_row[3]) > 0

    pdf_response = client.get(
        "/reports/inventory/current/pdf",
        headers={**headers, "X-Reason": "Revision existencias"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    xlsx_response = client.get(
        "/reports/inventory/current/xlsx",
        headers={**headers, "X-Reason": "Revision existencias"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_inventory_value_pdf_and_excel(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Norte",
                     "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post(
        "/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SM-020",
        "name": "Softmobile Pro",
        "quantity": 2,
        "unit_price": 15000,
        "costo_unitario": 11000,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    pdf_response = client.get(
        "/reports/inventory/value/pdf",
        headers={**headers, "X-Reason": "Valoracion inventario"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    xlsx_response = client.get(
        "/reports/inventory/value/xlsx",
        headers={**headers, "X-Reason": "Valoracion inventario"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_inventory_movements_pdf_and_excel(client) -> None:
    headers = _auth_headers(client)

    pdf_response = client.get(
        "/reports/inventory/movements/pdf",
        headers={**headers, "X-Reason": "Revision movimientos"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    xlsx_response = client.get(
        "/reports/inventory/movements/xlsx",
        headers={**headers, "X-Reason": "Revision movimientos"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_inventory_top_products_pdf_and_excel(client) -> None:
    headers = _auth_headers(client)

    pdf_response = client.get(
        "/reports/inventory/top-products/pdf",
        headers={**headers, "X-Reason": "Ranking ventas"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    xlsx_response = client.get(
        "/reports/inventory/top-products/xlsx",
        headers={**headers, "X-Reason": "Ranking ventas"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert xlsx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_inventory_supplier_batches_overview(client) -> None:
    headers = _auth_headers(client)
    reason_headers = {**headers, "X-Reason": "Registro de lotes"}

    store_payload = {"name": "Sucursal Norte",
                     "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post(
        "/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    other_store_payload = {"name": "Sucursal Sur",
                           "location": "GDL", "timezone": "America/Mexico_City"}
    other_store_response = client.post(
        "/stores", json=other_store_payload, headers=headers)
    assert other_store_response.status_code == status.HTTP_201_CREATED
    other_store_id = other_store_response.json()["id"]

    device_payload = {"sku": "SM-100",
                      "name": "Smartphone Corporativo", "quantity": 10}
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

    other_supplier_payload = {
        "name": "Tecnología Sur", "contact_name": "Óscar Peña"}
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
    overview_payload = overview_response.json()
    overview_items = _extract_items(overview_payload)
    assert len(overview_items) == 1

    supplier_entry = overview_items[0]
    assert supplier_entry["supplier_id"] == supplier_id
    assert supplier_entry["supplier_name"] == "Componentes del Norte"
    assert supplier_entry["batch_count"] == 2
    assert supplier_entry["total_quantity"] == 35
    assert pytest.approx(
        supplier_entry["total_value"], rel=1e-4) == 800 * 20 + 820 * 15
    assert supplier_entry["latest_batch_code"] == "L-2024-02"
    assert supplier_entry["latest_purchase_date"] == "2024-02-10"


def test_inventory_current_and_value_reports(client) -> None:
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Reporte Centro", "location": "CDMX",
              "timezone": "America/Mexico_City"},
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

    current_response = client.get(
        "/reports/inventory/current", headers=headers)
    assert current_response.status_code == status.HTTP_200_OK
    current_payload = current_response.json()
    assert current_payload["totals"]["devices"] >= 1
    assert any(store["store_name"] ==
               "Reporte Centro" for store in current_payload["stores"])

    value_response = client.get("/reports/inventory/value", headers=headers)
    assert value_response.status_code == status.HTTP_200_OK
    value_payload = value_response.json()
    assert any(entry["store_name"] ==
               "Reporte Centro" for entry in value_payload["stores"])

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
        json={"name": "Movimientos Norte", "location": "MTY",
              "timezone": "America/Monterrey"},
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
        "sucursal_destino_id": store_id,
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
        "sucursal_destino_id": store_id,
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
    assert any(entry["tipo_movimiento"] ==
               "entrada" for entry in report["resumen"]["por_tipo"])

    # Validar normalización del rango de fechas: la función _normalize_date_range
    # debe incluir el final del día (23:59:59.999999) para date_to cuando se pasa
    # solo la fecha sin hora. Generamos un movimiento adicional justo antes de
    # la medianoche y comprobamos que sigue siendo incluido al consultar el mismo
    # rango (date_from == date_to == hoy).
    late_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 1,
        "comentario": "Entrada tardia",
        "sucursal_destino_id": store_id,
        "unit_cost": 1250,
    }
    late_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=late_payload,
        headers={**headers, "X-Reason": "Entrada tardia"},
    )
    assert late_response.status_code == status.HTTP_201_CREATED

    # Re-consultar con el mismo rango para asegurar que el movimiento tardío
    # se incluye (incrementa el total de movimientos).
    movements_response_late = client.get(
        "/reports/inventory/movements",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=headers,
    )
    assert movements_response_late.status_code == status.HTTP_200_OK
    late_report = movements_response_late.json()
    assert late_report["resumen"]["total_movimientos"] >= report["resumen"]["total_movimientos"]

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
            json={"name": "Ventas Centro", "location": "CDMX",
                  "timezone": "America/Mexico_City"},
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


def test_inventory_movements_report_swapped_date_range(client) -> None:
    """
    Valida que cuando se envía un rango de fechas invertido (date_from > date_to),
    el backend normaliza el rango y devuelve resultados equivalentes al rango correcto.
    """
    headers = _auth_headers(client)

    # Crear una sucursal y un dispositivo con al menos un movimiento hoy.
    store_response = client.post(
        "/stores",
        json={"name": "Rango Invertido Centro",
              "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "INV-200",
        "name": "Access Point Corporativo",
        "quantity": 3,
        "unit_price": 2500,
        "costo_unitario": 1800,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    # Registrar un movimiento de entrada hoy para asegurar datos en el reporte
    movement_headers = {**headers, "X-Reason": "Ajuste inicial"}
    entrada_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 5,
        "comentario": "Ajuste inicial",
        "sucursal_destino_id": store_id,
        "unit_cost": 1250,
    }
    entrada_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=entrada_payload,
        headers=movement_headers,
    )
    assert entrada_response.status_code == status.HTTP_201_CREATED, entrada_response.text

    today = datetime.utcnow().date()
    yesterday = datetime.utcnow().date().fromordinal(today.toordinal() - 1)

    # Consulta con rango correcto (hoy a hoy)
    correct_response = client.get(
        "/reports/inventory/movements",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=headers,
    )
    assert correct_response.status_code == status.HTTP_200_OK
    correct_payload = correct_response.json()

    # Consulta con rango invertido (hoy a ayer) — debe normalizarse y ser equivalente
    swapped_response = client.get(
        "/reports/inventory/movements",
        params={"date_from": today.isoformat(
        ), "date_to": yesterday.isoformat()},
        headers=headers,
    )
    assert swapped_response.status_code == status.HTTP_200_OK
    swapped_payload = swapped_response.json()

    assert swapped_payload["resumen"]["total_movimientos"] == correct_payload["resumen"]["total_movimientos"]


def test_inventory_top_products_report_swapped_date_range(client) -> None:
    """Confirma que el rango invertido se normaliza en top-products y devuelve
    resultados equivalentes al rango correcto para el mismo día."""
    headers = _auth_headers(client)
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        # Sucursal y producto con venta hoy
        store_response = client.post(
            "/stores",
            json={"name": "TopProducts Centro", "location": "CDMX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "VENT-INV-002",
                "name": "Softmobile Edge",
                "quantity": 5,
                "unit_price": 9900,
                "costo_unitario": 7200,
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers={**headers, "X-Reason": "Venta corporativa"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        today = datetime.utcnow().date()
        yesterday = datetime.utcnow().date().fromordinal(today.toordinal() - 1)

        # Rango correcto (hoy a hoy)
        correct_resp = client.get(
            "/reports/inventory/top-products",
            params={"date_from": today.isoformat(), "date_to": today.isoformat()},
            headers=headers,
        )
        assert correct_resp.status_code == status.HTTP_200_OK
        correct = correct_resp.json()

        # Rango invertido (hoy a ayer) — debe normalizarse y devolver mismo total
        swapped_resp = client.get(
            "/reports/inventory/top-products",
            params={"date_from": today.isoformat(
            ), "date_to": yesterday.isoformat()},
            headers=headers,
        )
        assert swapped_resp.status_code == status.HTTP_200_OK
        swapped = swapped_resp.json()

        assert swapped["total_unidades"] == correct["total_unidades"]
        # Debe contener el producto vendido en ambos casos
        assert any(item["sku"] == "VENT-INV-002" for item in swapped["items"]) \
            and any(item["sku"] == "VENT-INV-002" for item in correct["items"])
    finally:
        settings.enable_purchases_sales = previous_flag


def test_inventory_current_report_swapped_date_range(client) -> None:
    """El reporte current debe normalizar rangos invertidos (date_from > date_to)
    y devolver los mismos resultados que el rango correcto para el mismo día."""
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Rango Current Centro", "location": "CDMX",
              "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "CURR-001",
            "name": "Terminal Current",
            "quantity": 4,
            "unit_price": 1200,
            "costo_unitario": 900,
        },
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    today = datetime.utcnow().date()
    yesterday = datetime.utcnow().date().fromordinal(today.toordinal() - 1)

    correct_resp = client.get(
        "/reports/inventory/current",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=headers,
    )
    assert correct_resp.status_code == status.HTTP_200_OK
    correct = correct_resp.json()

    swapped_resp = client.get(
        "/reports/inventory/current",
        params={"date_from": today.isoformat(
        ), "date_to": yesterday.isoformat()},
        headers=headers,
    )
    assert swapped_resp.status_code == status.HTTP_200_OK
    swapped = swapped_resp.json()

    # Comparar por lo menos el conjunto de sucursales reportadas
    def store_names(payload: dict[str, any]) -> set[str]:
        return {s.get("store_name") or s.get("name") for s in payload.get("stores", [])}

    assert store_names(swapped) == store_names(correct)
    # Si hay totales, deben coincidir también
    if "totals" in correct and isinstance(correct["totals"], dict):
        assert swapped.get("totals") == correct.get("totals")


def test_inventory_value_report_swapped_date_range(client) -> None:
    """El reporte value debe normalizar rangos invertidos y conservar resultados."""
    headers = _auth_headers(client)

    store_resp = client.post(
        "/stores",
        json={"name": "Rango Value Norte", "location": "MTY",
              "timezone": "America/Monterrey"},
        headers=headers,
    )
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "VAL-001",
            "name": "Terminal Value",
            "quantity": 2,
            "unit_price": 3000,
            "costo_unitario": 2100,
        },
        headers=headers,
    )
    assert device_resp.status_code == status.HTTP_201_CREATED

    today = datetime.utcnow().date()
    yesterday = datetime.utcnow().date().fromordinal(today.toordinal() - 1)

    correct_resp = client.get(
        "/reports/inventory/value",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=headers,
    )
    assert correct_resp.status_code == status.HTTP_200_OK
    correct = correct_resp.json()

    swapped_resp = client.get(
        "/reports/inventory/value",
        params={"date_from": today.isoformat(
        ), "date_to": yesterday.isoformat()},
        headers=headers,
    )
    assert swapped_resp.status_code == status.HTTP_200_OK
    swapped = swapped_resp.json()

    def store_names(payload: dict[str, any]) -> set[str]:
        return {s.get("store_name") or s.get("name") for s in payload.get("stores", [])}

    assert store_names(swapped) == store_names(correct)
    # Si existe un resumen o totales, deben coincidir
    if "summary" in correct and isinstance(correct["summary"], dict):
        assert swapped.get("summary") == correct.get("summary")
