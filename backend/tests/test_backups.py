import json
import shutil
from pathlib import Path

import pytest
from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.services import backups as backup_services


def _login_headers(client, username: str = "admin", password: str = "MuySegura123") -> dict[str, str]:
    token_response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK, token_response.json()
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code in {
        status.HTTP_201_CREATED,
        status.HTTP_400_BAD_REQUEST,
    }
    return _login_headers(client, payload["username"], payload["password"])


def _with_reason(headers: dict[str, str], reason: str = "Motivo QA de respaldo") -> dict[str, str]:
    return {**headers, "X-Reason": reason}


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

    backup_response = client.post(
        "/backups/run",
        json={"nota": "Respaldo QA"},
        headers=_with_reason(headers, "Generar respaldo QA"),
    )
    assert backup_response.status_code == status.HTTP_201_CREATED
    backup_data = backup_response.json()

    pdf_path = Path(backup_data["pdf_path"])
    archive_path = Path(backup_data["archive_path"])
    json_path = Path(backup_data["json_path"])
    sql_path = Path(backup_data["sql_path"])
    config_path = Path(backup_data["config_path"])
    metadata_path = Path(backup_data["metadata_path"])
    critical_directory = Path(backup_data["critical_directory"])

    for path in [
        pdf_path,
        archive_path,
        json_path,
        sql_path,
        config_path,
        metadata_path,
    ]:
        assert path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["notes"] == "Respaldo QA"
    assert metadata["reason"] == "Generar respaldo QA"
    assert metadata["triggered_by_id"] == backup_data["triggered_by_id"]
    assert metadata["total_size_bytes"] == backup_data["total_size_bytes"]
    assert metadata["components"] == [
        "configuration",
        "critical_files",
        "database",
    ]

    assert critical_directory.exists() and critical_directory.is_dir()
    expected_size = sum(
        path.stat().st_size for path in [pdf_path, archive_path, json_path, sql_path, config_path, metadata_path]
    )
    expected_size += sum(file_path.stat().st_size for file_path in critical_directory.rglob("*") if file_path.is_file())
    assert backup_data["total_size_bytes"] == expected_size
    assert set(backup_data["components"]) == {
        "database",
        "configuration",
        "critical_files",
    }

    headers = _auth_headers(client)
    history_response = client.get("/backups/history", headers=headers)
    assert history_response.status_code == status.HTTP_200_OK, history_response.json()
    history = history_response.json()
    assert history
    assert history[0]["notes"] == "Respaldo QA"
    assert set(history[0]["components"]) == {
        "database",
        "configuration",
        "critical_files",
    }

    logs_response = client.get("/logs/sistema", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    logs = logs_response.json()
    assert any(log["accion"] == "backup_generated" for log in logs)

    pdf_response = client.get(
        "/reports/inventory/pdf",
        headers={**headers, "X-Reason": "Descarga inventario QA"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def test_backup_restore_database_and_files(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SM-RESTORE-01",
        "name": "Tablet Restore",
        "quantity": 2,
        "unit_price": 5500.0,
        "imei": "351234567890123",
        "serial": "REST-0001",
        "marca": "Softmobile",
        "modelo": "Restore Tab",
    }
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED

    backup_response = client.post(
        "/backups/run",
        json={},
        headers=_with_reason(headers, "Respaldo inicial"),
    )
    assert backup_response.status_code == status.HTTP_201_CREATED
    backup_data = backup_response.json()
    backup_id = backup_data["id"]

    headers = _auth_headers(client)
    extra_store = client.post(
        "/stores",
        json={"name": "Sucursal Temporal", "location": "TMP", "timezone": "UTC"},
        headers=headers,
    )
    assert extra_store.status_code == status.HTTP_201_CREATED, extra_store.json()

    restore_response = client.post(
        f"/backups/{backup_id}/restore",
        json={"componentes": ["database"], "aplicar_base_datos": True},
        headers=_with_reason(headers, "Restaurar base de datos QA"),
    )
    assert restore_response.status_code == status.HTTP_200_OK
    restore_data = restore_response.json()
    assert restore_data["job_id"] == backup_id
    assert "database" in restore_data["componentes"]
    assert restore_data["resultados"]["database"].startswith("Base de datos restaurada")

    headers = _auth_headers(client)
    stores_after_restore = client.get("/stores", headers=headers)
    assert stores_after_restore.status_code == status.HTTP_200_OK
    stores_payload = stores_after_restore.json()
    store_names = {store["name"] for store in stores_payload["items"]}
    assert "Sucursal Temporal" not in store_names

    destino_personalizado = tmp_path / "restaurados"
    restore_files_response = client.post(
        f"/backups/{backup_id}/restore",
        json={"componentes": ["configuration", "critical_files"], "destino": str(destino_personalizado)},
        headers=_with_reason(headers, "Restaurar archivos criticos"),
    )
    assert restore_files_response.status_code == status.HTTP_200_OK
    restore_files_data = restore_files_response.json()
    assert restore_files_data["componentes"] == ["configuration", "critical_files"]
    assert Path(restore_files_data["destino"]).exists()
    assert (Path(restore_files_data["destino"]) / "archivos_criticos").exists()
    assert "database" not in restore_files_data["resultados"]

    restore_config_response = client.post(
        f"/backups/{backup_id}/restore",
        json={"componentes": ["configuration"]},
        headers=_with_reason(headers, "Restaurar configuracion QA"),
    )
    assert restore_config_response.status_code == status.HTTP_200_OK
    restore_config_data = restore_config_response.json()
    assert restore_config_data["componentes"] == ["configuration"]
    assert "database" not in restore_config_data["resultados"]

    invalid_restore = client.post(
        f"/backups/{backup_id}/restore",
        json={"componentes": ["unknown_component"]},
        headers=_with_reason(headers, "Intento restauracion invalido"),
    )
    assert invalid_restore.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = invalid_restore.json()["detail"][0]["msg"]
    assert "Input should be" in error_detail and "critical_files" in error_detail

    logs_response = client.get("/logs/sistema", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    logs = logs_response.json()
    assert any(log["accion"] == "backup_restored" for log in logs)


def test_backup_restore_sql_without_applying_database(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {
        "name": "Sucursal Copia SQL",
        "location": "GDL",
        "timezone": "America/Mexico_City",
    }
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED, store_response.json()

    backup_response = client.post(
        "/backups/run",
        json={},
        headers=_with_reason(headers, "Respaldo previo a restauracion en destino"),
    )
    assert backup_response.status_code == status.HTTP_201_CREATED, backup_response.json()
    backup_id = backup_response.json()["id"]

    active_store_response = client.post(
        "/stores",
        json={"name": "Sucursal Activa", "location": "MTY", "timezone": "America/Monterrey"},
        headers=headers,
    )
    assert active_store_response.status_code == status.HTTP_201_CREATED, active_store_response.json()

    before_restore = client.get("/stores", headers=headers)
    assert before_restore.status_code == status.HTTP_200_OK, before_restore.json()
    before_names = {store["name"] for store in before_restore.json()["items"]}
    assert before_names.issuperset({"Sucursal Copia SQL", "Sucursal Activa"})

    destino_personalizado = tmp_path / "restauracion_sql"
    restore_response = client.post(
        f"/backups/{backup_id}/restore",
        json={
            "componentes": ["database"],
            "aplicar_base_datos": False,
            "destino": str(destino_personalizado),
        },
        headers=_with_reason(headers, "Copiar SQL a destino temporal"),
    )
    assert restore_response.status_code == status.HTTP_200_OK, restore_response.json()
    restore_data = restore_response.json()

    restore_destination = Path(restore_data["destino"])
    assert restore_destination.exists() and restore_destination.is_dir()
    assert set(restore_data["componentes"]) == {"database"}
    sql_restored_path = Path(restore_data["resultados"]["database"])
    assert sql_restored_path.exists() and sql_restored_path.is_file()
    assert sql_restored_path.parent == restore_destination

    with sql_restored_path.open(encoding="utf-8") as sql_file:
        sql_content = sql_file.read()

    branch_inserts = [
        line
        for line in sql_content.splitlines()
        if 'INSERT INTO "sucursales"' in line
    ]
    assert any("Sucursal Copia SQL" in line for line in branch_inserts)
    assert not any("Sucursal Activa" in line for line in branch_inserts)

    after_restore = client.get("/stores", headers=headers)
    assert after_restore.status_code == status.HTTP_200_OK, after_restore.json()
    after_names = {store["name"] for store in after_restore.json()["items"]}
    assert after_names == before_names

    shutil.rmtree(restore_destination, ignore_errors=True)


def test_backup_download_formats(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    backup_response = client.post(
        "/backups/run",
        json={},
        headers=_with_reason(headers, "Respaldo para descargas"),
    )
    assert backup_response.status_code == status.HTTP_201_CREATED, backup_response.json()
    backup_data = backup_response.json()
    backup_id = backup_data["id"]

    formatos = (
        ("zip", "archive_path", "application/zip"),
        ("sql", "sql_path", "application/sql"),
        ("json", "json_path", "application/json"),
    )

    for formato, attr, media_type in formatos:
        response = client.get(
            f"/backups/{backup_id}/download",
            params={"formato": formato},
            headers=_with_reason(headers, f"Descargar respaldo {formato}"),
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith(media_type)
        expected_filename = Path(backup_data[attr]).name
        assert expected_filename in response.headers["content-disposition"]

    limited_user_payload = {
        "username": "operador",
        "password": "Clave12345",
        "full_name": "Operador Local",
        "roles": [],
    }
    created = client.post("/auth/bootstrap", json=limited_user_payload)
    if created.status_code == status.HTTP_201_CREATED:
        user_headers = _login_headers(
            client, limited_user_payload["username"], limited_user_payload["password"]
        )
        forbidden = client.get(
            f"/backups/{backup_id}/download",
            params={"formato": "zip"},
            headers=_with_reason(user_headers, "Descarga no autorizada"),
        )
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN


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

    integrity = snapshot["integrity_report"]
    assert integrity["resumen"]["dispositivos_evaluados"] == 3
    assert integrity["resumen"]["dispositivos_inconsistentes"] == 3
    assert integrity["resumen"]["discrepancias_totales"] >= 3

    stores = {store["name"]: store for store in snapshot["stores"]}
    assert stores["Sucursal Centro"]["inventory_value"] == pytest.approx(61000.0)
    assert stores["Sucursal Centro"]["device_count"] == 2
    assert stores["Sucursal Centro"]["total_units"] == 5
    assert stores["Sucursal Norte"]["inventory_value"] == pytest.approx(4800.0)
    assert stores["Sucursal Norte"]["device_count"] == 1
    assert stores["Sucursal Norte"]["total_units"] == 4
