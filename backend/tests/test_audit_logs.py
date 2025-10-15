"""Pruebas para filtros y exportación de la bitácora de auditoría."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from io import StringIO

from fastapi import status

from backend.app import models
from backend.app.core.roles import ADMIN


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
    assert {log["severity"] for log in logs} <= {"info", "warning", "critical"}

    future_from = (datetime.utcnow() + timedelta(days=1)).isoformat()
    empty_logs = client.get(
        "/audit/logs",
        params={"date_from": future_from},
        headers=auth_headers,
    )
    assert empty_logs.status_code == status.HTTP_200_OK
    assert empty_logs.json() == []

    export_response = client.get(
        "/audit/logs/export.csv",
        params={"performed_by_id": admin["id"], "action": "store_created"},
        headers=auth_headers,
    )
    assert export_response.status_code == status.HTTP_200_OK
    assert export_response.headers["content-type"].startswith("text/csv")
    csv_rows = list(csv.reader(StringIO(export_response.text)))
    assert csv_rows
    header = csv_rows[0]
    assert header[-3:] == ["Estado alerta", "Acuse registrado", "Nota de acuse"]
    assert any("store_created" in row for row in csv_rows[1:])
    assert any(row[header.index("Estado alerta")] in {"Pendiente", "Atendida"} for row in csv_rows[1:])

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
        assert log["severity_label"] in {"Informativa", "Preventiva", "Crítica"}

    pdf_response = client.get(
        "/reports/audit/pdf",
        params={"performed_by_id": admin["id"], "action": "store_created", "limit": 50},
        headers=auth_headers,
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert len(pdf_response.content) > 1000


def test_audit_persistent_reminders(client, db_session):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    base_time = datetime.utcnow() - timedelta(minutes=45)
    repeated_action = "login_fail_attempt"

    first_log = models.AuditLog(
        action=repeated_action,
        entity_type="auth",
        entity_id="login",
        details="fail: contraseña incorrecta",
        performed_by_id=admin["id"],
        created_at=base_time,
    )
    second_log = models.AuditLog(
        action=repeated_action,
        entity_type="auth",
        entity_id="login",
        details="fail: bloqueo automático",
        performed_by_id=admin["id"],
        created_at=base_time + timedelta(minutes=10),
    )
    db_session.add_all([first_log, second_log])
    db_session.flush()

    reminders_response = client.get(
        "/audit/reminders",
        params={"threshold_minutes": 15, "lookback_hours": 24, "min_occurrences": 1},
        headers=auth_headers,
    )
    assert reminders_response.status_code == status.HTTP_200_OK
    data = reminders_response.json()
    assert data["threshold_minutes"] == 15
    assert data["min_occurrences"] == 1
    assert data["total"] >= 1
    assert data["persistent"]
    assert data["pending"] >= 1
    reminder = data["persistent"][0]
    assert reminder["entity_type"] == "auth"
    assert reminder["entity_id"] == "login"
    assert reminder["occurrences"] >= 1
    assert reminder["latest_action"] == repeated_action
    assert reminder["status"] == "pending"
    assert reminder["acknowledged_at"] is None

    ack_headers = {**auth_headers, "X-Reason": "Mitigacion critica manual"}
    ack_payload = {
        "entity_type": "auth",
        "entity_id": "login",
        "note": "Acceso bloqueado y usuario informado",
    }
    ack_response = client.post("/audit/acknowledgements", json=ack_payload, headers=ack_headers)
    assert ack_response.status_code == status.HTTP_201_CREATED
    ack_data = ack_response.json()
    assert ack_data["entity_type"] == "auth"
    assert ack_data["entity_id"] == "login"
    assert ack_data["note"] == ack_payload["note"]
    assert ack_data["acknowledged_by_id"] == admin["id"]

    reminders_response = client.get(
        "/audit/reminders",
        params={"threshold_minutes": 15, "lookback_hours": 24, "min_occurrences": 1},
        headers=auth_headers,
    )
    assert reminders_response.status_code == status.HTTP_200_OK
    data = reminders_response.json()
    assert data["threshold_minutes"] == 15
    assert data["min_occurrences"] == 1
    assert data["total"] >= 1
    assert data["persistent"]
    assert data["acknowledged_total"] >= 1
    reminder_after = data["persistent"][0]
    assert reminder_after["entity_type"] == "auth"
    assert reminder_after["entity_id"] == "login"
    assert reminder_after["status"] == "acknowledged"
    assert reminder_after["acknowledged_by_id"] == admin["id"]
    assert reminder_after["acknowledged_note"] == ack_payload["note"]

    metrics_response = client.get("/reports/metrics", headers=auth_headers)
    assert metrics_response.status_code == status.HTTP_200_OK
    metrics = metrics_response.json()
    audit_alerts = metrics["audit_alerts"]
    assert audit_alerts["acknowledged_critical"] >= 1
    assert audit_alerts["pending_critical"] >= 0
    assert all("entity_id" in highlight for highlight in audit_alerts["highlights"])
    assert any(entry["entity_id"] == "login" for entry in audit_alerts["acknowledged"])


def test_audit_acknowledgements_conflict_and_exports(client, db_session):
    admin, credentials = _bootstrap_admin(client)
    token_data = _login(client, credentials["username"], credentials["password"])

    auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    ack_headers = {**auth_headers, "X-Reason": "Mitigacion critica manual"}

    base_time = datetime.utcnow() - timedelta(minutes=90)
    critical_logs = [
        models.AuditLog(
            action="login_fail_attempt",
            entity_type="auth",
            entity_id="login",
            details="fail: contraseña incorrecta",
            performed_by_id=admin["id"],
            created_at=base_time,
        ),
        models.AuditLog(
            action="login_fail_attempt",
            entity_type="auth",
            entity_id="login",
            details="fail: bloqueo automático",
            performed_by_id=admin["id"],
            created_at=base_time + timedelta(minutes=5),
        ),
    ]
    other_logs = [
        models.AuditLog(
            action="sync_outbox_retry_fail",
            entity_type="sync",
            entity_id="outbox",
            details="fail: reintentos agotados",
            performed_by_id=admin["id"],
            created_at=base_time + timedelta(minutes=10),
        ),
        models.AuditLog(
            action="session_refresh",
            entity_type="auth",
            entity_id="token",
            details="refresh correcto",
            performed_by_id=admin["id"],
            created_at=base_time + timedelta(minutes=15),
        ),
    ]
    db_session.add_all([*critical_logs, *other_logs])
    db_session.commit()

    pdf_before = client.get(
        "/reports/audit/pdf",
        params={"entity_type": "auth", "limit": 50},
        headers=auth_headers,
    )
    assert pdf_before.status_code == status.HTTP_200_OK
    pdf_content_before = pdf_before.content

    ack_payload = {
        "entity_type": "auth",
        "entity_id": "login",
        "note": "Contraseña restablecida y sesión cerrada",
    }

    ack_response = client.post("/audit/acknowledgements", json=ack_payload, headers=ack_headers)
    assert ack_response.status_code == status.HTTP_201_CREATED

    duplicate_response = client.post("/audit/acknowledgements", json=ack_payload, headers=ack_headers)
    assert duplicate_response.status_code == status.HTTP_409_CONFLICT
    assert "ya fue atendida" in duplicate_response.json()["detail"]

    missing_payload = {
        "entity_type": "auth",
        "entity_id": "token",
        "note": "Intento de acuse sin alerta crítica",
    }
    missing_response = client.post("/audit/acknowledgements", json=missing_payload, headers=ack_headers)
    assert missing_response.status_code == status.HTTP_404_NOT_FOUND
    assert "No existen alertas críticas" in missing_response.json()["detail"]

    export_response = client.get(
        "/audit/logs/export.csv",
        params={"entity_type": "auth"},
        headers=auth_headers,
    )
    assert export_response.status_code == status.HTTP_200_OK
    rows = list(csv.reader(StringIO(export_response.text)))
    assert rows and len(rows) >= 2
    header = rows[0]
    status_index = header.index("Estado alerta")
    note_index = header.index("Nota de acuse")
    statuses = {row[status_index] for row in rows[1:]}
    assert "Atendida" in statuses
    assert any(row[note_index] == ack_payload["note"] for row in rows[1:])

    pdf_response = client.get(
        "/reports/audit/pdf",
        params={"entity_type": "auth", "limit": 50},
        headers=auth_headers,
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.content != pdf_content_before
    assert len(pdf_response.content) >= len(pdf_content_before)
