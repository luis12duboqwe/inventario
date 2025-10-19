from __future__ import annotations

from fastapi import status

from backend.app import crud, models
from backend.app.core.roles import ADMIN
from backend.app.services import inventory_smart_import


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "inventory_admin",
        "password": "ClaveSegura123",
        "full_name": "Inventario Admin",
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
    sanitized_reason = "Importación inventario".encode("ascii", "ignore").decode("ascii") or "Importacion inventario"
    return {"Authorization": f"Bearer {token}", "X-Reason": sanitized_reason}


def test_inventory_smart_import_preview_and_commit(db_session):
    csv_content = (
        "Sucursal,Marca,Modelo,IMEI,Color,Cantidad,Precio,Costo\n"
        "Sucursal Central,Samsung,Galaxy S22,123456789012345,Azul,5,12000,8000\n"
    )

    preview_response = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="inventario.csv",
        commit=False,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Carga inicial",
    )

    assert preview_response.resultado is None
    assert preview_response.preview.total_filas == 1
    mapped_columns = {match.campo: match.estado for match in preview_response.preview.columnas}
    assert mapped_columns.get("tienda") == "ok"
    assert mapped_columns.get("imei") in {"ok", "pendiente"}

    commit_response = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="inventario.csv",
        commit=True,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Carga inicial",
    )

    assert commit_response.resultado is not None
    result = commit_response.resultado
    assert result.total_procesados == 1
    assert result.nuevos == 1
    assert result.actualizados == 0
    assert "📦 Resultado de importación" in result.resumen

    store = crud.get_store_by_name(db_session, "Sucursal Central")
    assert store is not None
    device = crud.find_device_for_import(
        db_session,
        store_id=store.id,
        imei="123456789012345",
    )
    assert device is not None
    assert device.completo is True
    assert device.imei == "123456789012345"
    assert device.quantity == 5

    history = crud.list_inventory_import_history(db_session, limit=5)
    assert history
    last_record = history[0]
    assert last_record.total_registros == 1
    assert last_record.nuevos == 1
    assert last_record.nombre_archivo == "inventario.csv"

    system_logs = db_session.query(models.SystemLog).all()
    assert any("Importación inteligente ejecutada" in log.descripcion for log in system_logs)


def test_inventory_smart_import_handles_overrides_and_incomplete_records(db_session):
    csv_content = (
        "Sucursal,Dispositivo,Identificador,Color,Cantidad,Estado,Marca\n"
        "Sucursal Norte,Serie X,,Negro,1,Disponible,\n"
    )

    initial_preview = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="inventario.xlsx",
        commit=False,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Carga inicial",
    )

    mapped_columns = {match.campo: match.encabezado_origen for match in initial_preview.preview.columnas}
    assert mapped_columns.get("modelo") is None
    assert "imei" in initial_preview.preview.columnas_faltantes

    commit_response = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="inventario.xlsx",
        commit=True,
        overrides={"modelo": "Dispositivo", "imei": "Identificador"},
        performed_by_id=None,
        username="tester",
        reason="Importación con overrides",
    )

    result = commit_response.resultado
    assert result is not None
    assert result.total_procesados == 1
    assert result.registros_incompletos == 1
    assert "Sucursal Norte" in result.tiendas_nuevas

    store = crud.get_store_by_name(db_session, "Sucursal Norte")
    assert store is not None
    device = crud.find_device_for_import(
        db_session,
        store_id=store.id,
        modelo="Serie X",
        color="Negro",
    )
    assert device is not None
    assert device.completo is False
    assert device.marca is None
    assert device.imei is None

    history = crud.list_inventory_import_history(db_session, limit=1)
    assert history
    record = history[0]
    assert record.total_registros == 1
    assert record.registros_incompletos == 1
    assert record.columnas_detectadas.get("modelo") == "Dispositivo"


def test_inventory_smart_import_endpoint_rejects_invalid_overrides(client):
    headers = _auth_headers(client)
    response = client.post(
        "/inventory/import/smart",
        files={
            "file": (
                "inventario.xlsx",
                b"Sucursal,Marca\nCentral,Samsung\n",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"commit": "false", "overrides": "no-json"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "overrides_invalid"


def test_inventory_incomplete_devices_endpoint_returns_pending_records(client, db_session):
    headers = _auth_headers(client)

    csv_content = (
        "Sucursal,Marca,Modelo,IMEI,Color,Cantidad,Estado\n"
        "Sucursal Centro,Apple,iPhone 14,,Negro,1,Disponible\n"
    )

    inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="pendientes.csv",
        commit=True,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Importación incompleta",
    )

    response = client.get("/inventory/devices/incomplete", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    device = payload[0]
    assert device["completo"] is False
    assert device["name"]
    store = crud.get_store_by_name(db_session, "Sucursal Centro")
    assert store is not None
    assert device["store_id"] == store.id
    assert device["modelo"] == "iPhone 14"
