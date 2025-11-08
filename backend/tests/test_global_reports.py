from datetime import datetime

from fastapi import status

from backend.app import crud, models
from backend.app.config import settings
from backend.app.services import global_reports_data, global_reports_renderers
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "report_admin",
        "password": "Reportes123*",
        "full_name": "Supervisora Global",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json(), payload


def _login(client, username: str, password: str):
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


def test_global_reports_overview_dashboard_and_exports(client, db_session):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # Crear eventos de bitácora con diferentes niveles
    crud._log_action(
        db_session,
        action="inventory_audit",
        entity_type="inventory",
        entity_id="inv-001",
        performed_by_id=admin["id"],
        details="Auditoría programada",
    )
    crud._log_action(
        db_session,
        action="inventory_warning",
        entity_type="inventory",
        entity_id="inv-002",
        performed_by_id=admin["id"],
        details="Desviación detectada",
    )
    crud._create_system_log(  # type: ignore[attr-defined]
        db_session,
        audit_log=None,
        usuario=admin["username"],
        module="sincronizacion",
        action="sync_failed",
        description="Error crítico de sincronización",
        level=models.SystemLogLevel.CRITICAL,
    )
    crud.register_system_error(
        db_session,
        mensaje="Fallo al procesar cola",
        stack_trace="Traceback...",
        modulo="sincronizacion",
        usuario=admin["username"],
        ip_origen="127.0.0.1",
    )

    entry = crud.enqueue_sync_outbox(
        db_session,
        entity_type="inventory",
        entity_id="inv-001",
        operation="update",
        payload={"sku": "ABC-001", "quantity": 5},
    )
    entry.status = models.SyncOutboxStatus.FAILED
    entry.error_message = "Conexión rechazada"
    entry.updated_at = datetime.utcnow()
    db_session.add(entry)
    db_session.commit()

    overview_response = client.get("/reports/global/overview", headers=headers)
    assert overview_response.status_code == status.HTTP_200_OK
    overview = overview_response.json()
    assert overview["totals"]["logs"] >= 3
    assert overview["totals"]["errors"] >= 1
    assert any(alert["type"] == "sync_failure" for alert in overview["alerts"])
    assert any(log["nivel"] in {"error", "critical"} for log in overview["recent_logs"])

    info_only = client.get(
        "/reports/global/overview",
        params={"severity": "info"},
        headers=headers,
    )
    assert info_only.status_code == status.HTTP_200_OK
    info_payload = info_only.json()
    assert info_payload["totals"]["errors"] == 0

    dashboard_response = client.get("/reports/global/dashboard", headers=headers)
    assert dashboard_response.status_code == status.HTTP_200_OK
    dashboard = dashboard_response.json()
    assert dashboard["activity_series"]
    assert any(point["system_errors"] >= 0 for point in dashboard["activity_series"])

    pdf_response = client.get(
        "/reports/global/export",
        params={"format": "pdf"},
        headers={**headers, "X-Reason": "Reporte global corporativo"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    xlsx_response = client.get(
        "/reports/global/export",
        params={"format": "xlsx"},
        headers={**headers, "X-Reason": "Reporte global corporativo"},
    )
    assert xlsx_response.status_code == status.HTTP_200_OK
    assert "spreadsheetml" in xlsx_response.headers["content-type"]

    csv_response = client.get(
        "/reports/global/export",
        params={"format": "csv"},
        headers={**headers, "X-Reason": "Reporte global corporativo"},
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert b"Registros" in csv_response.content

    dataset = global_reports_data.build_dataset(
        db_session,
        date_from=None,
        date_to=None,
        module=None,
        severity=None,
    )
    assert dataset.overview.totals.logs >= 3
    assert dataset.dashboard.activity_series

    pdf_direct = global_reports_renderers.render_global_report_pdf(dataset.overview, dataset.dashboard)
    assert isinstance(pdf_direct, bytes) and len(pdf_direct) > 0

    xlsx_direct = global_reports_renderers.render_global_report_xlsx(dataset.overview, dataset.dashboard)
    assert len(xlsx_direct.getvalue()) > 0

    csv_direct = global_reports_renderers.render_global_report_csv(dataset.overview, dataset.dashboard)
    assert "Softmobile 2025" in csv_direct.getvalue()


def test_global_reports_respects_analytics_flag(client):
    original_flag = settings.enable_analytics_adv
    settings.enable_analytics_adv = False
    try:
        admin, credentials = _bootstrap_admin(client)
        token_data = _login(client, credentials["username"], credentials["password"])
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        overview_response = client.get("/reports/global/overview", headers=headers)
        assert overview_response.status_code == status.HTTP_404_NOT_FOUND
        assert overview_response.json()["detail"] == "Analítica avanzada no disponible"

        dashboard_response = client.get("/reports/global/dashboard", headers=headers)
        assert dashboard_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_analytics_adv = original_flag
