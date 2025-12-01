from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from backend import database as db_module
from backend.app.database import Base


def _setup_engine(db_path: Path, monkeypatch):
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    session_factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, future=True
    )
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)
    return engine


def test_migrate_lightweight_users_migrates_and_drops_legacy_table(
    tmp_path, monkeypatch
):
    engine = _setup_engine(tmp_path / "legacy_users.db", monkeypatch)

    usuarios_table = Base.metadata.tables["usuarios"]
    roles_table = Base.metadata.tables["roles"]
    user_roles_table = Base.metadata.tables["user_roles"]
    Base.metadata.create_all(
        bind=engine, tables=[usuarios_table, roles_table, user_roles_table]
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY,"
                "username VARCHAR(120),"
                "email VARCHAR(120),"
                "hashed_password VARCHAR(255),"
                "is_active BOOLEAN DEFAULT 1,"
                "created_at DATETIME,"
                "role VARCHAR(30),"
                "rol VARCHAR(30)"
                ")"
            )
        )
        connection.execute(
            text("INSERT INTO roles (id, name) VALUES (1, 'OPERADOR'), (2, 'ADMIN')")
        )
        connection.execute(
            text(
                "INSERT INTO users (username, email, hashed_password, is_active, created_at, role) "
                "VALUES (:username, :email, :password, :is_active, CURRENT_TIMESTAMP, :role)"
            ),
            {
                "username": "legacy_admin",
                "email": "legacy@example.com",
                "password": "hash123",
                "is_active": True,
                "role": "ADMIN",
            },
        )

    db_module._migrate_lightweight_users()

    insp = inspect(engine)
    assert "users" not in insp.get_table_names()

    with engine.connect() as connection:
        usuario = connection.execute(
            text(
                "SELECT id_usuario, correo, password_hash, rol, is_active"
                " FROM usuarios WHERE correo = :correo"
            ),
            {"correo": "legacy@example.com"},
        ).mappings().one()

        assert usuario["rol"] == "ADMIN"
        assert bool(usuario["is_active"]) is True
        assert usuario["password_hash"] == "hash123"

        role_assignment = connection.execute(
            text(
                "SELECT role_id FROM user_roles WHERE user_id = :user_id"
            ),
            {"user_id": usuario["id_usuario"]},
        ).scalar_one_or_none()

        assert role_assignment == 2


def test_migrate_lightweight_users_skips_when_no_legacy_table(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path / "no_legacy.db", monkeypatch)

    usuarios_table = Base.metadata.tables["usuarios"]
    roles_table = Base.metadata.tables["roles"]
    user_roles_table = Base.metadata.tables["user_roles"]
    Base.metadata.create_all(
        bind=engine, tables=[usuarios_table, roles_table, user_roles_table]
    )

    with engine.begin() as connection:
        connection.execute(text("INSERT INTO roles (id, name) VALUES (1, 'OPERADOR')"))
        connection.execute(
            text(
                "INSERT INTO usuarios (correo, nombre, password_hash, rol, estado, is_active, "
                "fecha_creacion, failed_login_attempts)"
                " VALUES (:correo, :nombre, :password_hash, :rol, 'ACTIVO', 1, "
                "CURRENT_TIMESTAMP, :failed_attempts)"
            ),
            {
                "correo": "usuario@example.com",
                "nombre": "Usuario",
                "password_hash": "hash456",
                "rol": "OPERADOR",
                "failed_attempts": 0,
            },
        )
        connection.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (1, 1)")
        )

    db_module._migrate_lightweight_users()

    insp = inspect(engine)
    assert "users" not in insp.get_table_names()

    with engine.connect() as connection:
        usuarios = connection.execute(
            text("SELECT correo FROM usuarios")
        ).all()
        assert len(usuarios) == 1
        assert usuarios[0][0] == "usuario@example.com"


def test_migrate_lightweight_users_backfills_missing_columns(tmp_path, monkeypatch):
    engine = _setup_engine(tmp_path / "backfill_columns.db", monkeypatch)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE usuarios ("
                "id_usuario INTEGER PRIMARY KEY,"
                "correo VARCHAR(255)"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY,"
                "username VARCHAR(120),"
                "email VARCHAR(120)"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (username, email) VALUES (:username, :email)"
            ),
            {"username": "legacy_user", "email": "legacy_backfill@example.com"},
        )

    db_module._migrate_lightweight_users()

    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()

    usuarios_columns = {column["name"] for column in inspector.get_columns("usuarios")}
    assert {
        "correo",
        "nombre",
        "password_hash",
        "rol",
        "estado",
        "is_active",
        "fecha_creacion",
        "failed_login_attempts",
        "last_login_attempt_at",
        "locked_until",
    }.issubset(usuarios_columns)

    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                "SELECT correo, password_hash, rol, estado, is_active, fecha_creacion "
                "FROM usuarios WHERE correo = :correo"
            ),
            {"correo": "legacy_backfill@example.com"},
        ).mappings().one()

        assert migrated["password_hash"] == ""
        assert migrated["rol"] == "OPERADOR"
        assert migrated["estado"] == "ACTIVO"
        assert bool(migrated["is_active"]) is True
        assert migrated["fecha_creacion"] is not None

