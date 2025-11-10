from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from backend.app.services import accounts_receivable
from backend.app.config import settings

from .test_customers import _bootstrap_admin


def test_accounts_receivable_reminder_dispatch(monkeypatch, client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Recordatorios automáticos"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-REM-01",
            "name": "Equipo Crédito",
            "quantity": 5,
            "unit_price": 500.0,
            "costo_unitario": 350.0,
        },
        headers=auth_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente Recordatorio",
            "phone": "+52 5550001111",
            "email": "recordatorio@example.com",
            "customer_type": "corporativo",
            "credit_limit": 2000.0,
        },
        headers=reason_headers,
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    sale_response = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "payment_method": "CREDITO",
            "items": [{"device_id": device_id, "quantity": 1}],
            "notes": "Venta con recordatorio",
        },
        headers={**auth_headers, "X-Reason": "Venta recordatorio"},
    )
    assert sale_response.status_code == 201

    # Marcar el cargo como antiguo para forzar vencimiento
    ledger_entry = db_session.execute(
        text(
            """
            SELECT id FROM customer_ledger_entries
            WHERE customer_id = :customer_id AND entry_type = 'SALE'
            ORDER BY created_at ASC LIMIT 1
            """
        ),
        {"customer_id": customer_id},
    ).scalar_one()
    db_session.execute(
        text(
            """
            UPDATE customer_ledger_entries
            SET created_at = :created_at
            WHERE id = :entry_id
            """
        ),
        {
            "created_at": datetime.utcnow() - timedelta(days=45),
            "entry_id": ledger_entry,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE clientes SET updated_at = :updated WHERE id_cliente = :cid
            """
        ),
        {"updated": datetime.utcnow() - timedelta(days=45), "cid": customer_id},
    )
    db_session.flush()

    sent_emails: list[dict] = []
    async_calls: list[dict] = []

    def fake_send_email_notification(**kwargs):
        sent_emails.append(kwargs)

    async def fake_send_whatsapp_message(**kwargs):
        async_calls.append(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(
        accounts_receivable.notifications,
        "send_email_notification",
        fake_send_email_notification,
    )
    monkeypatch.setattr(
        accounts_receivable.notifications,
        "send_whatsapp_message",
        fake_send_whatsapp_message,
    )

    try:
        results = accounts_receivable.send_upcoming_due_reminders(db_session)

        assert results
        reminder = results[0]
        assert reminder.customer_id == customer_id
        assert "email" in reminder.channels
        assert "whatsapp" in reminder.channels
        assert sent_emails and "recordatorio@example.com" in sent_emails[0]["recipients"]
        assert async_calls and async_calls[0]["to_number"] == "+52 5550001111"
    finally:
        settings.enable_purchases_sales = previous_flag
