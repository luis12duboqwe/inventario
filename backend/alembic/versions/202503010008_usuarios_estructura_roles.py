"""Usuarios estructura y roles base"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010008"
down_revision = "202503010007"
branch_labels = None
depends_on = None


ROLE_PRIORITY_CASE = "CASE r.name WHEN 'ADMIN' THEN 1 WHEN 'GERENTE' THEN 2 WHEN 'OPERADOR' THEN 3 WHEN 'INVITADO' THEN 4 ELSE 5 END"


def upgrade() -> None:
    op.rename_table("users", "usuarios")

    op.alter_column("usuarios", "id", new_column_name="id_usuario")
    op.alter_column("usuarios", "username", new_column_name="correo")
    op.alter_column("usuarios", "full_name", new_column_name="nombre")
    op.alter_column("usuarios", "created_at", new_column_name="fecha_creacion")

    op.add_column("usuarios", sa.Column("telefono", sa.String(length=30), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column("rol", sa.String(length=30), nullable=False, server_default="OPERADOR"),
    )
    op.add_column(
        "usuarios",
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="ACTIVO"),
    )

    op.drop_index("ix_users_id", table_name="usuarios")
    op.drop_index("ix_users_username", table_name="usuarios")
    op.drop_index("ix_users_sucursal_id", table_name="usuarios")

    op.create_index("ix_usuarios_id_usuario", "usuarios", ["id_usuario"], unique=False)
    op.create_index("ix_usuarios_correo", "usuarios", ["correo"], unique=True)
    op.create_index("ix_usuarios_sucursal_id", "usuarios", ["sucursal_id"], unique=False)

    op.execute(
        """
        UPDATE usuarios
        SET estado = CASE WHEN is_active THEN 'ACTIVO' ELSE 'INACTIVO' END
        """
    )
    op.execute(
        f"""
        UPDATE usuarios
        SET rol = (
            SELECT r.name
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = usuarios.id_usuario
            ORDER BY {ROLE_PRIORITY_CASE}
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM user_roles ur WHERE ur.user_id = usuarios.id_usuario
        )
        """
    )
    op.execute("UPDATE usuarios SET rol = 'OPERADOR' WHERE rol IS NULL")
    op.execute("UPDATE usuarios SET estado = 'ACTIVO' WHERE estado IS NULL")


def downgrade() -> None:
    op.execute("UPDATE usuarios SET is_active = CASE WHEN estado = 'ACTIVO' THEN 1 ELSE 0 END")

    op.drop_index("ix_usuarios_sucursal_id", table_name="usuarios")
    op.drop_index("ix_usuarios_correo", table_name="usuarios")
    op.drop_index("ix_usuarios_id_usuario", table_name="usuarios")

    op.drop_column("usuarios", "estado")
    op.drop_column("usuarios", "rol")
    op.drop_column("usuarios", "telefono")

    op.alter_column("usuarios", "fecha_creacion", new_column_name="created_at")
    op.alter_column("usuarios", "nombre", new_column_name="full_name")
    op.alter_column("usuarios", "correo", new_column_name="username")
    op.alter_column("usuarios", "id_usuario", new_column_name="id")

    op.rename_table("usuarios", "users")

    op.create_index("ix_users_sucursal_id", "users", ["sucursal_id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)
