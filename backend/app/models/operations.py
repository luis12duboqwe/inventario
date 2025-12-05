from __future__ import annotations
import enum
import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.models.users import User
from backend.app.models.stores import Store


class RecurringOrderType(str, enum.Enum):
    """Tipo de orden recurrente (compra o transferencia)."""
    PURCHASE = "purchase"
    TRANSFER = "transfer"


class RecurringOrder(Base):
    __tablename__ = "recurring_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_type: Mapped[RecurringOrderType] = mapped_column(
        Enum(RecurringOrderType, name="recurring_order_type"), nullable=False
    )
    store_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"), nullable=True
    )
    _payload: Mapped[str] = mapped_column("payload", Text, nullable=False)

    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    last_used_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relaciones
    store: Mapped[Store | None] = relationship("Store")
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    last_used_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[last_used_by_id]
    )

    @property
    def payload(self) -> dict[str, Any]:
        try:
            return json.loads(self._payload)
        except (json.JSONDecodeError, TypeError):
            return {}

    @payload.setter
    def payload(self, value: dict[str, Any] | str) -> None:
        if isinstance(value, str):
            self._payload = value
        else:
            self._payload = json.dumps(value, ensure_ascii=False)
