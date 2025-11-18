import asyncio

from backend.app import schemas
from backend.app.services.hardware.fiscal_printers import (
    FiscalPrinterContext,
    fiscal_printer_registry,
)


def test_fiscal_printer_registry_simulation_when_sdk_missing() -> None:
    profile = schemas.POSFiscalPrinterProfile(
        adapter="hasar",
        taxpayer_id="RTN999999999",
        serial_number="HAS-001",
        model="PR5F",
    )
    context = FiscalPrinterContext(
        name="HASAR-Demo",
        connector={"type": "usb", "identifier": "HASAR-Demo"},
        profile=profile,
    )
    execution = asyncio.run(
        fiscal_printer_registry.print_test(
            context,
            "PRUEBA FISCAL",
            {"cashier": "demo"},
        )
    )
    assert execution.success is True
    assert execution.simulated is True
    assert [command.command for command in execution.commands] == [
        "ABRIR_COMPROBANTE",
        "IMPRIMIR_TEXTO",
        "CERRAR_COMPROBANTE",
    ]
    assert execution.commands[0].simulated is True
    assert execution.commands[0].payload["metadata"]["adapter"] == "hasar"
    assert "simulada" in execution.message.lower()
