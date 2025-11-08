from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.app.middleware import build_reason_header_middleware
from backend.app.models.audit import AuditLog
from backend.app.services.audit import render_audit_pdf
from backend.app.utils import audit as audit_utils
from backend.app.main import SENSITIVE_METHODS, SENSITIVE_PREFIXES


@dataclass(slots=True)
class _StubAuditLog:
    id: int
    action: str
    entity_type: str
    entity_id: str
    details: str | None
    created_at: datetime
    performed_by_id: int | None = None


def _build_audit_pdf_payload() -> tuple[list[AuditLog], audit_utils.AuditAlertSummary]:
    base_time = datetime.now(timezone.utc)
    logs: list[AuditLog] = [
        _StubAuditLog(
            id=1,
            action="sync_fail",
            entity_type="sync_session",
            entity_id="ABC-1",
            details="Sincronización fallida",
            created_at=base_time - timedelta(minutes=5),
        ),
        _StubAuditLog(
            id=2,
            action="user_login",
            entity_type="user",
            entity_id="auditor",
            details="Inicio de sesión exitoso",
            created_at=base_time - timedelta(minutes=3),
        ),
    ]
    summary = audit_utils.summarize_alerts(logs)
    return logs, summary


def test_render_audit_pdf_generates_dark_theme_document() -> None:
    logs, summary = _build_audit_pdf_payload()
    filters = {"action": "sync_fail"}

    pdf_bytes = render_audit_pdf(logs, filters=filters, alerts=summary)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_reason_header_middleware_enforces_and_stores_reason() -> None:
    app = FastAPI()
    middleware = build_reason_header_middleware(
        sensitive_methods=SENSITIVE_METHODS,
        sensitive_prefixes=SENSITIVE_PREFIXES,
    )

    @app.middleware("http")
    async def _reason_middleware(request: Request, call_next):
        return await middleware(request, call_next)

    @app.post("/inventory/adjust")
    async def protected(request: Request):
        return JSONResponse({"reason": getattr(request.state, "x_reason", None)})

    @app.get("/customers/search")
    async def optional():
        return JSONResponse({"ok": True})

    client = TestClient(app)

    response = client.post("/inventory/adjust")
    assert response.status_code == 400
    assert response.json()["detail"] == "Reason header requerido"

    short_header = client.post("/inventory/adjust", headers={"X-Reason": "1234"})
    assert short_header.status_code == 400

    valid = client.post("/inventory/adjust", headers={"X-Reason": "Ajuste critico"})
    assert valid.status_code == 200
    assert valid.json()["reason"] == "Ajuste critico"

    invalid_optional = client.get("/customers/search", headers={"X-Reason": "bad"})
    assert invalid_optional.status_code == 400

    ok_optional = client.get("/customers/search", headers={"X-Reason": "Consulta clientes"})
    assert ok_optional.status_code == 200
    assert ok_optional.json()["ok"] is True
