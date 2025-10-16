"""Utilidades ligeras de cache con TTL en memoria."""
from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Dict, Generic, Hashable, Optional, Tuple, TypeVar


T = TypeVar("T")


class TTLCache(Generic[T]):
    """Cache en memoria con expiración basada en TTL."""

    __slots__ = ("_ttl", "_lock", "_values")

    def __init__(self, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")
        self._ttl = float(ttl_seconds)
        self._lock = Lock()
        self._values: Dict[Hashable, Tuple[float, T]] = {}

    def get(self, key: Hashable) -> Optional[T]:
        now = monotonic()
        with self._lock:
            record = self._values.get(key)
            if record is None:
                return None
            expires_at, value = record
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: Hashable, value: T) -> None:
        expires_at = monotonic() + self._ttl
        with self._lock:
            self._values[key] = (expires_at, value)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


__all__ = ["TTLCache"]
