from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from backend.app import crud, models
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "observ_admin",
        "password": "Observa123*",
        "full_name": "Supervisora Observabilidad",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_observability_snapshot_consolidates_metrics(client, db_session):
    token = _bootstrap_admin(client)
    now = datetime.utcnow()

    store = models.Store(name="Central Observabilidad", code="OBS-001", timezone="UTC")
    db_session.add(store)
    db_session.flush()

    crud._log_action(
        db_session,
        action="inventory_warning",
        entity_type="inventory",
        entity_id="demo",
        performed_by_id=None,
        details="Stock en riesgo en sucursal",
    )
    crud.register_system_error(
        db_session,
        mensaje="Error al sincronizar con la nube",
        stack_trace="Timeout",
        modulo="sync",
        usuario="observ_admin",
    )

    failure_entry = models.SyncOutbox(
        entity_type="sale",
        entity_id="sale-99",
        operation="create",
        payload="{}",
        status=models.SyncOutboxStatus.FAILED,
        priority=models.SyncOutboxPriority.HIGH,
        attempt_count=4,
        error_message="timeout",
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(minutes=15),
    )
    pending_entry = models.SyncOutbox(
        entity_type="inventory",
        entity_id="inv-77",
        operation="update",
        payload="{}",
        status=models.SyncOutboxStatus.PENDING,
        priority=models.SyncOutboxPriority.NORMAL,
        created_at=now - timedelta(hours=1, minutes=20),
        updated_at=now - timedelta(minutes=10),
    )

    sale = models.Sale(
        store=store,
        payment_method=models.PaymentMethod.EFECTIVO,
        subtotal_amount=Decimal("120"),
        tax_amount=Decimal("18"),
        total_amount=Decimal("138"),
    )

    queue_entries = []
    documents: list[models.DTEDocument] = []
    for index in range(3):
        document = models.DTEDocument(
            sale=sale,
            document_type="FACTURA",
            serie="OBS",
            correlative=index + 1,
            control_number=f"OBS-{index + 1:04d}",
            cai=f"CAI-OBS-{index + 1:04d}",
            xml_content="<xml>demo</xml>",
            signature="signed",
            status=models.DTEStatus.RECHAZADO,
        )
        queue_entry = models.DTEDispatchQueue(
            document=document,
            status=models.DTEDispatchStatus.FAILED,
            attempts=3 + index,
            last_error="Servicio DTE no disponible",
        )
        documents.append(document)
        queue_entries.append(queue_entry)

    db_session.add_all([sale, failure_entry, pending_entry, *documents, *queue_entries])
    db_session.commit()

    response = client.get(
        "/admin/observability",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    payload = response.json()

    assert payload["errors"]["total_errors"] >= 1
    assert payload["sync"]["total_failed"] >= 3

    latency_entities = {sample["entity_type"] for sample in payload["latency"]["samples"]}
    assert "inventory" in latency_entities

    notification_ids = {item["id"] for item in payload["notifications"]}
    assert "sync-outbox-sale" in notification_ids
    assert "dte-dispatch-failures" in notification_ids

    assert payload["logs"], "Se esperaban logs recientes en el snapshot"
