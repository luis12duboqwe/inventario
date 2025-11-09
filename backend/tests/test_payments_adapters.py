from decimal import Decimal

from backend.app.services.payments import (
    BancoAtlantidaAdapter,
    BancoFicohsaAdapter,
    registry,
)


def test_banco_atlantida_adapter_flow():
    adapter = BancoAtlantidaAdapter()
    token = adapter.tokenize({"reference": "9876"})
    assert token.token.startswith("ATL-")

    initiation = adapter.initiate(token=token, amount=Decimal("100.00"), currency="HNL")
    assert initiation.transaction_id

    confirmation = adapter.confirm(
        initiation=initiation,
        amount=Decimal("100.00"),
        currency="HNL",
    )
    assert confirmation.approval_code is not None
    assert confirmation.reconciled is True


def test_banco_ficohsa_adapter_flow():
    adapter = BancoFicohsaAdapter()
    token = adapter.tokenize({"reference": "4444", "cardholder": "Cliente POS"})
    assert token.token.startswith("FIC-")

    initiation = adapter.initiate(token=token, amount=Decimal("55.50"), currency="HNL")
    assert initiation.transaction_id.startswith("fic-")

    confirmation = adapter.confirm(
        initiation=initiation,
        amount=Decimal("55.50"),
        currency="HNL",
    )
    assert confirmation.reconciled is True


def test_registry_returns_configured_adapters():
    adapter = registry.get("banco_atlantida")
    assert isinstance(adapter, BancoAtlantidaAdapter)
    other = registry.get("banco_ficohsa")
    assert isinstance(other, BancoFicohsaAdapter)
