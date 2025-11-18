"""Conectores para impresoras de etiquetas Zebra y Epson.

Provee payloads de impresión directa para aplicaciones locales o bridges
que consumen eventos de hardware vía WebSocket.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from ...schemas import POSConnectorSettings


class LabelPrinterVendor(str, Enum):
    """Fabricantes soportados para impresión directa de etiquetas."""

    ZEBRA = "zebra"
    EPSON = "epson"


@dataclass(slots=True)
class LabelDirectPrintJob:
    """Describe un trabajo de impresión directa."""

    vendor: LabelPrinterVendor
    template: str
    commands: str
    connector: Mapping[str, Any] | None
    content_type: str

    def as_event(self, *, store_id: int) -> dict[str, Any]:
        """Serializa el trabajo como evento para el canal de hardware."""

        payload: dict[str, Any] = {
            "event": "label.print",
            "store_id": store_id,
            "vendor": self.vendor.value,
            "template": self.template,
            "commands": self.commands,
            "content_type": self.content_type,
        }
        if self.connector:
            payload["connector"] = dict(self.connector)
        return payload


def build_connector_payload(
    connector: POSConnectorSettings | None,
) -> Mapping[str, Any] | None:
    """Normaliza el conector recibido para que sea usable por bridges locales."""

    if connector is None:
        return None
    payload = {
        "type": connector.type.value,
        "identifier": connector.identifier,
    }
    if connector.path:
        payload["path"] = connector.path
    if connector.host:
        payload["host"] = connector.host
    if connector.port is not None:
        payload["port"] = connector.port
    return payload


def build_zebra_job(
    *,
    template: str,
    commands: str,
    connector: POSConnectorSettings | None,
) -> LabelDirectPrintJob:
    """Crea un trabajo para impresoras Zebra (ZPL/EPL)."""

    return LabelDirectPrintJob(
        vendor=LabelPrinterVendor.ZEBRA,
        template=template,
        commands=commands,
        connector=build_connector_payload(connector),
        content_type="text/zpl",
    )


def build_epson_job(
    *,
    template: str,
    commands: str,
    connector: POSConnectorSettings | None,
) -> LabelDirectPrintJob:
    """Crea un trabajo para impresoras Epson (ESC/POS)."""

    return LabelDirectPrintJob(
        vendor=LabelPrinterVendor.EPSON,
        template=template,
        commands=commands,
        connector=build_connector_payload(connector),
        content_type="text/escpos",
    )
