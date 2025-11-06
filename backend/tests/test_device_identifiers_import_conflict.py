from backend.app import crud, schemas
from backend.app.services import inventory_smart_import


def test_device_identifier_conflict_blocks_smart_import(db_session):
    # Preparar: crear sucursal origen y un dispositivo con identificador IMEI registrado en tabla device_identifiers
    store = crud.create_store(
        db_session,
        schemas.StoreCreate(name="Sucursal Origen", timezone="UTC"),
    )
    base_device = crud.create_device(
        db_session,
        store_id=store.id,
        payload=schemas.DeviceCreate(
            sku="SKU-BASE",
            name="Dispositivo Base",
            quantity=0,
            unit_price=0,
            costo_unitario=0,
            marca="MarcaX",
            modelo="ModeloX",
            color="Negro",
            completo=True,
        ),
    )
    # Registrar identificador con IMEI en la tabla secundaria
    crud.upsert_device_identifier(
        db_session,
        store_id=store.id,
        device_id=base_device.id,
        payload=schemas.DeviceIdentifierRequest(
            imei_1="888888888888888",
            imei_2=None,
            numero_serie=None,
            estado_tecnico=None,
            observaciones=None,
        ),
    )

    # Intentar importar en otra sucursal un dispositivo con el mismo IMEI
    csv_content = (
        "Sucursal,Marca,Modelo,IMEI,Color,Cantidad,Precio,Costo\n"
        "Sucursal Destino,MarcaY,ModeloY,888888888888888,Azul,1,1000,700\n"
    )

    commit_response = inventory_smart_import.process_smart_import(
        db_session,
        file_bytes=csv_content.encode("utf-8"),
        filename="inventario_conflicto_imei.csv",
        commit=True,
        overrides=None,
        performed_by_id=None,
        username="tester",
        reason="Importación conflicto IMEI",
    )

    result = commit_response.resultado
    assert result is not None
    # Debe marcarse como registro incompleto y sin altas/actualizaciones debido al conflicto
    assert result.registros_incompletos == 1
    assert result.nuevos == 0
    assert result.actualizados == 0
    # La advertencia debe incluir el código de conflicto de identificador
    assert any("device_identifier_conflict" in w for w in result.advertencias)

    # Verificar que no se creó el dispositivo en la sucursal destino con ese IMEI
    destino = crud.get_store_by_name(db_session, "Sucursal Destino")
    assert destino is not None
    device = crud.find_device_for_import(
        db_session, store_id=destino.id, imei="888888888888888")
    assert device is None
