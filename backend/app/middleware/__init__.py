"""Middlewares corporativos para Softmobile 2025."""

from .reason import (
    ReasonHeaderError,
    ensure_reason_header,
    requires_reason_header,
)

__all__ = [
    "ReasonHeaderError",
    "ensure_reason_header",
    "requires_reason_header",
]
