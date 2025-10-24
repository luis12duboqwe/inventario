"""Configuración centralizada de Loguru con contexto JSON."""
from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import datetime
from typing import Any, Final
import json
import logging
import sys

try:  # pragma: no cover - import guard exercised in environments con Loguru
    from loguru import logger as _loguru_logger
except ModuleNotFoundError:  # pragma: no cover - validated vía pruebas sin dependencia
    _loguru_logger = None  # type: ignore[assignment]

_HAS_LOGURU: Final[bool] = _loguru_logger is not None

_REQUEST_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})
_RESERVED_LOGGING_KEYS: Final[set[str]] = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


def _current_context() -> dict[str, Any]:
    """Devuelve el contexto activo asegurando claves estándar."""

    base = {"user_id": None, "path": None, "latency": None}
    context = _REQUEST_CONTEXT.get({})
    for key, value in context.items():
        if value is not None:
            base[key] = value
    return base


def _patch(record: dict[str, Any]) -> None:
    """Inyecta el contexto dinámico en cada log emitido."""

    extras = record.setdefault("extra", {})
    extras.update({k: v for k, v in _current_context().items() if v is not None})


class _JsonFormatter(logging.Formatter):
    """Formateador JSON para el modo de compatibilidad sin Loguru."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        payload.update({k: v for k, v in _current_context().items() if v is not None})
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if value is None or key in _RESERVED_LOGGING_KEYS:
                continue
            if key.startswith("extra_") and key[6:] in _RESERVED_LOGGING_KEYS:
                extras[key[6:]] = value
            else:
                extras[key] = value
        payload.update(extras)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class _BoundLogger(logging.LoggerAdapter):
    """Adaptador que imita ``logger.bind`` cuando Loguru no está instalado."""

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        super().__init__(logger, extra or {})

    def bind(self, **kwargs: Any) -> "_BoundLogger":
        context = {**self.extra}
        context.update({k: v for k, v in kwargs.items() if v is not None})
        return _BoundLogger(self.logger, context)

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extras = kwargs.get("extra", {})
        merged_extra = {**_current_context(), **self.extra, **extras}
        sanitized: dict[str, Any] = {}
        for key, value in merged_extra.items():
            if value is None:
                continue
            safe_key = key if key not in _RESERVED_LOGGING_KEYS else f"extra_{key}"
            sanitized[safe_key] = value
        kwargs["extra"] = sanitized
        return msg, kwargs


if _HAS_LOGURU:
    _logger = _loguru_logger  # type: ignore[assignment]
else:  # pragma: no cover - se ejerce en escenarios sin Loguru
    _base_logger = logging.getLogger("softmobile")
    _base_logger.setLevel(logging.INFO)
    _base_logger.propagate = False
    _logger = _BoundLogger(_base_logger)


def setup_logging() -> None:
    """Inicializa Loguru o activa un logger compatible en modo fallback."""

    if _HAS_LOGURU:
        assert _loguru_logger is not None  # ayuda a mypy en modo Loguru
        _loguru_logger.remove()
        _loguru_logger.configure(patcher=_patch)
        _loguru_logger.add(
            sys.stdout,
            serialize=True,
            backtrace=False,
            diagnose=False,
            level="INFO",
        )
    else:  # pragma: no cover - se valida indirectamente en pruebas
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        _base_logger.handlers.clear()
        _base_logger.addHandler(handler)


def bind_context(**kwargs: Any) -> Token:
    """Asocia valores contextuales que acompañarán los logs siguientes."""

    context = _REQUEST_CONTEXT.get({}).copy()
    for key, value in kwargs.items():
        if value is not None:
            context[key] = value
    return _REQUEST_CONTEXT.set(context)


def update_context(**kwargs: Any) -> None:
    """Actualiza el contexto activo sin crear un nuevo token."""

    context = _REQUEST_CONTEXT.get({}).copy()
    context.update(kwargs)
    _REQUEST_CONTEXT.set(context)


def reset_context(token: Token | None) -> None:
    """Restaura el contexto previo asociado al token recibido."""

    if token is not None:
        _REQUEST_CONTEXT.reset(token)


logger = _logger


__all__ = ["bind_context", "logger", "reset_context", "setup_logging", "update_context"]
