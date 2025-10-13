"""Database model for devices."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base_class import Base


class Device(Base):
    """Representa un dispositivo registrado en inventario."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    store: Mapped["Store"] = relationship("Store", back_populates="devices")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Device id={self.id} sku={self.sku!r} store={self.store_id}>"
