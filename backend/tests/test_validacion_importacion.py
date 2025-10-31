from fastapi import status

from backend.app import crud, models
from backend.app.services import inventory_smart_import
from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "validacion_admin",
        "password": "ClaveSegura123",
        "full_name": "Validación Admin",
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


def test_validacion_importacion_detecta_incidencias(db_session, client):
    header = "Sucursal,Marca,IMEI,Color,Cantidad,Precio\n"
    rows: list[str] = []
    duplicated_imei = "359999999999999"
    for index in range(500):
        store = f"Sucursal {index % 3 + 1}"
        marca = f"Marca {index % 5}"
        imei = duplicated_imei if index in {10, 120} else f"35{index:013d}"
        cantidad = "-3" if index == 25 else "1"
        precio = "9500"
        rows.append(f"{store},{marca},{imei},Negro,{cantidad},{precio}\n")
    dataset = header + "".join(rows)

    result = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=dataset.encode("utf-8"),
        filename="lote_validacion.csv",
        commit=True,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Validación masiva",
    )

    assert result.resultado is not None
    summary = result.resultado.validacion_resumen
    assert summary is not None
    assert summary.registros_revisados == 500
    assert summary.errores >= 1
    assert summary.advertencias >= 1
    assert "modelo" in summary.campos_faltantes

    validations = crud.list_import_validations(db_session, limit=200, offset=0)
    assert validations
    descriptions = [validation.descripcion for validation in validations]
    assert any("IMEI duplicado" in descripcion for descripcion in descriptions)
    assert any(descripcion.startswith("Columna faltante") for descripcion in descriptions)

    headers = _auth_headers(client)
    headers_with_reason = {**headers, "X-Reason": "Correccion de validacion"}

    report_response = client.get("/validacion/reporte", headers=headers)
    assert report_response.status_code == status.HTTP_200_OK
    report = report_response.json()
    assert "registros_revisados" in report
    assert report["errores"] >= 1

    export_response = client.get("/validacion/exportar?formato=excel", headers=headers)
    assert export_response.status_code == status.HTTP_200_OK
    assert export_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )

    first_validation = validations[0]
    patch_response = client.patch(
        f"/validacion/{first_validation.id}/corregir",
        headers=headers_with_reason,
    )
    assert patch_response.status_code == status.HTTP_200_OK
    payload = patch_response.json()
    assert payload["corregido"] is True

    updated_validation = db_session.get(models.ImportValidation, first_validation.id)
    assert updated_validation is not None
    assert updated_validation.corregido is True
