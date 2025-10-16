"""Pruebas para filtros y exportación de la bitácora de auditoría."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import status

from backend.app.core.roles import ADMIN
from backend.app import models, telemetry


def _metric_value(name: str, labels: dict[str, str]) -> float:
    value = telemetry.get_metric_value(name, labels)
    return float(value) if value is not None else 0.0


def _bootstrap_admin(client):
    payload = {
        "username": "auditor_admin",
        "password": "Auditoria123*",
        "full_name": "Auditora Principal",
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


def test_audit_filters_and_csv_export(client):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    create_store = client.post("/stores", json=store_payload, headers=auth_headers)
    assert create_store.status_code == status.HTTP_201_CREATED

    filtered_logs = client.get(
        "/audit/logs",
        params={"performed_by_id": admin["id"]},
        headers=auth_headers,
    )
    assert filtered_logs.status_code == status.HTTP_200_OK
    logs = filtered_logs.json()
    assert logs
    assert all(log["performed_by_id"] == admin["id"] for log in logs)
    assert any(log["action"] == "store_created" for log in logs)

    future_from = (datetime.utcnow() + timedelta(days=1)).isoformat()
    empty_logs = client.get(
        "/audit/logs",
        params={"date_from": future_from},
        headers=auth_headers,
    )
    assert empty_logs.status_code == status.HTTP_200_OK
    assert empty_logs.json() == []

    export_headers = {**auth_headers, "X-Reason": "Revision auditoria"}
    export_response = client.get(
        "/audit/logs/export.csv",
        params={"performed_by_id": admin["id"], "action": "store_created"},
        headers=export_headers,
    )
    assert export_response.status_code == status.HTTP_200_OK
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "store_created" in export_response.text

    reports_response = client.get(
        "/reports/audit",
        params={"performed_by_id": admin["id"], "action": "store_created"},
        headers=auth_headers,
    )
    assert reports_response.status_code == status.HTTP_200_OK
    report_logs = reports_response.json()
    assert report_logs
    for log in report_logs:
        assert log["performed_by_id"] == admin["id"]
        assert log["action"] == "store_created"


def test_audit_acknowledgement_flow(client, db_session):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}", "X-Reason": "Control critico"}

    critical_log = models.AuditLog(
        action="sync_fail",
        entity_type="sync_session",
        entity_id="session-1",
        details="Sincronización fallida",
        performed_by_id=admin["id"],
    )
    db_session.add(critical_log)
    db_session.commit()

    miss_before = _metric_value(
        "softmobile_audit_reminder_cache_events_total", {"event": "miss"}
    )
    hit_before = _metric_value(
        "softmobile_audit_reminder_cache_events_total", {"event": "hit"}
    )
    invalidated_before = _metric_value(
        "softmobile_audit_reminder_cache_events_total", {"event": "invalidated"}
    )
    created_before = _metric_value(
        "softmobile_audit_acknowledgements_total",
        {"entity_type": "sync_session", "event": "created"},
    )
    failure_before = _metric_value(
        "softmobile_audit_acknowledgement_failures_total",
        {"entity_type": "sync_session", "reason": "already_acknowledged"},
    )

    reminders_response = client.get(
        "/audit/reminders", headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert reminders_response.status_code == status.HTTP_200_OK
    reminders_payload = reminders_response.json()
    assert reminders_payload["total"] >= 0
    assert (
        _metric_value("softmobile_audit_reminder_cache_events_total", {"event": "miss"})
        == miss_before + 1
    )

    ack_payload = {"entity_type": "sync_session", "entity_id": "session-1", "note": "Incidente revisado"}
    ack_response = client.post("/audit/acknowledgements", json=ack_payload, headers=auth_headers)
    assert ack_response.status_code == status.HTTP_201_CREATED
    ack_data = ack_response.json()
    assert ack_data["entity_type"] == "sync_session"
    assert ack_data["entity_id"] == "session-1"
    assert ack_data["acknowledged_by_id"] == admin["id"]
    assert (
        _metric_value(
            "softmobile_audit_acknowledgements_total",
            {"entity_type": "sync_session", "event": "created"},
        )
        == created_before + 1
    )
    assert (
        _metric_value(
            "softmobile_audit_reminder_cache_events_total", {"event": "invalidated"}
        )
        == invalidated_before + 1
    )

    updated_reminders = client.get("/audit/reminders", headers={"Authorization": f"Bearer {token_data['access_token']}"})
    assert updated_reminders.status_code == status.HTTP_200_OK
    summary = updated_reminders.json()
    assert summary["acknowledged_count"] >= 1
    assert any(entry["status"] == "acknowledged" for entry in summary["persistent"]) or summary["total"] == 0
    assert (
        _metric_value("softmobile_audit_reminder_cache_events_total", {"event": "miss"})
        == miss_before + 2
    )

    cached_reminders = client.get(
        "/audit/reminders", headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert cached_reminders.status_code == status.HTTP_200_OK
    assert (
        _metric_value("softmobile_audit_reminder_cache_events_total", {"event": "hit"})
        == hit_before + 1
    )

    pdf_response = client.get(
        "/reports/audit/pdf",
        params={"performed_by_id": admin["id"]},
        headers=auth_headers,
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    duplicate_ack = client.post(
        "/audit/acknowledgements", json=ack_payload, headers=auth_headers
    )
    assert duplicate_ack.status_code == status.HTTP_409_CONFLICT
    assert (
        _metric_value(
            "softmobile_audit_acknowledgement_failures_total",
            {"entity_type": "sync_session", "reason": "already_acknowledged"},
        )
        == failure_before + 1
    )


def test_prometheus_metrics_endpoint(client):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    response = client.get(
        "/monitoring/metrics",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "softmobile_audit_acknowledgements_total" in response.text
