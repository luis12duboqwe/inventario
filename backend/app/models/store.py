"""Database model for stores/sucursales."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base_class import Base


class Store(Base):
    """Representa una sucursal de Softmobile."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), default=None)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="store", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Store id={self.id} name={self.name!r}>"
