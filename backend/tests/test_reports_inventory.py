from __future__ import annotations

import csv
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

