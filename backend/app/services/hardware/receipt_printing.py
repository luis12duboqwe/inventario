"""Servicios para controlar impresoras, gavetas y pantallas del POS."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, TYPE_CHECKING

from fastapi import BackgroundTasks
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from .fiscal_printers import FiscalPrinterContext, fiscal_printer_registry

if TYPE_CHECKING:  # pragma: no cover - sólo para tipado
    from ...schemas import POSFiscalPrinterProfile

logger = logging.getLogger(__name__)


class ConnectorType(str, Enum):
    """Tipos de conectores soportados para hardware POS."""

    USB = "usb"
    NETWORK = "network"


class PrinterMode(str, Enum):
    """Tipos de impresora soportados por el servicio."""

    THERMAL = "thermal"
    FISCAL = "fiscal"


@dataclass(slots=True)
class ConnectorConfig:
    """Configuración base para conectores físicos o de red."""

    type: ConnectorType
    identifier: str
    path: str | None = None
    host: str | None = None
    port: int | None = None

    def describe(self) -> str:
        """Devuelve una descripción humana del conector."""

        if self.type is ConnectorType.USB:
            return f"USB:{self.path or self.identifier}"
        host = self.host or "localhost"
        port = self.port or 9100
        return f"NET:{host}:{port}"

    def as_payload(self) -> dict[str, Any]:
        """Serializa el conector para ser consumido por adaptadores."""

        payload: dict[str, Any] = {
            "type": self.type.value,
            "identifier": self.identifier,
        }
        if self.path:
            payload["path"] = self.path
        if self.host:
            payload["host"] = self.host
        if self.port is not None:
            payload["port"] = self.port
        return payload


@dataclass(slots=True)
class ReceiptPrintResult:
    """Resultado devuelto por una operación de impresión de recibo."""

    success: bool
    message: str
    payload: dict[str, Any]


class BasePrinter:
    """Implementación base para impresoras POS."""

    def __init__(self, name: str, connector: ConnectorConfig) -> None:
        self.name = name
        self.connector = connector

    async def print_text(self, text: str, **metadata: Any) -> ReceiptPrintResult:
        raise NotImplementedError


class ThermalPrinter(BasePrinter):
    """Simula una impresora térmica conectada por USB o red."""

    async def print_text(self, text: str, **metadata: Any) -> ReceiptPrintResult:
        logger.info(
            "Imprimiendo en térmica %s (%s)",
            self.name,
            self.connector.describe(),
        )
        payload = {
            "mode": PrinterMode.THERMAL.value,
            "connector": self.connector.describe(),
            "text": text,
            "metadata": metadata,
        }
        return ReceiptPrintResult(True, "Impresión térmica simulada correctamente.", payload)


class FiscalPrinter(BasePrinter):
    """Opera una impresora fiscal apoyándose en adaptadores específicos."""

    def __init__(
        self,
        name: str,
        connector: ConnectorConfig,
        profile: "POSFiscalPrinterProfile | None",
    ) -> None:
        super().__init__(name, connector)
        self.profile = profile

    async def print_text(self, text: str, **metadata: Any) -> ReceiptPrintResult:
        logger.info(
            "Imprimiendo en fiscal %s (%s)",
            self.name,
            self.connector.describe(),
        )
        metadata_payload = dict(metadata)
        if not self.profile:
            payload = {
                "mode": PrinterMode.FISCAL.value,
                "connector": self.connector.describe(),
                "text": text,
                "metadata": metadata_payload,
                "simulated": True,
                "reason": "missing_profile",
            }
            message = "Impresión fiscal simulada por falta de perfil configurado."
            logger.warning(
                "Perfil fiscal no configurado para %s; se ejecutará simulación.",
                self.name,
            )
            return ReceiptPrintResult(True, message, payload)

        context = FiscalPrinterContext(
            name=self.name,
            connector=self.connector.as_payload(),
            profile=self.profile,
        )
        execution = await fiscal_printer_registry.print_test(
            context,
            text,
            metadata_payload,
        )
        payload = {
            "mode": PrinterMode.FISCAL.value,
            "connector": self.connector.describe(),
            "adapter": self.profile.adapter,
            "profile": self.profile.model_dump(),
            "commands": [command.to_payload() for command in execution.commands],
            "metadata": metadata_payload,
            "simulated": execution.simulated,
        }
        return ReceiptPrintResult(execution.success, execution.message, payload)


class ReceiptPrinterService:
    """Resuelve impresoras según configuración y envía trabajos de recibo."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def _build_printer(
        self,
        printer_settings: Mapping[str, Any],
    ) -> BasePrinter:
        printer_name = str(printer_settings.get("name", "Desconocida"))
        mode = PrinterMode(
            printer_settings.get("mode", PrinterMode.THERMAL.value)
        )
        connector = printer_settings.get("connector") or {}
        connector_config = ConnectorConfig(
            type=ConnectorType(connector.get("type", ConnectorType.USB.value)),
            identifier=str(connector.get("identifier", printer_name)),
            path=connector.get("path"),
            host=connector.get("host"),
            port=connector.get("port"),
        )
        if mode is PrinterMode.FISCAL:
            fiscal_profile_data = printer_settings.get("fiscal_profile")
            fiscal_profile: "POSFiscalPrinterProfile | None" = None
            if fiscal_profile_data:
                from ... import schemas  # Importación perezosa

                fiscal_profile = schemas.POSFiscalPrinterProfile.model_validate(
                    fiscal_profile_data
                )
            return FiscalPrinter(printer_name, connector_config, fiscal_profile)
        return ThermalPrinter(printer_name, connector_config)

    async def print_sample(
        self,
        printer_settings: Mapping[str, Any],
        *,
        sample: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> ReceiptPrintResult:
        """Genera una impresión de prueba en la impresora indicada."""

        metadata = dict(metadata or {})
        async with self._lock:
            printer = await self._build_printer(printer_settings)
            result = await printer.print_text(sample, **metadata)
        return result


class HardwareChannelManager:
    """Administra conexiones WebSocket por sucursal."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, store_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(store_id, set()).add(websocket)
        await websocket.send_json(
            {
                "event": "hardware.ready",
                "store_id": store_id,
            }
        )

    async def disconnect(self, store_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(store_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(store_id, None)

    async def broadcast(self, store_id: int, payload: Mapping[str, Any]) -> None:
        message = {"store_id": store_id, **payload}
        async with self._lock:
            connections = list(self._connections.get(store_id, set()))
        if not connections:
            logger.debug("Sin conexiones activas para sucursal %s", store_id)
            return
        for connection in connections:
            try:
                if connection.application_state != WebSocketState.CONNECTED:
                    raise RuntimeError("websocket_not_connected")
                await connection.send_json(message)
            except Exception:  # pragma: no cover - log y continúa
                logger.exception("No fue posible enviar evento de hardware POS")
                await self.disconnect(store_id, connection)

    def schedule_broadcast(
        self,
        background_tasks: BackgroundTasks,
        store_id: int,
        payload: Mapping[str, Any],
    ) -> None:
        """Encola un broadcast de eventos para ejecutarse en segundo plano."""

        background_tasks.add_task(self.broadcast, store_id, dict(payload))

    async def handle_incoming(
        self,
        store_id: int,
        websocket: WebSocket,
        message: Mapping[str, Any],
    ) -> None:
        """Procesa mensajes entrantes de los clientes locales."""

        message_type = str(message.get("type", ""))
        if message_type == "ping":
            await websocket.send_json({"event": "hardware.pong", "store_id": store_id})
            return
        if message_type == "ack":
            logger.debug(
                "ACK de hardware POS recibido: store=%s, payload=%s",
                store_id,
                message,
            )
            return
        logger.info(
            "Mensaje de hardware POS ignorado: store=%s, payload=%s",
            store_id,
            message,
        )

    async def reset(self) -> None:
        """Cierra todas las conexiones activas (principalmente para pruebas)."""

        async with self._lock:
            connections = list(self._connections.items())
            self._connections.clear()
        for store_id, websockets in connections:
            for websocket in websockets:
                try:
                    await websocket.close()
                except Exception:  # pragma: no cover - mejor esfuerzo
                    logger.debug(
                        "No fue posible cerrar websocket de sucursal %s", store_id,
                    )


hardware_channels = HardwareChannelManager()
receipt_printer_service = ReceiptPrinterService()
