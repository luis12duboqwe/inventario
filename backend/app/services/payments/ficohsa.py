from __future__ import annotations

from decimal import Decimal
from typing import Any

from .base import (
    HondurasBankClient,
    HondurasPaymentAdapter,
    PaymentConfirmation,
    PaymentExecutionError,
    PaymentInitiation,
    PaymentToken,
    PaymentTokenizationError,
)


class _FallbackFicohsaClient:
    """Simulador simple para integraciones locales con Banco Ficohsa."""

    def tokenize(self, payload: dict[str, Any]) -> dict[str, Any]:
        holder = str(payload.get("cardholder") or "anon").upper()
        return {
            "token": f"FIC-{holder[:4]}-{payload.get('reference', '0000')}",
            "raw": payload,
        }

    def create_payment(
        self,
        *,
        token: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "transaction": f"fic-{token}-{int(amount * 100)}",
            "status": "pending",
            "metadata": metadata or {},
        }

    def confirm_payment(
        self,
        *,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "transaction": transaction_id,
            "status": "reconciled",
            "auth_code": f"FIC{int(amount * 1000) % 9999:04d}",
            "raw": {"currency": currency, "metadata": metadata or {}},
        }


class BancoFicohsaAdapter(HondurasPaymentAdapter):
    """Adaptador del SDK de Banco Ficohsa Honduras."""

    name = "banco_ficohsa"

    def __init__(self, client: HondurasBankClient | None = None) -> None:
        self._client = client or _FallbackFicohsaClient()

    def tokenize(self, payload: dict[str, Any]) -> PaymentToken:
        try:
            response = self._client.tokenize(payload)
        except Exception as exc:  # pragma: no cover - errores del SDK
            raise PaymentTokenizationError("Ficohsa rechazó la tokenización.") from exc
        token = str(response.get("token") or "").strip()
        if not token:
            raise PaymentTokenizationError(
                "Token vacío recibido desde Ficohsa.",
                metadata={"response": response},
            )
        return PaymentToken(token=token, raw=response)

    def initiate(
        self,
        *,
        token: PaymentToken,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentInitiation:
        try:
            response = self._client.create_payment(
                token=token.token,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - errores del SDK
            raise PaymentExecutionError(
                "Ficohsa no aceptó el cargo.",
                metadata={"token": token.token},
            ) from exc
        transaction_id = str(response.get("transaction") or "").strip()
        status = str(response.get("status") or "").strip().lower() or "error"
        if not transaction_id:
            raise PaymentExecutionError(
                "Ficohsa devolvió una referencia vacía.",
                metadata={"response": response},
            )
        return PaymentInitiation(
            transaction_id=transaction_id,
            status=status,
            raw=response,
        )

    def confirm(
        self,
        *,
        initiation: PaymentInitiation,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentConfirmation:
        try:
            response = self._client.confirm_payment(
                transaction_id=initiation.transaction_id,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - errores del SDK
            raise PaymentExecutionError(
                "Ficohsa no confirmó la conciliación.",
                metadata={"transaction_id": initiation.transaction_id},
            ) from exc
        status = str(response.get("status") or "").strip().lower() or "error"
        approval_code = response.get("auth_code")
        return PaymentConfirmation(
            transaction_id=initiation.transaction_id,
            status=status,
            approval_code=str(approval_code) if approval_code else None,
            reconciliation_id=initiation.transaction_id[::-1],
            raw=response,
        )


__all__ = ["BancoFicohsaAdapter"]
