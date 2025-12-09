from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..database import Base

if TYPE_CHECKING:
    from .stores import Store
    from .inventory import InventoryMovement, InventoryReservation
    from .sync import SyncSession
    from .audit import AuditLog, AuditAlertAcknowledgement
    from .backups import BackupJob


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base):
    __tablename__ = "permisos"
    __table_args__ = (
        UniqueConstraint("rol", "modulo", name="uq_permisos_rol_modulo"),
    )

    id: Mapped[int] = mapped_column(
        "id_permiso", Integer, primary_key=True, index=True)
    role_name: Mapped[str] = mapped_column(
        "rol",
        String(50),
        ForeignKey("roles.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module: Mapped[str] = mapped_column(
        "modulo", String(120), nullable=False, index=True)
    can_view: Mapped[bool] = mapped_column(
        "puede_ver", Boolean, nullable=False, default=False)
    can_edit: Mapped[bool] = mapped_column(
        "puede_editar", Boolean, nullable=False, default=False)
    can_delete: Mapped[bool] = mapped_column(
        "puede_borrar", Boolean, nullable=False, default=False)

    rol = synonym("role_name")

    role: Mapped[Role] = relationship("Role", back_populates="permissions")


class User(Base):
    __tablename__ = "usuarios"
    __table_args__ = (Index("ix_usuarios_is_deleted", "is_deleted"),)

    id: Mapped[int] = mapped_column(
        "id_usuario", Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column("correo", String(
        120), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(
        "nombre", String(120), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rol: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OPERADOR", server_default="OPERADOR")
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVO", server_default="ACTIVO")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    supervisor_pin_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0)
    last_login_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    store_id: Mapped[int | None] = mapped_column(
        "sucursal_id",
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    correo = synonym("username")
    nombre = synonym("full_name")

    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement", back_populates="performed_by", passive_deletes=True
    )
    sync_sessions: Mapped[list["SyncSession"]] = relationship(
        "SyncSession", back_populates="triggered_by", passive_deletes=True
    )
    logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="performed_by", passive_deletes=True
    )
    backup_jobs: Mapped[list["BackupJob"]] = relationship(
        "BackupJob",
        back_populates="triggered_by",
        passive_deletes=True,
        foreign_keys="BackupJob.triggered_by_id",
    )
    store: Mapped[Store | None] = relationship(
        "Store",
        back_populates="users",
        passive_deletes=True,
        primaryjoin="and_(foreign(User.store_id)==Store.id, Store.is_deleted.is_(False))",
    )
    totp_secret: Mapped[UserTOTPSecret | None] = relationship(
        "UserTOTPSecret", back_populates="user", uselist=False
    )
    active_sessions: Mapped[list["ActiveSession"]] = relationship(
        "ActiveSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="ActiveSession.user_id",
    )
    audit_acknowledgements: Mapped[list["AuditAlertAcknowledgement"]] = relationship(
        "AuditAlertAcknowledgement",
        back_populates="acknowledged_by",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    inventory_reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="reserved_by",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="InventoryReservation.reserved_by_id",
    )
    resolved_reservations: Mapped[list["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="resolved_by",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="InventoryReservation.resolved_by_id",
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint(
        "user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "usuarios.id_usuario", ondelete="CASCADE"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "roles.id", ondelete="CASCADE"), index=True)

    user: Mapped[User] = relationship("User", back_populates="roles")
    role: Mapped[Role] = relationship("Role", back_populates="users")


class UserTOTPSecret(Base):
    __tablename__ = "user_totp_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True
    )
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="totp_secret")


class ActiveSession(Base):
    __tablename__ = "active_sessions"
    __table_args__ = (UniqueConstraint(
        "session_token", name="uq_active_session_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True, index=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True)

    user: Mapped[User] = relationship(
        "User", foreign_keys=[user_id], back_populates="active_sessions"
    )
    revoked_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[revoked_by_id]
    )


class JWTBlacklist(Base):
    __tablename__ = "jwt_blacklist"
    __table_args__ = (UniqueConstraint("jti", name="uq_jwt_blacklist_jti"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    revoked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    revoked_by: Mapped[User | None] = relationship("User")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint(
        "token", name="uq_password_reset_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship(
        "User", back_populates="password_reset_tokens")


class StoreMembership(Base):
    """Vincula usuarios con tiendas y sus permisos de transferencias."""
    __tablename__ = "store_memberships"
    __table_args__ = (UniqueConstraint(
        "user_id", "store_id", name="uq_user_store"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.id_usuario", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    can_create_transfer: Mapped[bool] = mapped_column(default=False)
    can_receive_transfer: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship("User")
    store: Mapped[Any] = relationship("Store")
