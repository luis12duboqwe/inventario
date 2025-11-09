"""Servicios de pagos electrónicos para el POS."""

from .banco_atlantida import BancoAtlantidaAdapter
from .ficohsa import BancoFicohsaAdapter
from .pos import ElectronicPaymentError, process_electronic_payments
from .registry import registry

__all__ = [
    "BancoAtlantidaAdapter",
    "BancoFicohsaAdapter",
    "ElectronicPaymentError",
    "process_electronic_payments",
    "registry",
]
