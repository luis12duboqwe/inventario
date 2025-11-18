"""Utilidades de formateo localizadas para reportes.

Estas rutinas centralizan los formatos en español hondureño,
incluyendo la conversión visible a USD cuando exista una tasa
configurada.
"""

from decimal import Decimal, ROUND_HALF_UP

from ..config import settings


def _normalize_decimal(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_spanish_number(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "∂").replace(".", ",").replace("∂", ".")


def format_hnl(value: Decimal | float | int) -> str:
    normalized = _normalize_decimal(value)
    return f"L {_format_spanish_number(normalized)}"


def format_usd(value: Decimal | float | int, *, rate: Decimal | None = None) -> str | None:
    normalized_rate = _normalize_decimal(rate or settings.usd_exchange_rate)
    if normalized_rate <= 0:
        return None
    normalized_value = _normalize_decimal(value) / normalized_rate
    return f"$ {_format_spanish_number(normalized_value)}"


def format_dual_currency(value: Decimal | float | int, *, rate: Decimal | None = None) -> str:
    base_label = format_hnl(value)
    usd_label = format_usd(value, rate=rate)
    if usd_label is None:
        return base_label
    return f"{base_label} (≈ {usd_label})"


def format_units(value: int) -> str:
    return f"{value:,}".replace(",", ".")
