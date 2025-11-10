import json
from decimal import Decimal
from typing import Any, Iterable

import pytest

from fastapi import status
from sqlalchemy import select

from backend.app import models

from backend.app.config import settings
from backend.app.core.roles import ADMIN, OPERADOR
from backend.app.services import notifications


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


def _bootstrap_admin(client):
    payload = {
        "username": "pos_admin",
        "password": "PosAdmin123*",
        "full_name": "POS Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return token


def _bootstrap_operator(client, admin_token: str | None = None) -> str:
    if admin_token is None:
        admin_token = _bootstrap_admin(client)

    payload = {
        "username": "pos_operator",
        "password": "PosOperador123*",
        "full_name": "Operador POS",
        "roles": [OPERADOR],
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_pos_config_requires_reason_header(client):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": ""}
    response = client.get("/pos/config", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    valid_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Consulta POS QA"}
    ok_response = client.get("/pos/config", headers=valid_headers)
    assert ok_response.status_code != status.HTTP_400_BAD_REQUEST


def test_pos_sale_with_receipt_and_config(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "POS-001",
        "name": "Smartphone POS",
        "quantity": 2,
        "unit_price": 100.0,
        "costo_unitario": 70.0,
        "margen_porcentaje": 10.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    draft_payload = {
        "store_id": store_id,
        "payment_method": "EFECTIVO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": False,
        "save_as_draft": True,
    }
    draft_response = client.post(
        "/pos/sale",
        json=draft_payload,
        headers={**auth_headers, "X-Reason": "Preparar venta POS"},
    )
    assert draft_response.status_code == 201
    draft_data = draft_response.json()
    assert draft_data["status"] == "draft"
    draft_id = draft_data["draft"]["id"]

    config_response = client.get(
        f"/pos/config?store_id={store_id}",
        headers={**auth_headers, "X-Reason": "Consultar POS"},
    )
    assert config_response.status_code == 200
    default_config = config_response.json()
    assert default_config["store_id"] == store_id
    assert default_config["hardware_settings"]["printers"] == []
    assert default_config["hardware_settings"]["cash_drawer"]["enabled"] is False
    assert default_config["default_document_type"] == "TICKET"
    catalog_types = {entry["type"] for entry in default_config["document_catalog"]}
    assert {"FACTURA", "TICKET", "NOTA_CREDITO", "NOTA_DEBITO"}.issubset(catalog_types)

    update_payload = {
        "store_id": store_id,
        "tax_rate": 16.0,
        "invoice_prefix": "POSCDMX",
        "printer_name": "TM-88V",
        "printer_profile": "USB",
        "quick_product_ids": [device_id],
        "default_document_type": "FACTURA",
        "hardware_settings": {
            "printers": [
                {
                    "name": "TM-88V",
                    "mode": "thermal",
                    "is_default": True,
                    "connector": {
                        "type": "usb",
                        "identifier": "TM-88V",
                    },
                    "paper_width_mm": 80,
                    "supports_qr": True,
                }
            ],
            "cash_drawer": {
                "enabled": True,
                "connector": {
                    "type": "usb",
                    "identifier": "Drawer-01",
                },
                "auto_open_on_cash_sale": True,
                "pulse_duration_ms": 200,
            },
            "customer_display": {
                "enabled": True,
                "channel": "websocket",
                "brightness": 85,
                "theme": "dark",
                "message_template": "Gracias por tu compra",
            },
        },
    }
    update_response = client.put(
        "/pos/config",
        json=update_payload,
        headers={**auth_headers, "X-Reason": "Configurar POS"},
    )
    assert update_response.status_code == 200
    updated_config = update_response.json()
    assert updated_config["tax_rate"] == 16.0
    assert updated_config["invoice_prefix"] == "POSCDMX"
    assert updated_config["hardware_settings"]["printers"][0]["name"] == "TM-88V"
    assert updated_config["hardware_settings"]["cash_drawer"]["enabled"] is True
    assert updated_config["default_document_type"] == "FACTURA"

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente POS",
            "email": "pos@example.com",
            "phone": "555-100-1000",
        },
        headers={**auth_headers, "X-Reason": "Alta cliente POS"},
    )
    assert customer_response.status_code == status.HTTP_201_CREATED
    customer_id = customer_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "payment_method": "TARJETA",
        "discount_percent": 5.0,
        "customer_id": customer_id,
        "items": [{"device_id": device_id, "quantity": 1, "discount_percent": 5.0}],
        "confirm": True,
        "draft_id": draft_id,
        "notes": "Venta mostrador",
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Finalizar venta POS"},
    )
    assert sale_response.status_code == 201
    sale_data = sale_response.json()
    assert sale_data["status"] == "registered"
    sale_info = sale_data["sale"]
    assert sale_info["payment_method"] == "TARJETA"
    assert sale_info["customer_id"] == customer_id
    assert sale_info["customer_name"] == "Cliente POS"
    assert sale_info["customer"]["id"] == customer_id
    assert sale_info["customer"]["name"] == "Cliente POS"
    assert sale_info["subtotal_amount"] == 95.0
    assert sale_info["tax_amount"] == 15.2
    assert sale_info["total_amount"] == 110.2
    assert any("Stock bajo" in message for message in sale_data["warnings"])
    assert sale_data["receipt_url"] == f"/pos/receipt/{sale_info['id']}"
    assert sale_data["document_type"] == "FACTURA"
    assert sale_data["document_number"].startswith("POSCDMX")
    assert sale_info["document_type"] == "FACTURA"
    assert sale_info["document_number"].startswith("POSCDMX")

    persisted_sale = db_session.execute(
        select(models.Sale).where(models.Sale.id == sale_info["id"])
    ).scalar_one()
    assert persisted_sale.customer_id == customer_id
    assert persisted_sale.customer is not None
    assert persisted_sale.customer.name == "Cliente POS"
    assert persisted_sale.document_type == models.POSDocumentType.FACTURA
    assert persisted_sale.document_number.startswith("POSCDMX")

    receipt_response = client.get(
        f"/pos/receipt/{sale_info['id']}",
        headers={**auth_headers, "X-Reason": "Descargar recibo POS"},
    )
    assert receipt_response.status_code == 200
    assert receipt_response.headers["content-type"].startswith("application/pdf")
    assert len(receipt_response.content) > 100

    devices_after = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after.status_code == 200
    remaining = next(
        item for item in _extract_items(devices_after.json()) if item["id"] == device_id
    )
    assert remaining["quantity"] == 1

    settings.enable_purchases_sales = False


def test_pos_receipt_delivery_records_audit(client, db_session, monkeypatch):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Notificaciones", "location": "TEG", "timezone": "America/Tegucigalpa"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "NOTIF-001",
            "name": "Impresora POS",
            "quantity": 1,
            "unit_price": 50.0,
            "costo_unitario": 30.0,
        },
        headers={**auth_headers, "X-Reason": "Alta dispositivo"},
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "payment_method": "EFECTIVO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": True,
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Registrar venta"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_id = sale_response.json()["sale"]["id"]

    email_called: dict[str, Any] = {}
    whatsapp_called: dict[str, Any] = {}

    def fake_email_notification(**kwargs):
        email_called.update(kwargs)

    async def fake_whatsapp_notification(**kwargs):
        whatsapp_called.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(notifications, "send_email_notification", fake_email_notification)
    monkeypatch.setattr(notifications, "send_whatsapp_message", fake_whatsapp_notification)

    send_headers = {**auth_headers, "X-Reason": "Enviar recibo"}
    email_response = client.post(
        f"/pos/receipt/{sale_id}/send",
        json={"channel": "email", "recipient": "cliente@test.com", "message": "Gracias"},
        headers=send_headers,
    )
    assert email_response.status_code == status.HTTP_202_ACCEPTED
    assert email_called["recipients"] == ["cliente@test.com"]

    log_entry = db_session.execute(
        select(models.AuditLog)
        .where(models.AuditLog.entity_type == "sale")
        .order_by(models.AuditLog.created_at.desc())
    ).scalar_one()
    assert json.loads(log_entry.details)["canal"] == "email"

    whatsapp_response = client.post(
        f"/pos/receipt/{sale_id}/send",
        json={"channel": "whatsapp", "recipient": "+50499998888"},
        headers=send_headers,
    )
    assert whatsapp_response.status_code == status.HTTP_202_ACCEPTED
    assert whatsapp_called["to_number"] == "+50499998888"

    latest_log = db_session.execute(
        select(models.AuditLog)
        .where(models.AuditLog.action == "pos_receipt_sent")
        .order_by(models.AuditLog.created_at.desc())
    ).scalars().first()
    assert latest_log is not None
    details = json.loads(latest_log.details)
    assert details["canal"] == "whatsapp"
    assert details["destinatario"] == "+50499998888"

    settings.enable_purchases_sales = False


def test_pos_cash_sessions_and_credit_sales(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Operacion POS"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Sur", "location": "MTY", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "POS-CR-001",
            "name": "Laptop Servicio",
            "quantity": 3,
            "unit_price": 200.0,
            "costo_unitario": 120.0,
        },
        headers=reason_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente Crédito",
            "email": "credito@example.com",
            "phone": "555-500-5000",
            "credit_limit": 500.0,
        },
        headers=reason_headers,
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    open_response = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 500.0, "notes": "Apertura"},
        headers=reason_headers,
    )
    assert open_response.status_code == 201
    session_id = open_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "CREDITO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": True,
        "cash_session_id": session_id,
        "payment_breakdown": {"CREDITO": 200.0},
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers=reason_headers,
    )
    assert sale_response.status_code == 201
    sale_data = sale_response.json()
    assert sale_data["sale"]["customer_id"] == customer_id
    assert sale_data["cash_session_id"] == session_id
    assert sale_data["payment_breakdown"]["CREDITO"] == 200.0
    assert sale_data["debt_summary"]["remaining_balance"] == pytest.approx(200.0)
    assert sale_data["credit_schedule"]
    assert sale_data["debt_receipt_pdf_base64"]
    assert sale_data["payment_receipts"] == []

    customer_details = client.get(
        f"/customers/{customer_id}", headers=auth_headers
    )
    assert customer_details.status_code == 200
    assert customer_details.json()["outstanding_debt"] == 200.0

    close_response = client.post(
        "/pos/cash/close",
        json={
            "session_id": session_id,
            "closing_amount": 500.0,
            "payment_breakdown": {"CREDITO": 200.0},
            "notes": "Cierre turno",
        },
        headers=reason_headers,
    )
    assert close_response.status_code == 200
    session_data = close_response.json()
    assert session_data["status"] == "CERRADO"
    assert session_data["difference_amount"] == 0.0
    assert session_data["payment_breakdown"]["CREDITO"] == 200.0

    history_response = client.get(
        f"/pos/cash/history?store_id={store_id}",
        headers={**auth_headers, "X-Reason": "Consultar historia"},
    )
    assert history_response.status_code == 200
    history_items = _extract_items(history_response.json())
    assert any(item["id"] == session_id for item in history_items)

    settings.enable_purchases_sales = False


def test_pos_credit_note_emission(client, db_session):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={
                "name": "POS Fiscal",
                "location": "San Pedro Sula",
                "timezone": "America/Tegucigalpa",
            },
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        config_payload = {
            "store_id": store_id,
            "tax_rate": 15.0,
            "invoice_prefix": "POSNC",
            "printer_name": "Fiscal Printer",
            "printer_profile": "USB",
            "quick_product_ids": [],
            "hardware_settings": {
                "printers": [
                    {
                        "name": "Fiscal Printer",
                        "mode": "thermal",
                        "is_default": True,
                        "connector": {"type": "usb", "identifier": "Fiscal-01"},
                        "paper_width_mm": 80,
                        "supports_qr": True,
                    }
                ],
                "cash_drawer": {
                    "enabled": True,
                    "connector": {"type": "usb", "identifier": "DrawerFiscal"},
                    "auto_open_on_cash_sale": True,
                    "pulse_duration_ms": 200,
                },
                "customer_display": {
                    "enabled": False,
                    "channel": "websocket",
                    "brightness": 60,
                    "theme": "dark",
                },
            },
            "document_catalog": [
                {
                    "type": "FACTURA",
                    "label": "Factura POS",
                    "prefix": "POSNCF",
                    "requires_customer": True,
                },
                {
                    "type": "TICKET",
                    "label": "Ticket POS",
                    "prefix": "POSNCTK",
                    "requires_customer": False,
                },
                {
                    "type": "NOTA_CREDITO",
                    "label": "Nota de crédito POS",
                    "prefix": "POSNCNC",
                    "requires_customer": True,
                },
                {
                    "type": "NOTA_DEBITO",
                    "label": "Nota de débito POS",
                    "prefix": "POSNCND",
                    "requires_customer": True,
                },
            ],
            "default_document_type": "FACTURA",
        }
        config_response = client.put(
            "/pos/config",
            json=config_payload,
            headers={**auth_headers, "X-Reason": "Configurar comprobantes POS"},
        )
        assert config_response.status_code == status.HTTP_200_OK

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "POS-NC-001",
                "name": "Terminal Fiscal",
                "quantity": 2,
                "unit_price": 100.0,
                "costo_unitario": 60.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={
                "name": "Cliente Fiscal",
                "email": "fiscal@example.com",
                "phone": "504-1234-5678",
                "tax_id": "08011985123960",
            },
            headers={**auth_headers, "X-Reason": "Alta cliente fiscal"},
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        sale_payload = {
            "store_id": store_id,
            "customer_id": customer_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
            "confirm": True,
            "notes": "Venta fiscalizada",
        }
        sale_response = client.post(
            "/pos/sale",
            json=sale_payload,
            headers={**auth_headers, "X-Reason": "Registrar venta fiscal"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_data = sale_response.json()
        assert sale_data["document_type"] == "FACTURA"
        sale_id = sale_data["sale"]["id"]

        note_payload = {
            "document_type": "NOTA_CREDITO",
            "amount": 25.0,
            "reason": "Devolución parcial"
        }
        note_response = client.post(
            f"/pos/documents/{sale_id}/notes",
            json=note_payload,
            headers={**auth_headers, "X-Reason": "Emitir nota fiscal"},
        )
        assert note_response.status_code == status.HTTP_201_CREATED
        note_data = note_response.json()
        assert note_data["document_type"] == "NOTA_CREDITO"
        assert note_data["reference_document_number"] == sale_data["document_number"]
        assert note_data["amount"] == pytest.approx(25.0)

        document_record = db_session.execute(
            select(models.FiscalDocument).where(models.FiscalDocument.id == note_data["id"])
        ).scalar_one()
        assert document_record.reference is not None
        assert document_record.reference.document_number == sale_data["document_number"]
        assert document_record.amount == Decimal("25.00")
        assert document_record.reason == "Devolución parcial"
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_credit_note_requires_invoice_document(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={
                "name": "POS Tickets",
                "location": "La Ceiba",
                "timezone": "America/Tegucigalpa",
            },
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "POS-TK-001",
                "name": "Lector Básico",
                "quantity": 1,
                "unit_price": 80.0,
                "costo_unitario": 40.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={
                "name": "Cliente Ticket",
                "email": "ticket@example.com",
                "phone": "504-5555-0000",
            },
            headers={**auth_headers, "X-Reason": "Alta cliente POS"},
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        sale_response = client.post(
            "/pos/sale",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
                "confirm": True,
                "notes": "Venta con ticket",
            },
            headers={**auth_headers, "X-Reason": "Registrar venta POS"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["sale"]["id"]
        assert sale_response.json()["document_type"] == "TICKET"

        note_response = client.post(
            f"/pos/documents/{sale_id}/notes",
            json={
                "document_type": "NOTA_CREDITO",
                "amount": 10.0,
                "reason": "Reverso parcial",
            },
            headers={**auth_headers, "X-Reason": "Intentar nota"},
        )
        assert note_response.status_code == status.HTTP_409_CONFLICT
        assert "factura" in note_response.json()["detail"].lower()
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_electronic_payment_with_tip_and_terminal(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Pago electrónico POS"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Atlántida", "location": "TGU", "timezone": "America/Tegucigalpa"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "ATL-001",
            "name": "Teléfono Premium",
            "quantity": 2,
            "unit_price": 250.0,
            "costo_unitario": 140.0,
        },
        headers=reason_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    open_response = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 300.0, "notes": "Turno mañana"},
        headers=reason_headers,
    )
    assert open_response.status_code == 201
    session_id = open_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "payment_method": "TARJETA",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": True,
        "cash_session_id": session_id,
        "payments": [
            {
                "method": "TARJETA",
                "amount": 250.0,
                "terminalId": "atl-01",
                "tipAmount": 15.0,
                "reference": "1234",
            }
        ],
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers=reason_headers,
    )
    assert sale_response.status_code == 201, sale_response.text
    sale_data = sale_response.json()
    assert sale_data["status"] == "registered"
    assert sale_data["payment_breakdown"]["TARJETA"] == 265.0
    electronic = sale_data.get("electronic_payments", [])
    assert electronic and electronic[0]["terminal_id"] == "atl-01"
    assert electronic[0]["status"]

    session_model = db_session.get(models.CashRegisterSession, session_id)
    assert session_model is not None
    breakdown = session_model.payment_breakdown or {}
    assert breakdown.get("cobrado_TARJETA") == 265.0
    assert breakdown.get("propina_TARJETA") == 15.0

    settings.enable_purchases_sales = False


def test_pos_requires_auth_reason_and_roles(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        sale_payload = {
            "store_id": 1,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": 1, "quantity": 1}],
            "confirm": True,
        }

        unauth_response = client.post("/pos/sale", json=sale_payload)
        assert unauth_response.status_code == status.HTTP_400_BAD_REQUEST

        admin_token = _bootstrap_admin(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        store_response = client.post(
            "/stores",
            json={"name": "POS Validaciones", "location": "MX", "timezone": "America/Mexico_City"},
            headers=admin_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "POS-VALIDA-001",
                "name": "Impresora POS",
                "quantity": 5,
                "unit_price": 50.0,
                "costo_unitario": 25.0,
            },
            headers=admin_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
            "confirm": True,
        }

        missing_reason_response = client.post(
            "/pos/sale",
            json=payload,
            headers=admin_headers,
        )
        assert missing_reason_response.status_code == status.HTTP_400_BAD_REQUEST

        operator_token = _bootstrap_operator(client, admin_token)
        operator_headers = {
            "Authorization": f"Bearer {operator_token}",
            "X-Reason": "Intento POS",
        }

        forbidden_response = client.post(
            "/pos/sale",
            json=payload,
            headers=operator_headers,
        )
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

        valid_headers = {**admin_headers, "X-Reason": "Venta Validada"}
        success_response = client.post(
            "/pos/sale",
            json=payload,
            headers=valid_headers,
        )
        assert success_response.status_code == status.HTTP_201_CREATED
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_sale_rejects_unknown_store(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        headers = {"Authorization": f"Bearer {token}", "X-Reason": "Validar sucursal"}
        payload = {
            "store_id": 9999,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": 1, "quantity": 1}],
            "confirm": True,
        }

        response = client.post("/pos/sale", json=payload, headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Sucursal no encontrada."
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_config_requires_reason_and_audit(client, db_session):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "POS Auditoria", "location": "GDL", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        missing_reason_response = client.get(
            f"/pos/config?store_id={store_id}",
            headers=auth_headers,
        )
        assert missing_reason_response.status_code == status.HTTP_400_BAD_REQUEST

        valid_headers = {**auth_headers, "X-Reason": "Auditar POS"}
        ok_response = client.get(
            f"/pos/config?store_id={store_id}",
            headers=valid_headers,
        )
        assert ok_response.status_code == status.HTTP_200_OK

        audit_query = (
            select(models.AuditLog)
            .where(
                models.AuditLog.action == "pos_config_viewed",
                models.AuditLog.entity_type == "store",
                models.AuditLog.entity_id == str(store_id),
            )
            .order_by(models.AuditLog.created_at.desc())
        )
        audit_entry = db_session.execute(audit_query).scalars().first()
        assert audit_entry is not None
        assert audit_entry.details is not None
        details = json.loads(audit_entry.details)
        assert details["store_id"] == store_id
        assert details["reason"] == "Auditar POS"
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_hardware_channels_and_drawer(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Prueba hardware POS"}

        store_response = client.post(
            "/stores",
            json={"name": "Hardware POS", "location": "MTY", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        config_payload = {
            "store_id": store_id,
            "tax_rate": 16.0,
            "invoice_prefix": "POSHW",
            "printer_name": "TM-HW",
            "printer_profile": "USB",
            "quick_product_ids": [],
            "hardware_settings": {
                "printers": [
                    {
                        "name": "TM-HW",
                        "mode": "thermal",
                        "is_default": True,
                        "connector": {
                            "type": "usb",
                            "identifier": "TM-HW",
                        },
                    }
                ],
                "cash_drawer": {
                    "enabled": True,
                    "connector": {
                        "type": "usb",
                        "identifier": "Drawer-HW",
                    },
                    "auto_open_on_cash_sale": True,
                    "pulse_duration_ms": 180,
                },
                "customer_display": {
                    "enabled": True,
                    "channel": "websocket",
                    "brightness": 90,
                    "theme": "dark",
                },
            },
        }
        config_response = client.put(
            "/pos/config",
            json=config_payload,
            headers=reason_headers,
        )
        assert config_response.status_code == status.HTTP_200_OK

        with client.websocket_connect(f"/pos/hardware/ws?storeId={store_id}") as websocket:
            ready_message = websocket.receive_json()
            assert ready_message["event"] == "hardware.ready"

            print_response = client.post(
                "/pos/hardware/print-test",
                json={
                    "store_id": store_id,
                    "printer_name": "TM-HW",
                    "mode": "thermal",
                },
                headers=reason_headers,
            )
            assert print_response.status_code == status.HTTP_200_OK
            assert print_response.json()["status"] == "ok"

            drawer_response = client.post(
                "/pos/hardware/drawer/open",
                json={"store_id": store_id},
                headers=reason_headers,
            )
            assert drawer_response.status_code == status.HTTP_200_OK
            drawer_event = websocket.receive_json()
            assert drawer_event["event"] == "cash_drawer.open"
            assert drawer_event["store_id"] == store_id

            display_response = client.post(
                "/pos/hardware/display/push",
                json={
                    "store_id": store_id,
                    "headline": "Gracias",
                    "message": "Total a pagar",
                    "total_amount": 199.99,
                },
                headers=reason_headers,
            )
            assert display_response.status_code == status.HTTP_200_OK
            display_event = websocket.receive_json()
            assert display_event["event"] == "customer_display.message"
            assert display_event["headline"] == "Gracias"
    finally:
        settings.enable_purchases_sales = original_flag


def test_pos_cash_history_requires_reason(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "POS Historial", "location": "MX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        missing_reason_response = client.get(
            f"/pos/cash/history?store_id={store_id}",
            headers=auth_headers,
        )
        assert missing_reason_response.status_code == status.HTTP_400_BAD_REQUEST

        valid_headers = {**auth_headers, "X-Reason": "Revisar historial"}
        ok_response = client.get(
            f"/pos/cash/history?store_id={store_id}",
            headers=valid_headers,
        )
        assert ok_response.status_code == status.HTTP_200_OK
    finally:
        settings.enable_purchases_sales = original_flag

def test_pos_sale_with_store_credit_breakdown(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_payload = {
        "name": "POS Notas",
        "location": "Guadalajara",
        "timezone": "America/Mexico_City",
    }
    store_response = client.post("/stores", json=store_payload, headers=auth_headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "NC-001",
        "name": "Dispositivo con nota",
        "quantity": 3,
        "unit_price": 120.0,
        "costo_unitario": 80.0,
        "margen_porcentaje": 15.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    customer_payload = {
        "name": "Cliente Nota POS",
        "phone": "+52 55 1111 5555",
        "customer_type": "minorista",
        "status": "activo",
        "credit_limit": 0.0,
        "history": [],
    }
    customer_response = client.post(
        "/customers",
        json=customer_payload,
        headers={**auth_headers, "X-Reason": "Alta cliente POS"},
    )
    assert customer_response.status_code == status.HTTP_201_CREATED
    customer_id = customer_response.json()["id"]

    issue_payload = {
        "customer_id": customer_id,
        "amount": 120.0,
        "notes": "Reposición venta anterior",
    }
    credit_response = client.post(
        "/store-credits",
        json=issue_payload,
        headers={**auth_headers, "X-Reason": "Emisión nota"},
    )
    assert credit_response.status_code == status.HTTP_201_CREATED
    credit_id = credit_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "NOTA_CREDITO",
        "items": [
            {"device_id": device_id, "quantity": 1},
        ],
        "confirm": True,
        "save_as_draft": False,
        "apply_taxes": False,
        "payment_breakdown": {"NOTA_CREDITO": 120.0},
        "notes": "Venta cubierta con nota",
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta con nota"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    assert sale_data["status"] == "registered"
    assert any("nota de crédito" in warning.lower() for warning in sale_data.get("warnings", []))

    credits_after = client.get(
        f"/store-credits/by-customer/{customer_id}",
        headers={**auth_headers, "X-Reason": "Verificar saldo nota"},
    )
    assert credits_after.status_code == status.HTTP_200_OK
    credit_items = credits_after.json()
    assert credit_items[0]["id"] == credit_id
    assert credit_items[0]["balance_amount"] == 0.0
    assert credit_items[0]["status"] == "REDIMIDO"
    assert len(credit_items[0]["redemptions"]) >= 1
