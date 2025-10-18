from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, inspect


def _column_map(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def _index_map(inspector, table_name: str) -> dict[str, dict]:
    return {index["name"]: index for index in inspector.get_indexes(table_name)}


def test_sucursales_estructura_principal(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    columns = _column_map(inspector, "sucursales")

    expected_columns = {
        "id_sucursal",
        "nombre",
        "direccion",
        "telefono",
        "responsable",
        "estado",
        "codigo",
        "fecha_creacion",
    }
    assert expected_columns.issubset(columns.keys())

    assert isinstance(columns["id_sucursal"]["type"], Integer)
    assert isinstance(columns["nombre"]["type"], String)
    assert isinstance(columns["direccion"]["type"], String)
    assert isinstance(columns["estado"]["type"], String)
    assert isinstance(columns["codigo"]["type"], String)
    assert isinstance(columns["fecha_creacion"]["type"], DateTime)

    assert columns["estado"]["nullable"] is False
    assert columns["codigo"]["nullable"] is False
    assert columns["fecha_creacion"]["nullable"] is False

    indexes = _index_map(inspector, "sucursales")
    assert "ix_sucursales_nombre" in indexes
    assert bool(indexes["ix_sucursales_nombre"]["unique"]) is True
    assert "ix_sucursales_codigo" in indexes
    assert bool(indexes["ix_sucursales_codigo"]["unique"]) is True
    assert "ix_sucursales_estado" in indexes


def test_sucursales_relaciones_principales(db_session) -> None:
    engine = db_session.get_bind()
    inspector = inspect(engine)

    devices_fks = inspector.get_foreign_keys("devices")
    assert any(
        fk["referred_table"] == "sucursales"
        and fk["constrained_columns"] == ["sucursal_id"]
        and fk["referred_columns"] == ["id_sucursal"]
        for fk in devices_fks
    )

    table_names = set(inspector.get_table_names())
    if "productos" in table_names:
        productos_fks = inspector.get_foreign_keys("productos")
        assert any(
            fk["referred_table"] == "sucursales"
            and fk["constrained_columns"] == ["sucursal_id"]
            and fk["referred_columns"] == ["id_sucursal"]
            for fk in productos_fks
        )

    users_columns = _column_map(inspector, "users")
    assert "sucursal_id" in users_columns
    assert isinstance(users_columns["sucursal_id"]["type"], Integer)

    users_fks = inspector.get_foreign_keys("users")
    assert any(
        fk["referred_table"] == "sucursales"
        and fk["constrained_columns"] == ["sucursal_id"]
        and fk["referred_columns"] == ["id_sucursal"]
        for fk in users_fks
    )

    movimientos_columns = _column_map(inspector, "inventory_movements")
    assert "sucursal_destino_id" in movimientos_columns
    assert "sucursal_origen_id" in movimientos_columns

    movimientos_fks = inspector.get_foreign_keys("inventory_movements")
    assert any(
        fk["referred_table"] == "sucursales"
        and fk["constrained_columns"] == ["sucursal_destino_id"]
        and fk["referred_columns"] == ["id_sucursal"]
        for fk in movimientos_fks
    )
    assert any(
        fk["referred_table"] == "sucursales"
        and fk["constrained_columns"] == ["sucursal_origen_id"]
        and fk["referred_columns"] == ["id_sucursal"]
        for fk in movimientos_fks
    )
