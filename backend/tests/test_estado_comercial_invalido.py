"""Pruebas de importación con estados comerciales inválidos."""
from backend.app import crud, models
from backend.app.services import inventory_smart_import


CSV_INVALID_STATE = (
    "Sucursal,Marca,Modelo,IMEI,Color,Cantidad,Estado Comercial\n"
    "Sucursal Diagnostico,Motorola,Moto G 50,123456789012349,Gris,2,USADO-MALO\n"
)


def test_inventory_import_normalizes_invalid_commercial_state(db_session) -> None:
    """Un estado desconocido debe normalizarse a NUEVO y no romper la importación."""

    response = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=CSV_INVALID_STATE.encode("utf-8"),
        filename="estado_invalido.csv",
        commit=True,
        overrides=None,
        performed_by_id=None,
        username="auditor",
        reason="Validación de estado",
    )

    result = response.resultado
    assert result is not None
    assert result.total_procesados == 1
    assert result.nuevos == 1

    store = crud.get_store_by_name(db_session, "Sucursal Diagnostico")
    assert store is not None

    device = crud.find_device_for_import(
        db_session,
        store_id=store.id,
        imei="123456789012349",
    )
    assert device is not None
    assert device.estado_comercial == models.CommercialState.NUEVO
