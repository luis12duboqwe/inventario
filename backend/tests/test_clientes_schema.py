from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, Text, inspect

from backend.app import models


def _column_map(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def test_clientes_estructura_general(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    columns = _column_map(inspector, "clientes")

    expected_columns = {
        "id_cliente",
        "nombre",
        "telefono",
        "correo",
        "direccion",
        "tipo",
        "estado",
        "limite_credito",
        "saldo",
        "notas",
    }
    assert expected_columns.issubset(columns.keys())

    assert isinstance(columns["id_cliente"]["type"], Integer)
    assert isinstance(columns["nombre"]["type"], String)
    assert isinstance(columns["telefono"]["type"], String)
    assert isinstance(columns["estado"]["type"], String)
    assert isinstance(columns["limite_credito"]["type"], Numeric)
    assert isinstance(columns["saldo"]["type"], Numeric)
    assert isinstance(columns["notas"]["type"], Text)
    assert columns["telefono"]["nullable"] is False
    assert columns["limite_credito"]["nullable"] is False
    assert columns["saldo"]["nullable"] is False

    indexes = {index["name"]: index for index in inspector.get_indexes("clientes")}
    assert "ix_clientes_nombre" in indexes
    assert bool(indexes["ix_clientes_nombre"]["unique"]) is True
    assert "ix_clientes_telefono" in indexes

    unique_constraints = inspector.get_unique_constraints("clientes")
    has_unique_email = any(
        constraint.get("column_names") == ["correo"] for constraint in unique_constraints
    )
    if not has_unique_email:
        has_unique_email = any(
            (index.get("column_names") or []) == ["correo"]
            and bool(index.get("unique"))
            for index in indexes.values()
        )
    assert has_unique_email


def test_relaciones_clientes_con_ventas_y_reparaciones(db_session) -> None:
    inspector = inspect(db_session.get_bind())

    ventas_fks = inspector.get_foreign_keys("ventas")
    assert any(
        fk["referred_table"] == "clientes"
        and fk["referred_columns"] == ["id_cliente"]
        and fk["constrained_columns"] == ["cliente_id"]
        and fk.get("options", {}).get("ondelete") == "SET NULL"
        for fk in ventas_fks
    )

    ventas_indexes = {
        index["name"]: index for index in inspector.get_indexes("ventas")
    }
    assert "ix_ventas_cliente_id" in ventas_indexes

    reparaciones_fks = inspector.get_foreign_keys("repair_orders")
    assert any(
        fk["referred_table"] == "clientes"
        and fk["referred_columns"] == ["id_cliente"]
        and fk["constrained_columns"] == ["customer_id"]
        and fk.get("options", {}).get("ondelete") == "SET NULL"
        for fk in reparaciones_fks
    )


def test_factura_se_vincula_con_cliente(db_session) -> None:
    store = models.Store(name="Tienda Facturas", timezone="America/Mexico_City")
    cliente = models.Customer(
        name="Cliente Factura",
        phone="5550001122",
        customer_type="mayorista",
        status="activo",
        credit_limit=Decimal("5000"),
    )
    venta = models.Sale(
        store=store,
        customer=cliente,
        payment_method=models.PaymentMethod.EFECTIVO,
        subtotal_amount=Decimal("100"),
        tax_amount=Decimal("16"),
        total_amount=Decimal("116"),
        notes="Factura directa",
    )

    db_session.add_all([store, cliente, venta])
    db_session.commit()

    assert venta.customer_id == cliente.id
    assert venta.customer is cliente
    assert venta.customer.name == "Cliente Factura"
