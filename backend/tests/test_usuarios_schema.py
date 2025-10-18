"""Pruebas de integridad para la estructura del módulo de usuarios."""
from sqlalchemy import Boolean, DateTime, Integer, String, inspect

from backend.app import models  # noqa: F401 - necesario para registrar metadatos
from backend.app.core.roles import DEFAULT_ROLES


def _column_map(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def _index_map(inspector, table_name: str) -> dict[str, dict]:
    return {index["name"]: index for index in inspector.get_indexes(table_name)}


def _unique_map(inspector, table_name: str) -> dict[str, dict]:
    return {constraint["name"]: constraint for constraint in inspector.get_unique_constraints(table_name)}


def test_usuarios_columnas_indices_y_fk(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    columns = _column_map(inspector, "usuarios")

    expected_columns = {
        "id_usuario",
        "correo",
        "nombre",
        "telefono",
        "rol",
        "sucursal_id",
        "estado",
        "fecha_creacion",
    }
    assert expected_columns.issubset(columns.keys())

    assert isinstance(columns["id_usuario"]["type"], Integer)
    assert isinstance(columns["correo"]["type"], String)
    assert isinstance(columns["nombre"]["type"], String)
    assert isinstance(columns["telefono"]["type"], String)
    assert isinstance(columns["rol"]["type"], String)
    assert isinstance(columns["estado"]["type"], String)
    assert isinstance(columns["fecha_creacion"]["type"], DateTime)

    assert columns["correo"]["nullable"] is False

    indexes = _index_map(inspector, "usuarios")
    assert "ix_usuarios_correo" in indexes
    assert bool(indexes["ix_usuarios_correo"]["unique"]) is True

    assert columns["rol"]["default"] in {"'OPERADOR'", "OPERADOR"}
    assert columns["estado"]["default"] in {"'ACTIVO'", "ACTIVO"}

    foreign_keys = inspector.get_foreign_keys("usuarios")
    assert any(
        fk["referred_table"] == "sucursales"
        and fk["constrained_columns"] == ["sucursal_id"]
        and fk["referred_columns"] == ["id_sucursal"]
        for fk in foreign_keys
    )


def test_permisos_columnas_indices_y_relaciones(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    columns = _column_map(inspector, "permisos")

    expected_columns = {
        "id_permiso",
        "rol",
        "modulo",
        "puede_ver",
        "puede_editar",
        "puede_borrar",
    }
    assert expected_columns.issubset(columns.keys())

    assert isinstance(columns["id_permiso"]["type"], Integer)
    assert isinstance(columns["rol"]["type"], String)
    assert isinstance(columns["modulo"]["type"], String)
    for column_name in ("puede_ver", "puede_editar", "puede_borrar"):
        assert isinstance(columns[column_name]["type"], (Boolean, Integer))

    for column_name in ("rol", "modulo", "puede_ver", "puede_editar", "puede_borrar"):
        assert columns[column_name]["nullable"] is False

    indexes = _index_map(inspector, "permisos")
    assert "ix_permisos_rol" in indexes
    assert "ix_permisos_modulo" in indexes

    unique_constraints = _unique_map(inspector, "permisos")
    assert "uq_permisos_rol_modulo" in unique_constraints

    foreign_keys = inspector.get_foreign_keys("permisos")
    assert any(
        fk["referred_table"] == "roles"
        and fk["referred_columns"] == ["name"]
        and fk["constrained_columns"] == ["rol"]
        for fk in foreign_keys
    )


def test_roles_base_configurados() -> None:
    expected_roles = {"ADMIN", "GERENTE", "OPERADOR", "INVITADO"}
    assert set(DEFAULT_ROLES) == expected_roles
