from pathlib import Path

import pytest
from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.services import backups as backup_services


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


def test_backup_generation_and_pdf(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-XYZ",
        "name": "iPhone 15",
        "quantity": 3,
        "unit_price": 18999.99,
        "imei": "359876543210123",
        "serial": "APL-000123",
        "marca": "Apple",
        "modelo": "iPhone 15 Pro",
        "color": "Titanio",
        "capacidad_gb": 256,
        "proveedor": "Distribuidor Apple",
        "costo_unitario": 14500,
        "margen_porcentaje": 23.5,
        "garantia_meses": 12,
        "lote": "APL-2024-01",
        "fecha_compra": "2024-02-10",
    }
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED

    backup_response = client.post("/backups/run", json={"nota": "Respaldo QA"}, headers=headers)
    assert backup_response.status_code == status.HTTP_201_CREATED
    backup_data = backup_response.json()

    pdf_path = Path(backup_data["pdf_path"])
    archive_path = Path(backup_data["archive_path"])
    assert pdf_path.exists()
    assert archive_path.exists()
    assert backup_data["total_size_bytes"] == pdf_path.stat().st_size + archive_path.stat().st_size

    history_response = client.get("/backups/history", headers=headers)
    assert history_response.status_code == status.HTTP_200_OK
    history = history_response.json()
    assert history
    assert history[0]["notes"] == "Respaldo QA"

    pdf_response = client.get(
        "/reports/inventory/pdf",
        headers={**headers, "X-Reason": "Descarga inventario QA"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def test_inventory_pdf_requires_reason(client) -> None:
    headers = _auth_headers(client)

    response = client.get("/reports/inventory/pdf", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Reason header requerido"


def test_render_snapshot_pdf_includes_financial_and_catalog_details() -> None:
    snapshot = {
        "stores": [
            {
                "name": "Sucursal Centro",
                "timezone": "America/Mexico_City",
                "inventory_value": 48000.0,
                "device_count": 1,
                "total_units": 4,
                "devices": [
                    {
                        "sku": "SM-001",
                        "name": "Smartphone Elite",
                        "quantity": 4,
                        "unit_price": 12000.0,
                        "inventory_value": 48000.0,
                        "imei": "123456789012345",
                        "serial": "SN-0001",
                        "marca": "Softmobile",
                        "modelo": "Elite X",
                        "proveedor": "Proveedor Uno",
                        "color": "Negro",
                        "capacidad_gb": 256,
                        "estado_comercial": "nuevo",
                        "lote": "L-001",
                        "fecha_compra": "2024-01-20",
                        "garantia_meses": 24,
                        "costo_unitario": 8500.0,
                        "margen_porcentaje": 30.0,
                    }
                ],
            }
        ],
        "summary": {
            "store_count": 1,
            "device_records": 1,
            "total_units": 4,
            "inventory_value": 48000.0,
        },
    }

    table_data, store_total = backup_services._build_financial_table(snapshot["stores"][0]["devices"])  # noqa: SLF001
    detail_table = backup_services._build_catalog_detail_table(snapshot["stores"][0]["devices"])  # noqa: SLF001

    assert table_data[0] == [
        "SKU",
        "Nombre",
        "Cantidad",
        "Precio",
        "Valor total",
        "IMEI",
        "Serie",
        "Marca",
        "Modelo",
        "Proveedor",
    ]
    assert store_total == 48000.0
    assert table_data[1][3] == "$12,000.00"
    assert table_data[1][4] == "$48,000.00"
    assert table_data[1][5] == "123456789012345"
    assert table_data[1][8] == "Elite X"
    assert table_data[1][9] == "Proveedor Uno"

    assert detail_table[0] == [
        "SKU",
        "Color",
        "Capacidad (GB)",
        "Estado",
        "Lote",
        "Fecha compra",
        "Garantía (meses)",
        "Costo unitario",
        "Margen (%)",
    ]
    assert detail_table[1][1] == "Negro"
    assert detail_table[1][2] == "256"
    assert detail_table[1][5] == "2024-01-20"
    assert detail_table[1][6] == "24"
    assert detail_table[1][7] == "$8,500.00"
    assert detail_table[1][8] == "30.00%"

    pdf_bytes = backup_services.render_snapshot_pdf(snapshot)
    assert pdf_bytes.startswith(b"%PDF")


def test_inventory_snapshot_summary_includes_store_values(client, db_session) -> None:
    headers = _auth_headers(client)

    store_centro = client.post(
        "/stores",
        json={"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_centro.status_code == status.HTTP_201_CREATED
    store_centro_id = store_centro.json()["id"]

    store_norte = client.post(
        "/stores",
        json={"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"},
        headers=headers,
    )
    assert store_norte.status_code == status.HTTP_201_CREATED
    store_norte_id = store_norte.json()["id"]

    device_centro_a = {
        "sku": "SM-C-001",
        "name": "Smartphone Pro",
        "quantity": 3,
        "unit_price": 15000,
    }
    device_centro_b = {
        "sku": "SM-C-002",
        "name": "Tablet Ejecutiva",
        "quantity": 2,
        "unit_price": 8000,
    }
    device_norte = {
        "sku": "SM-N-001",
        "name": "Accesorio Norte",
        "quantity": 4,
        "unit_price": 1200,
    }

    response_a = client.post(
        f"/stores/{store_centro_id}/devices",
        json=device_centro_a,
        headers=headers,
    )
    assert response_a.status_code == status.HTTP_201_CREATED
    response_b = client.post(
        f"/stores/{store_centro_id}/devices",
        json=device_centro_b,
        headers=headers,
    )
    assert response_b.status_code == status.HTTP_201_CREATED
    response_norte = client.post(
        f"/stores/{store_norte_id}/devices",
        json=device_norte,
        headers=headers,
    )
    assert response_norte.status_code == status.HTTP_201_CREATED

    snapshot = backup_services.build_inventory_snapshot(db_session)
    summary = snapshot["summary"]

    assert summary["store_count"] == 2
    assert summary["device_records"] == 3
    assert summary["total_units"] == 9
    assert summary["inventory_value"] == pytest.approx(65800.0)

    stores = {store["name"]: store for store in snapshot["stores"]}
    assert stores["Sucursal Centro"]["inventory_value"] == pytest.approx(61000.0)
    assert stores["Sucursal Centro"]["device_count"] == 2
    assert stores["Sucursal Centro"]["total_units"] == 5
    assert stores["Sucursal Norte"]["inventory_value"] == pytest.approx(4800.0)
    assert stores["Sucursal Norte"]["device_count"] == 1
    assert stores["Sucursal Norte"]["total_units"] == 4
