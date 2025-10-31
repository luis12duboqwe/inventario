"""Pruebas de integridad para el módulo clásico de compras y proveedores."""

from __future__ import annotations

from sqlalchemy import DateTime, Integer, Numeric, String, Text, inspect


def _column_map(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def test_proveedores_schema_completo(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    columns = _column_map(inspector, "proveedores")

    expected_columns = {
        "id_proveedor",
        "nombre",
        "telefono",
        "correo",
        "direccion",
        "tipo",
        "estado",
        "notas",
    }
    assert expected_columns.issubset(columns.keys())

    assert isinstance(columns["id_proveedor"]["type"], Integer)
    assert isinstance(columns["nombre"]["type"], String)
    assert isinstance(columns["estado"]["type"], String)
    assert isinstance(columns["notas"]["type"], Text)

    indexes = {index["name"]: index for index in inspector.get_indexes("proveedores")}
    assert "ix_proveedores_nombre" in indexes
    assert bool(indexes["ix_proveedores_nombre"]["unique"]) is True


def test_compras_y_detalles_relaciones(db_session) -> None:
    engine = db_session.get_bind()
    inspector = inspect(engine)

    compras_columns = _column_map(inspector, "compras")
    assert {
        "id_compra",
        "proveedor_id",
        "usuario_id",
        "fecha",
        "total",
        "impuesto",
        "forma_pago",
        "estado",
    }.issubset(compras_columns.keys())

    assert isinstance(compras_columns["id_compra"]["type"], Integer)
    assert isinstance(compras_columns["fecha"]["type"], DateTime)
    assert isinstance(compras_columns["total"]["type"], Numeric)
    assert isinstance(compras_columns["impuesto"]["type"], Numeric)
    assert isinstance(compras_columns["forma_pago"]["type"], String)

    compras_indexes = {
        index["name"]: index for index in inspector.get_indexes("compras")
    }
    assert "ix_compras_proveedor_id" in compras_indexes
    assert "ix_compras_usuario_id" in compras_indexes

    compras_fks = inspector.get_foreign_keys("compras")
    assert any(
        fk["referred_table"] == "proveedores"
        and fk["referred_columns"] == ["id_proveedor"]
        and fk["constrained_columns"] == ["proveedor_id"]
        for fk in compras_fks
    )
    assert any(
        fk["referred_table"] == "usuarios"
        and fk["referred_columns"] == ["id_usuario"]
        and fk["constrained_columns"] == ["usuario_id"]
        for fk in compras_fks
    )

    detalles_columns = _column_map(inspector, "detalle_compras")
    assert {
        "id_detalle",
        "compra_id",
        "producto_id",
        "cantidad",
        "costo_unitario",
        "subtotal",
    }.issubset(detalles_columns.keys())

    assert isinstance(detalles_columns["id_detalle"]["type"], Integer)
    assert isinstance(detalles_columns["cantidad"]["type"], Integer)
    assert isinstance(detalles_columns["costo_unitario"]["type"], Numeric)
    assert isinstance(detalles_columns["subtotal"]["type"], Numeric)

    detalles_indexes = {
        index["name"]: index for index in inspector.get_indexes("detalle_compras")
    }
    assert "ix_detalle_compras_compra_id" in detalles_indexes
    assert "ix_detalle_compras_producto_id" in detalles_indexes

    detalles_fks = inspector.get_foreign_keys("detalle_compras")
    assert any(
        fk["referred_table"] == "compras"
        and fk["referred_columns"] == ["id_compra"]
        and fk["constrained_columns"] == ["compra_id"]
        for fk in detalles_fks
    )
    assert any(
        fk["referred_table"] in {"productos", "devices"}
        and fk["constrained_columns"] == ["producto_id"]
        for fk in detalles_fks
    )
