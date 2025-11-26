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


class _FallbackAtlantidaClient:
    """Implementación mínima para entornos de prueba sin SDK real."""

    def tokenize(self, payload: dict[str, Any]) -> dict[str, Any]:
        reference = str(payload.get("reference") or "anon")[-4:]
        return {
            "token": f"ATL-{reference}",
            "expires_at": None,
            "raw": {"reference": reference},
        }

    def create_payment(
        self,
        *,
        token: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        transaction_id = f"atl-{token}-{int(amount * 100)}"
        return {
            "id": transaction_id,
            "status": "authorized",
            "raw": {"currency": currency, "metadata": metadata or {}},
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
            "id": transaction_id,
            "status": "confirmed",
            "approval_code": f"ATL-{str(amount).replace('.', '')[-6:]}",
            "reconciliation_id": transaction_id[::-1],
            "raw": {"currency": currency, "metadata": metadata or {}},
        }


class BancoAtlantidaAdapter(HondurasPaymentAdapter):
    """Adaptador para el SDK de Banco Atlántida Honduras."""

    name = "banco_atlantida"

    def __init__(self, client: HondurasBankClient | None = None) -> None:
        self._client = client or _FallbackAtlantidaClient()

    def tokenize(self, payload: dict[str, Any]) -> PaymentToken:
        try:
            response = self._client.tokenize(payload)
        except Exception as exc:  # pragma: no cover - errores del SDK
            raise PaymentTokenizationError("No fue posible tokenizar la tarjeta.") from exc

        token = str(response.get("token") or "").strip()
        if not token:
            raise PaymentTokenizationError(
                "Token inválido entregado por Banco Atlántida.",
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
                "Banco Atlántida rechazó la autorización.",
                metadata={"token": token.token},
            ) from exc
        transaction_id = str(response.get("id") or "").strip()
        status = str(response.get("status") or "").strip().lower() or "error"
        if not transaction_id:
            raise PaymentExecutionError(
                "La autorización de Banco Atlántida no devolvió referencia.",
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
                "Banco Atlántida no confirmó el cargo.",
                metadata={"transaction_id": initiation.transaction_id},
            ) from exc
        status = str(response.get("status") or "").strip().lower() or "error"
        approval_code = response.get("approval_code")
        reconciliation_id = response.get("reconciliation_id")
        return PaymentConfirmation(
            transaction_id=initiation.transaction_id,
            status=status,
            approval_code=str(approval_code) if approval_code else None,
            reconciliation_id=str(reconciliation_id)
            if reconciliation_id
            else None,
            raw=response,
        )


__all__ = ["BancoAtlantidaAdapter"]
