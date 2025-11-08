from __future__ import annotations

import importlib
import json
import logging as std_logging
import sys
from types import ModuleType

import pytest

from backend.core import logging as core_logging


@pytest.fixture
def reload_core_logging(monkeypatch):
    """Permite recargar el módulo de logging en modo compatibilidad."""

    original_module = sys.modules.get("backend.core.logging")
    original_loguru = sys.modules.get("loguru")

    def _reload_without_loguru() -> ModuleType:
        sys.modules.pop("backend.core.logging", None)
        monkeypatch.setitem(sys.modules, "loguru", None)
        module = importlib.import_module("backend.core.logging")
        return module

    yield _reload_without_loguru

    sys.modules.pop("backend.core.logging", None)
    if original_loguru is not None:
        sys.modules["loguru"] = original_loguru
    if original_module is not None:
        sys.modules["backend.core.logging"] = original_module
    importlib.import_module("backend.core.logging")


def test_loguru_setup_injects_context(capfd):
    core_logging.setup_logging()
    token = core_logging.bind_context(user_id="auditor", path="/demo")
    core_logging.logger.info("evento_de_prueba")
    core_logging.reset_context(token)

    output = capfd.readouterr().out.strip().splitlines()
    assert output, "Se esperaba al menos una línea de log en la salida capturada."
    payload = json.loads(output[-1])
    record = payload["record"]
    assert record["message"] == "evento_de_prueba"
    assert record["extra"]["user_id"] == "auditor"
    assert record["extra"]["path"] == "/demo"


def test_reset_context_clears_previous_values(capfd):
    core_logging.setup_logging()
    token = core_logging.bind_context(user_id="auditor")
    core_logging.logger.info("primero")
    first_output = capfd.readouterr().out.strip()
    core_logging.reset_context(token)
    core_logging.logger.info("segundo")
    second_output = capfd.readouterr().out.strip()

    first_payload = json.loads(first_output)
    second_payload = json.loads(second_output)

    assert first_payload["record"]["extra"]["user_id"] == "auditor"
    assert "user_id" not in second_payload["record"]["extra"]


def test_json_formatter_includes_context_and_extras(reload_core_logging):
    module = reload_core_logging()
    module.setup_logging()

    token = module.bind_context(user_id="compat", path="/fallback")
    try:
        record = std_logging.LogRecord(
            name="softmobile-tests",
            level=std_logging.INFO,
            pathname=__file__,
            lineno=123,
            msg="mensaje_fallback",
            args=(),
            exc_info=None,
        )
        record.detalle = "extra"
        formatter = module._JsonFormatter()  # type: ignore[attr-defined]
        formatted = formatter.format(record)
        payload = json.loads(formatted)
    finally:
        module.reset_context(token)

    assert payload["message"] == "mensaje_fallback"
    assert payload["user_id"] == "compat"
    assert payload["path"] == "/fallback"
    assert payload["detalle"] == "extra"
