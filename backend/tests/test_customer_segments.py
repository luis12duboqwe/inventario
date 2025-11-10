from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.services import customer_segments


def _create_store(session) -> models.Store:
    store = models.Store(
        name="Segmentos Centro",
        code="SEG-001",
        timezone="UTC",
        inventory_value=Decimal("0"),
    )
    session.add(store)
    session.flush()
    return store


def _create_customer(session, name: str, *, phone: str = "555-000-0000") -> models.Customer:
    customer = models.Customer(
        name=name,
        phone=phone,
        customer_type="corporativo",
        status="activo",
        credit_limit=Decimal("0"),
        outstanding_debt=Decimal("0"),
        history=[],
    )
    session.add(customer)
    session.flush()
    return customer


def _bootstrap_admin(client) -> str:
    payload = {
        "username": "segment_admin",
        "password": "Segmentos123*",
        "full_name": "Segment Admin",
        "roles": ["admin"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == 200
    return token_response.json()["access_token"]


def test_refresh_customer_segments_creates_snapshots(tmp_path: Path, db_session):
    previous_directory = settings.customer_segments_export_directory
    previous_mailchimp_url = settings.mailchimp_api_url
    previous_mailchimp_key = settings.mailchimp_api_key
    previous_sms_url = settings.sms_campaign_api_url
    previous_sms_token = settings.sms_campaign_api_token
    try:
        settings.customer_segments_export_directory = str(tmp_path)
        settings.mailchimp_api_url = None
        settings.mailchimp_api_key = None
        settings.sms_campaign_api_url = None
        settings.sms_campaign_api_token = None

        store = _create_store(db_session)
        vip_customer = _create_customer(db_session, "Cliente VIP")
        basic_customer = _create_customer(db_session, "Cliente Básico", phone="555-111-2222")

        now = datetime(2025, 2, 1, 12, 0, tzinfo=timezone.utc)
        for days_offset in (15, 60, 120, 200):
            sale = models.Sale(
                store_id=store.id,
                customer_id=vip_customer.id,
                payment_method=models.PaymentMethod.EFECTIVO,
                subtotal_amount=Decimal("2500"),
                tax_amount=Decimal("400"),
                total_amount=Decimal("2900"),
                status="COMPLETADA",
                created_at=now - timedelta(days=days_offset),
            )
            db_session.add(sale)

        db_session.flush()

        result = customer_segments.refresh_customer_segments(
            db_session,
            now=now,
            export_directory=str(tmp_path),
        )

        vip_snapshot = db_session.scalar(
            select(models.CustomerSegmentSnapshot).where(
                models.CustomerSegmentSnapshot.customer_id == vip_customer.id
            )
        )
        assert vip_snapshot is not None
        assert vip_snapshot.orders_last_year == 4
        assert "alto_valor" in vip_snapshot.segment_labels
        assert vip_snapshot.frequency_label == "recurrente"

        basic_snapshot = db_session.scalar(
            select(models.CustomerSegmentSnapshot).where(
                models.CustomerSegmentSnapshot.customer_id == basic_customer.id
            )
        )
        assert basic_snapshot is not None
        assert "valor_bajo" in basic_snapshot.segment_labels
        assert "sin_compras" in basic_snapshot.segment_labels
        assert "recuperacion" in basic_snapshot.segment_labels

        exported_files = list(tmp_path.glob("*.csv"))
        assert exported_files, "Se esperaba al menos un archivo de exportación"
        assert result.updated_customers == 2
        assert result.segments["alto_valor"], "Debe existir al menos un cliente alto valor"
    finally:
        settings.customer_segments_export_directory = previous_directory
        settings.mailchimp_api_url = previous_mailchimp_url
        settings.mailchimp_api_key = previous_mailchimp_key
        settings.sms_campaign_api_url = previous_sms_url
        settings.sms_campaign_api_token = previous_sms_token


@pytest.mark.parametrize("segment,expected_status", [("alto_valor", 200), ("desconocido", 422)])
def test_export_customer_segment_endpoint(client, db_session, tmp_path: Path, segment: str, expected_status: int):
    previous_directory = settings.customer_segments_export_directory
    settings.customer_segments_export_directory = str(tmp_path)
    try:
        store = _create_store(db_session)
        customer = _create_customer(db_session, "Cliente Segmentado")
        now = datetime(2025, 2, 1, 9, 0, tzinfo=timezone.utc)
        sale = models.Sale(
            store_id=store.id,
            customer_id=customer.id,
            payment_method=models.PaymentMethod.EFECTIVO,
            subtotal_amount=Decimal("9000"),
            tax_amount=Decimal("1500"),
            total_amount=Decimal("10500"),
            status="COMPLETADA",
            created_at=now - timedelta(days=10),
        )
        db_session.add(sale)
        db_session.flush()

        customer_segments.refresh_customer_segments(db_session, now=now, trigger_marketing=False)

        token = _bootstrap_admin(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reason": "Export segmentos QA",
        }
        response = client.get(
            "/customers/segments/export",
            params={"segment": segment},
            headers=headers,
        )
        assert response.status_code == expected_status
        if response.status_code == 200:
            assert "segmento_alto_valor" in response.headers.get("Content-Disposition", "")
            assert "Cliente Segmentado" in response.text
    finally:
        settings.customer_segments_export_directory = previous_directory
