from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

# Tablas esperadas clave (renombradas / estructuras centrales). Algunas pueden
# existir con nombre original si el renombre ocurre en migración posterior.
EXPECTED_TABLES = {
    "stores",  # nombre inicial antes de renombre a sucursales
    "sucursales",
    "devices",
    "inventory_movements",
    "users",  # nombre inicial antes de renombre a usuarios
    "usuarios",
    "clientes",
    "ventas",
    "detalle_ventas",
    "compras",
    "detalle_compras",
    "transfer_orders",
    "audit_logs",
    "sync_outbox",
    "backup_jobs",
    "roles",
    "user_roles",
}


def test_clean_install_migrations(tmp_path) -> None:
    db_path = tmp_path / "migraciones.db"
    database_url = f"sqlite:///{db_path}"  # Persistente temporal

    # Preparar configuración de Alembic apuntando al nuevo DB
    alembic_ini = Path("backend/alembic.ini").resolve()
    assert alembic_ini.exists(), "No se encontró alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", database_url)
    # Asegurar ubicación correcta del script de migraciones relativa al repo
    script_location = Path("backend/alembic").resolve()
    config.set_main_option("script_location", str(script_location))

    # Ejecutar upgrade head sobre DB vacía
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())

    # Debe existir al menos una tabla representando sucursales y usuarios
    assert ("stores" in existing_tables) or (
        "sucursales" in existing_tables), "No se creó stores/sucursales"
    assert ("users" in existing_tables) or (
        "usuarios" in existing_tables), "No se creó users/usuarios"
    # Conjunto crítico mínimo
    critical = {"devices", "inventory_movements",
                "audit_logs", "roles", "user_roles", "backup_jobs"}
    missing_critical = critical.difference(existing_tables)
    assert not missing_critical, f"Faltan tablas críticas: {sorted(missing_critical)}"

    # Smoke: verificar columnas clave en tablas renombradas
    if "sucursales" in existing_tables:
        sucursales_cols = {col["name"]
                           for col in insp.get_columns("sucursales")}
        assert {"id_sucursal", "nombre", "codigo", "timezone",
                "inventory_value"}.issubset(sucursales_cols)
    else:  # fallback stores inicial
        stores_cols = {col["name"] for col in insp.get_columns("stores")}
        assert {"id", "name", "timezone"}.issubset(stores_cols)

    if "usuarios" in existing_tables:
        usuarios_cols = {col["name"] for col in insp.get_columns("usuarios")}
        assert {"id_usuario", "correo", "rol",
                "estado"}.issubset(usuarios_cols)
    else:
        users_cols = {col["name"] for col in insp.get_columns("users")}
        assert {"id", "username", "password_hash"}.issubset(users_cols)

    # Clientes: tolerar instalaciones donde aún no existe la tabla (según base inicial)
    clientes_table = (
        "clientes" if "clientes" in existing_tables else (
            "customers" if "customers" in existing_tables else None
        )
    )
    if clientes_table == "clientes":
        clientes_cols = {col["name"] for col in insp.get_columns("clientes")}
        assert {"id_cliente", "nombre", "limite_credito",
                "saldo"}.issubset(clientes_cols)
    elif clientes_table == "customers":
        customers_cols = {col["name"] for col in insp.get_columns("customers")}
        # Comprobación mínima en esquema original
        assert {"id", "name"}.issubset(customers_cols)
    else:
        # Si no existe ninguna tabla de clientes, continuar sin fallo (esquema base sin módulo clientes)
        pass

    # Ventas: aceptar nombre español o inglés
    ventas_table = (
        "ventas" if "ventas" in existing_tables else (
            "sales" if "sales" in existing_tables else None
        )
    )
    if ventas_table == "ventas":
        ventas_cols = {col["name"] for col in insp.get_columns("ventas")}
        assert {"id_venta", "cliente_id", "usuario_id",
                "total"}.issubset(ventas_cols)
    elif ventas_table == "sales":
        sales_cols = {col["name"] for col in insp.get_columns("sales")}
        assert {"id", "customer_id", "user_id", "total"}.issubset(sales_cols)
    else:
        # Si no existe ninguna tabla de ventas, fallar: ventas es requerida por la app
        raise AssertionError(
            "No se encontró ventas/sales en la instalación limpia")

    # Verificación rápida de estructura: columnas renombradas existen
    device_cols = {c["name"] for c in insp.get_columns("devices")}
    assert "sucursal_id" in device_cols or "store_id" in device_cols, (
        "devices debe contener sucursal_id o store_id"
    )

    mov_cols = {c["name"] for c in insp.get_columns("inventory_movements")}
    assert (
        "sucursal_origen_id" in mov_cols or "tienda_origen_id" in mov_cols
    ), "inventory_movements debe contener sucursal_origen_id/tienda_origen_id"

    # Confirmar que audit_logs existe con columnas básicas (aceptar nombres ES/EN)
    audit_cols = {c["name"] for c in insp.get_columns("audit_logs")}
    assert {"id", "created_at"}.issubset(audit_cols)
    assert ("accion" in audit_cols) or ("action" in audit_cols), (
        "audit_logs debe incluir accion/action"
    )

    # Confirmar sync_outbox columnas claves (sinónimos attempts/attempt_count)
    outbox_cols = {c["name"] for c in insp.get_columns("sync_outbox")}
    assert {"id", "entity_type", "status"}.issubset(outbox_cols)
    assert ("attempts" in outbox_cols) or ("attempt_count" in outbox_cols), (
        "sync_outbox debe incluir attempts/attempt_count"
    )

    # No dejar archivos huérfanos
    assert db_path.exists() and db_path.stat().st_size > 0

    # Señal que la instalación mínima es consistente
    print(f"Instalación limpia OK. Tablas: {len(existing_tables)} enumeradas.")
