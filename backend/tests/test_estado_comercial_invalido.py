"""Pruebas para validar registros con estado comercial inválido."""
from __future__ import annotations

from decimal import Decimal

from fastapi import status

from backend.app import crud, models
from backend.app.core.roles import ADMIN
from backend.app.services import import_validation


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "estado_admin",
        "password": "ClaveSegura123",
        "full_name": "Estado Admin",
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
    return {
        "Authorization": f"Bearer {token}",
        "X-Reason": "Validacion estado comercial",
    }


def test_validador_estado_invalido_registra_incidencia(db_session) -> None:
    """El validador debe registrar incidencias para estados no reconocidos."""

    registros = [
        import_validation.build_record(
            row_index=1,
            store_id=None,
            store_name=None,
            imei="359000000000999",
            serial=None,
            raw_cantidad="1",
            parsed_cantidad=1,
            raw_precio="12000",
            parsed_precio=Decimal("12000"),
            raw_costo="8000",
            parsed_costo=Decimal("8000"),
            fecha_compra=None,
            fecha_ingreso=None,
            device_id=None,
        )
    ]

    summary = import_validation.validar_importacion(
        db_session,
        registros=registros,
        columnas_faltantes=(),
        import_duration=0.1,
        incidencias_estado_comercial=[
            {
                "row_index": 1,
                "device_id": None,
                "valor_original": "USADO-MALO",
                "fix_sugerido": "NUEVO",
            }
        ],
    )

    assert summary.advertencias == 1
    validations = crud.list_import_validations(db_session, limit=10, offset=0)
    assert any(
        "[ESTADO_COMERCIAL_INVALIDO]" in validation.descripcion for validation in validations
    )


def test_api_import_estado_invalido(db_session, client) -> None:
    """La API debe reportar la incidencia y normalizar el estado a NUEVO."""

    headers = _auth_headers(client)
    csv_content = (
        "Sucursal,Marca,Modelo,IMEI,Color,Cantidad,Estado Comercial\n"
        "Sucursal Validaciones,Samsung,Galaxy S22,359000000000001,Negro,1,USADO-MALO\n"
    )

    response = client.post(
        "/inventory/import/smart",
        files={
            "file": (
                "estado_invalido.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
        data={"commit": "true", "overrides": "{}"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["resultado"] is not None

    report_response = client.get("/validacion/reporte", headers=headers)
    assert report_response.status_code == status.HTTP_200_OK
    report = report_response.json()
    assert report["advertencias"] >= 1

    validations = crud.list_import_validations(db_session, limit=20, offset=0)
    assert any(
        "ESTADO_COMERCIAL_INVALIDO" in validation.descripcion for validation in validations
    )
    assert any("fix_sugerido='NUEVO'" in validation.descripcion for validation in validations)

    store = crud.get_store_by_name(db_session, "Sucursal Validaciones")
    assert store is not None
    device = crud.find_device_for_import(
        db_session,
        store_id=store.id,
        imei="359000000000001",
    )
    assert device is not None
    assert device.estado_comercial == models.CommercialState.NUEVO
