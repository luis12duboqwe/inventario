"""Interfaces genéricas para lectores RFID y básculas industriales."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable


@dataclass(slots=True)
class RFIDTagReading:
    """Lectura individual capturada por un lector RFID."""

    epc: str
    reader: str
    timestamp: datetime
    signal_dbm: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RFIDProductLink:
    """Asociación de un EPC RFID con un producto del catálogo."""

    epc: str
    product_id: str
    linked_at: datetime
    source: str


@dataclass(slots=True)
class ScaleReading:
    """Medición de peso proveniente de una báscula."""

    weight_kg: float
    timestamp: datetime
    source: str
    stable: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProductWeightCapture:
    """Registro de peso asociado a un producto específico."""

    product_id: str
    reading: ScaleReading


@runtime_checkable
class RFIDReaderAdapter(Protocol):
    """Contrato mínimo esperado para un lector RFID."""

    name: str

    async def connect(self) -> None:
        """Inicializa la comunicación con el lector."""

    async def disconnect(self) -> None:
        """Libera la conexión con el lector."""

    async def read_single(self) -> RFIDTagReading | None:
        """Obtiene una lectura única (EPC) o devuelve ``None`` si no hay etiquetas."""

    async def read_batch(self, timeout_s: float | None = None) -> list[RFIDTagReading]:
        """Lee múltiples EPC dentro de una ventana opcional de tiempo."""


@runtime_checkable
class ScaleAdapter(Protocol):
    """Contrato mínimo esperado para una báscula digital."""

    name: str

    async def connect(self) -> None:
        """Inicializa la comunicación con la báscula."""

    async def disconnect(self) -> None:
        """Libera la conexión con la báscula."""

    async def read_weight(self) -> ScaleReading:
        """Devuelve una medición de peso normalizada en kilogramos."""


class ProductInputRepository(Protocol):
    """Repositorio abstracto para persistir asociaciones de hardware con productos."""

    async def bind_epc(self, epc: str, product_id: str, source: str) -> RFIDProductLink:
        """Guarda la asociación EPC⇄producto y devuelve el enlace registrado."""

    async def record_weight(self, product_id: str, reading: ScaleReading) -> ProductWeightCapture:
        """Persiste una medición de peso ligada a un producto."""


async def capture_and_link_epc(
    reader: RFIDReaderAdapter,
    repository: ProductInputRepository,
    product_id: str,
    *,
    source: str | None = None,
) -> RFIDProductLink | None:
    """Lee un EPC y lo asocia con el producto indicado.

    Si no se detecta ninguna etiqueta, devuelve ``None``.
    """

    await reader.connect()
    try:
        reading = await reader.read_single()
        if reading is None:
            return None
        return await repository.bind_epc(
            reading.epc,
            product_id,
            source or reading.reader,
        )
    finally:
        await reader.disconnect()


async def capture_weight_for_product(
    scale: ScaleAdapter,
    repository: ProductInputRepository,
    product_id: str,
) -> ProductWeightCapture:
    """Obtiene el peso actual y lo registra para el producto indicado."""

    await scale.connect()
    try:
        reading = await scale.read_weight()
        return await repository.record_weight(product_id, reading)
    finally:
        await scale.disconnect()
