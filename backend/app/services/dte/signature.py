"""Utilidades de firma para documentos tributarios electrónicos."""
from __future__ import annotations

import base64
import hashlib
from decimal import Decimal


def _normalize_total(total: Decimal | float | int) -> Decimal:
    if isinstance(total, Decimal):
        return total.quantize(Decimal("0.01"))
    return Decimal(str(total)).quantize(Decimal("0.01"))


def build_signature(*, control_number: str, cai: str, total: Decimal | float | int, private_key: str) -> str:
    """Genera la firma digital simplificada compatible con el SAR."""

    normalized_total = _normalize_total(total)
    payload = f"{control_number}|{cai}|{normalized_total:.2f}|{private_key}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return base64.b64encode(digest).decode("ascii")


__all__ = ["build_signature"]
