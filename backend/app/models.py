"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    location = Column(String(120), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")

    devices = relationship("Device", back_populates="store", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("store_id", "sku", name="uq_devices_store_sku"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String(80), nullable=False)
    name = Column(String(120), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)

    store = relationship("Store", back_populates="devices")
