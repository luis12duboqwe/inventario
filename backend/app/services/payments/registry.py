from __future__ import annotations

from typing import Callable, Dict

from .base import HondurasPaymentAdapter
from .banco_atlantida import BancoAtlantidaAdapter
from .ficohsa import BancoFicohsaAdapter


AdapterFactory = Callable[[], HondurasPaymentAdapter]


class AdapterRegistry:
    """Registro en memoria de adaptadores bancarios disponibles."""

    def __init__(self) -> None:
        self._registry: Dict[str, AdapterFactory] = {}
        self.register("banco_atlantida", BancoAtlantidaAdapter)
        self.register("banco_ficohsa", BancoFicohsaAdapter)

    def register(self, key: str, factory: AdapterFactory) -> None:
        normalized = key.strip().lower()
        self._registry[normalized] = factory

    def get(self, key: str) -> HondurasPaymentAdapter:
        normalized = key.strip().lower()
        try:
            factory = self._registry[normalized]
        except KeyError as exc:
            raise LookupError(f"No existe adaptador bancario para '{key}'.") from exc
        adapter = factory()
        return adapter


registry = AdapterRegistry()

__all__ = ["registry", "AdapterRegistry", "AdapterFactory"]
