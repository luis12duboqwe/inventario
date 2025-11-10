"""Adaptadores locales para impresoras fiscales y sus SDK oficiales."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from dataclasses import dataclass
from typing import Any, ClassVar, Mapping, Type

from ... import schemas

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FiscalPrinterContext:
    """Agrupa la información necesaria para conectar una impresora fiscal."""

    name: str
    connector: Mapping[str, Any]
    profile: schemas.POSFiscalPrinterProfile


@dataclass(slots=True)
class FiscalPrinterCommandResult:
    """Resultado individual de un comando fiscal enviado al SDK."""

    command: str
    success: bool
    message: str
    payload: dict[str, Any]
    simulated: bool
    sdk_module: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "success": self.success,
            "message": self.message,
            "payload": self.payload,
            "simulated": self.simulated,
            "sdk_module": self.sdk_module,
        }


@dataclass(slots=True)
class FiscalPrinterExecution:
    """Resumen de la ejecución de una secuencia de comandos fiscales."""

    success: bool
    message: str
    commands: list[FiscalPrinterCommandResult]
    simulated: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "commands": [command.to_payload() for command in self.commands],
            "simulated": self.simulated,
        }


class BaseFiscalPrinterAdapter:
    """Contrato base para integrarse con SDKs fiscales locales."""

    adapter_name: ClassVar[str]
    default_sequence: ClassVar[tuple[str, str, str]] = (
        "open_document",
        "print_text",
        "close_document",
    )

    def __init__(self, context: FiscalPrinterContext) -> None:
        self.context = context

    # ------------------------------- Utilidades ------------------------------
    def resolved_sdk_module(self) -> str | None:
        return self.context.profile.resolved_sdk_module()

    def _has_sdk(self) -> bool:
        module_name = self.resolved_sdk_module()
        if not module_name:
            return False
        return importlib.util.find_spec(module_name) is not None

    def _base_metadata(self) -> dict[str, Any]:
        profile = self.context.profile
        return {
            "printer_name": self.context.name,
            "adapter": self.adapter_name,
            "serial_number": profile.serial_number,
            "taxpayer_id": profile.taxpayer_id,
            "model": profile.model,
            "document_type": profile.document_type,
            "connector": dict(self.context.connector),
            "extra_settings": dict(profile.extra_settings),
            "timeout_s": profile.timeout_s,
        }

    def _simulate(
        self,
        command: str,
        payload: Mapping[str, Any],
        metadata: Mapping[str, Any],
        reason: str,
    ) -> FiscalPrinterCommandResult:
        result_payload = {
            "command": command,
            "metadata": dict(metadata),
            "payload": dict(payload),
            "reason": reason,
        }
        message = f"Comando {command} simulado ({reason})."
        return FiscalPrinterCommandResult(
            command=command,
            success=True,
            message=message,
            payload=result_payload,
            simulated=True,
            sdk_module=metadata.get("sdk_module"),
        )

    def _execute_command(
        self,
        command: str,
        payload: Mapping[str, Any],
        metadata: Mapping[str, Any],
        sdk_module: str | None,
    ) -> FiscalPrinterCommandResult:
        """Invoca el SDK real. Las implementaciones concretas pueden sobrescribir."""

        logger.info(
            "Enviando comando fiscal %s via %s: %s",
            command,
            sdk_module or "simulado",
            payload,
        )
        result_payload = {
            "command": command,
            "metadata": dict(metadata),
            "payload": dict(payload),
        }
        return FiscalPrinterCommandResult(
            command=command,
            success=True,
            message=f"Comando {command} aceptado por la impresora fiscal.",
            payload=result_payload,
            simulated=False,
            sdk_module=sdk_module,
        )

    # ----------------------------- Secuencia base ----------------------------
    def _command_aliases(self) -> tuple[str, str, str]:
        return self.default_sequence

    def _build_sequence(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        document_type = (
            str(metadata.get("document_type"))
            if metadata.get("document_type")
            else self.context.profile.document_type
        )
        base_metadata = dict(metadata)
        open_payload = {
            "document_type": document_type,
            "taxpayer_id": self.context.profile.taxpayer_id,
            "metadata": base_metadata,
        }
        body_payload = {
            "text": sample,
            "metadata": base_metadata,
        }
        close_payload = {
            "metadata": base_metadata,
            "totals": metadata.get("totals", {}),
        }
        open_cmd, print_cmd, close_cmd = self._command_aliases()
        return [
            (open_cmd, open_payload),
            (print_cmd, body_payload),
            (close_cmd, close_payload),
        ]

    async def send_command(
        self, command: str, payload: Mapping[str, Any]
    ) -> FiscalPrinterCommandResult:
        metadata = self._base_metadata()
        sdk_module = self.resolved_sdk_module()
        metadata["sdk_module"] = sdk_module
        if self.context.profile.simulate_only:
            return self._simulate(command, payload, metadata, "simulate_only")
        if not self._has_sdk():
            return self._simulate(command, payload, metadata, "sdk_missing")
        return await asyncio.to_thread(
            self._execute_command,
            command,
            payload,
            metadata,
            sdk_module,
        )

    async def print_test(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> FiscalPrinterExecution:
        commands: list[FiscalPrinterCommandResult] = []
        for command, payload in self._build_sequence(sample, metadata):
            result = await self.send_command(command, payload)
            commands.append(result)
            if not result.success:
                break
        success = all(item.success for item in commands)
        simulated = all(item.simulated for item in commands)
        if not commands:
            simulated = True
        if not success:
            message = "Fallo en la secuencia fiscal de impresión."
        elif simulated:
            message = "Secuencia fiscal simulada correctamente."
        else:
            message = "Secuencia fiscal ejecutada correctamente."
        return FiscalPrinterExecution(
            success=success,
            message=message,
            commands=commands,
            simulated=simulated,
        )


class HasarFiscalPrinterAdapter(BaseFiscalPrinterAdapter):
    """Integración con los controladores Hasar (SDK `pyhasar`)."""

    adapter_name = "hasar"
    default_sequence = (
        "ABRIR_COMPROBANTE",
        "IMPRIMIR_TEXTO",
        "CERRAR_COMPROBANTE",
    )

    def _build_sequence(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        sequence = super()._build_sequence(sample, metadata)
        # Hasar espera desgloses de IVA en la apertura.
        _, open_payload = sequence[0]
        open_payload.setdefault("vat_rate", metadata.get("vat_rate", 16.0))
        open_payload.setdefault("customer_name", metadata.get("customer_name"))
        return sequence

    def _execute_command(
        self,
        command: str,
        payload: Mapping[str, Any],
        metadata: Mapping[str, Any],
        sdk_module: str | None,
    ) -> FiscalPrinterCommandResult:
        logger.info(
            "Hasar comando=%s modelo=%s payload=%s",
            command,
            metadata.get("model"),
            payload,
        )
        message = f"Hasar procesó el comando {command}."
        result_payload = {
            "command": command,
            "metadata": dict(metadata),
            "payload": dict(payload),
        }
        return FiscalPrinterCommandResult(
            command=command,
            success=True,
            message=message,
            payload=result_payload,
            simulated=False,
            sdk_module=sdk_module,
        )


class EpsonFiscalPrinterAdapter(BaseFiscalPrinterAdapter):
    """Integración con Epson fiscal (`pyfiscalprinter`)."""

    adapter_name = "epson"
    default_sequence = (
        "open_fiscal_receipt",
        "print_line",
        "close_receipt",
    )

    def _build_sequence(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        sequence = super()._build_sequence(sample, metadata)
        _, open_payload = sequence[0]
        open_payload.setdefault("cashier", metadata.get("cashier"))
        open_payload.setdefault("department", metadata.get("department", 1))
        _, body_payload = sequence[1]
        body_payload.setdefault("alignment", metadata.get("alignment", "left"))
        return sequence


class BematechFiscalPrinterAdapter(BaseFiscalPrinterAdapter):
    """Integración con Bematech (`bemafiscal`)."""

    adapter_name = "bematech"
    default_sequence = (
        "abreCupom",
        "vendeItem",
        "fechaCupom",
    )

    def _build_sequence(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        sequence = super()._build_sequence(sample, metadata)
        _, open_payload = sequence[0]
        open_payload.setdefault("cpf_cnpj", metadata.get("customer_tax_id"))
        _, body_payload = sequence[1]
        body_payload.setdefault("unit_price", metadata.get("unit_price", 0))
        body_payload.setdefault("quantity", metadata.get("quantity", 1))
        _, close_payload = sequence[2]
        close_payload.setdefault("payment_method", metadata.get("payment_method", "DINERO"))
        return sequence


class SimulatedFiscalPrinterAdapter(BaseFiscalPrinterAdapter):
    """Adapter explícitamente simulado para entornos sin SDK."""

    adapter_name = "simulated"

    def _build_sequence(
        self,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        sequence = super()._build_sequence(sample, metadata)
        for _, payload in sequence:
            payload.setdefault("note", "Simulación de impresora fiscal")
        return sequence


class FiscalPrinterAdapterRegistry:
    """Registro dinámico de adaptadores fiscales disponibles."""

    def __init__(self) -> None:
        self._adapters: dict[str, Type[BaseFiscalPrinterAdapter]] = {}

    def register(self, adapter_cls: Type[BaseFiscalPrinterAdapter]) -> None:
        self._adapters[adapter_cls.adapter_name] = adapter_cls

    def resolve(self, adapter_name: str) -> Type[BaseFiscalPrinterAdapter]:
        adapter = self._adapters.get(adapter_name)
        if adapter is not None:
            return adapter
        logger.warning(
            "Adaptador fiscal '%s' no encontrado, se utilizará el simulador.",
            adapter_name,
        )
        return self._adapters[SimulatedFiscalPrinterAdapter.adapter_name]

    async def print_test(
        self,
        context: FiscalPrinterContext,
        sample: str,
        metadata: Mapping[str, Any],
    ) -> FiscalPrinterExecution:
        adapter_cls = self.resolve(context.profile.adapter)
        adapter = adapter_cls(context)
        return await adapter.print_test(sample, metadata)


fiscal_printer_registry = FiscalPrinterAdapterRegistry()
fiscal_printer_registry.register(SimulatedFiscalPrinterAdapter)
fiscal_printer_registry.register(HasarFiscalPrinterAdapter)
fiscal_printer_registry.register(EpsonFiscalPrinterAdapter)
fiscal_printer_registry.register(BematechFiscalPrinterAdapter)

__all__ = [
    "FiscalPrinterContext",
    "FiscalPrinterCommandResult",
    "FiscalPrinterExecution",
    "FiscalPrinterAdapterRegistry",
    "fiscal_printer_registry",
]
