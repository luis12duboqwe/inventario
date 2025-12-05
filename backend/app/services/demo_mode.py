"""Utilidades para habilitar un modo demo aislado con datos ficticios."""
from __future__ import annotations

from typing import List

from ..config import settings
from ..schemas.help_center import DemoDataset, HelpGuide


def is_demo_mode_enabled() -> bool:
    """Expone el flag global de modo demostración."""

    return settings.demo_mode_enabled


def get_demo_dataset() -> DemoDataset:
    """Construye un dataset de referencia sin tocar la base corporativa."""

    inventory_samples: List[dict] = [
        {
            "sku": "DEMO-IMEI-001",
            "name": "Smartphone de prueba",
            "imei": "111222333444555",
            "serial": "SN-DEMO-001",
            "store": "Central demo",
            "status": "EN_LINEA",
            "quantity": 12,
        },
        {
            "sku": "DEMO-LAP-002",
            "name": "Laptop corporativa demo",
            "serial": "SN-DEMO-002",
            "store": "Sucursal Norte",
            "status": "RESERVADO",
            "quantity": 4,
        },
    ]

    operations_samples: List[dict] = [
        {
            "type": "venta",
            "reference": "POS-DEMO-1001",
            "reason": "Demostración sin impacto",
            "amount": 12500,
            "payment_methods": ["CASH", "CARD"],
        },
        {
            "type": "transferencia",
            "reference": "TRF-DEMO-2001",
            "reason": "Flujo SOLICITADA→EN_TRANSITO→RECIBIDA",
            "amount": 0,
            "payment_methods": [],
        },
    ]

    contacts_samples: List[dict] = [
        {
            "name": "Cliente demostración",
            "tier": "VIP",
            "credit_limit": 15000,
            "balance": 0,
        },
        {
            "name": "Proveedor demo",
            "tier": "Proveedor preferente",
            "credit_limit": 0,
            "balance": 0,
        },
    ]

    return DemoDataset(
        inventory=inventory_samples,
        operations=operations_samples,
        contacts=contacts_samples,
    )


def get_help_guides() -> list[HelpGuide]:
    """Entrega guías contextuales alineadas a los manuales PDF y videos."""

    base_path = "docs/capacitacion"
    return [
        HelpGuide(
            module="inventory",
            title="Inventario y auditoría",
            summary="Altas con IMEI/serie, ajustes con X-Reason y reportes oscuros.",
            steps=[
                "Registra equipos con IMEI/serie y proveedor en Inventario → Productos.",
                "Ajusta existencias con motivo corporativo (X-Reason) y valida el impacto.",
                "Descarga reportes PDF oscuros de rotación y aging para el comité.",
            ],
            manual=f"{base_path}/manual_inventario.pdf",
            video=f"{base_path}/videos/inventario_resumen.txt",
        ),
        HelpGuide(
            module="operations",
            title="POS, compras y transferencias",
            summary="Flujos de ventas, compras parciales y transferencias con stock seguro.",
            steps=[
                "Ejecuta ventas POS con pago mixto y motivo corporativo obligatorio.",
                "Recibe compras parciales y valida el promedio ponderado del costo.",
                "Confirma transferencias EN_TRANSITO→RECIBIDA sin afectar inventario productivo.",
            ],
            manual=f"{base_path}/manual_operaciones.pdf",
            video=f"{base_path}/videos/operaciones_resumen.txt",
        ),
        HelpGuide(
            module="analytics",
            title="Analítica avanzada",
            summary="Rotación, aging y forecast en tema oscuro con exportes PDF/Excel.",
            steps=[
                "Filtra por sucursal y rango para visualizar tarjetas y gráficas en el tablero.",
                "Ejecuta el forecast de quiebres y exporta el PDF oscuro para compras.",
                "Monitorea alertas críticas desde el mismo tablero sin salir del módulo.",
            ],
            manual=f"{base_path}/manual_analytics.pdf",
            video=f"{base_path}/videos/analytics_resumen.txt",
        ),
        HelpGuide(
            module="security",
            title="Seguridad y auditoría",
            summary="Sesiones, 2FA opcional y X-Reason en operaciones sensibles.",
            steps=[
                "Activa 2FA cuando el flag lo permita y entrega el código TOTP al usuario.",
                "Revoca sesiones sospechosas dejando trazabilidad en la bitácora.",
                "Exige X-Reason ≥ 5 caracteres en exportes y operaciones críticas.",
            ],
            manual=f"{base_path}/manual_seguridad.pdf",
            video=f"{base_path}/videos/seguridad_resumen.txt",
        ),
        HelpGuide(
            module="config",
            title="Configuración de Impresoras",
            summary="Guía técnica para configurar impresoras térmicas y márgenes.",
            steps=[
                "Instala el controlador de tu impresora térmica (Zebra/Epson) en el sistema operativo.",
                "Configura el tamaño de papel a 80mm o 58mm en las preferencias de impresión del navegador.",
                "Desactiva encabezados y pies de página en el diálogo de impresión del sistema.",
                "Usa la vista previa de recibo en POS para validar márgenes antes de imprimir.",
            ],
            manual=f"{base_path}/manual_impresoras.pdf",
            video=f"{base_path}/videos/impresoras_setup.txt",
        ),
        HelpGuide(
            module="help",
            title="Centro de ayuda",
            summary="Acceso rápido a manuales PDF y guías en video sin salir del panel.",
            steps=[
                "Consulta las guías contextuales por módulo.",
                "Descarga los manuales PDF desde docs/capacitacion en español.",
                "Activa el modo demostración para practicar con datos ficticios aislados.",
            ],
            manual=f"{base_path}/README.md",
            video=f"{base_path}/videos/operaciones_resumen.txt",
        ),
    ]
