from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fiscal_books_expected.json"


def _bootstrap_admin(client) -> str:
    payload = {
        "username": "fiscal_admin",
        "password": "Fiscal123*",
        "full_name": "Fiscal Admin",
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


def _load_expected_totals() -> dict[str, object]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handler:
        return json.load(handler)


@pytest.mark.usefixtures("client")
def test_fiscal_books_match_fixture(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Fiscal", "location": "Tegucigalpa", "timezone": "America/Tegucigalpa"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        user = db_session.query(models.User).filter(models.User.username == "fiscal_admin").one()

        sale_15 = models.Sale(
            store_id=store_id,
            customer_name="Cliente ISV15",
            payment_method=models.PaymentMethod.EFECTIVO,
            subtotal_amount=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            status="COMPLETADA",
            created_at=datetime(2024, 5, 5, 10, 0),
            performed_by_id=user.id,
        )
        sale_18 = models.Sale(
            store_id=store_id,
            customer_name="Cliente ISV18",
            payment_method=models.PaymentMethod.TARJETA,
            subtotal_amount=Decimal("200.00"),
            tax_amount=Decimal("36.00"),
            total_amount=Decimal("236.00"),
            status="COMPLETADA",
            created_at=datetime(2024, 5, 12, 12, 0),
            performed_by_id=user.id,
        )
        sale_exempt = models.Sale(
            store_id=store_id,
            customer_name="Cliente Exento",
            payment_method=models.PaymentMethod.TRANSFERENCIA,
            subtotal_amount=Decimal("500.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("500.00"),
            status="COMPLETADA",
            created_at=datetime(2024, 5, 20, 9, 30),
            performed_by_id=user.id,
        )

        vendor = models.Proveedor(nombre="Proveedor Fiscal", estado="activo")
        db_session.add(vendor)
        db_session.flush()

        purchase_15 = models.Compra(
            proveedor_id=vendor.id_proveedor,
            usuario_id=user.id,
            fecha=datetime(2024, 5, 7, 15, 0),
            total=Decimal("345.00"),
            impuesto=Decimal("45.00"),
            forma_pago="TRANSFERENCIA",
            estado="REGISTRADA",
        )
        purchase_18 = models.Compra(
            proveedor_id=vendor.id_proveedor,
            usuario_id=user.id,
            fecha=datetime(2024, 5, 18, 11, 0),
            total=Decimal("236.00"),
            impuesto=Decimal("36.00"),
            forma_pago="CONTADO",
            estado="REGISTRADA",
        )
        purchase_exempt = models.Compra(
            proveedor_id=vendor.id_proveedor,
            usuario_id=user.id,
            fecha=datetime(2024, 5, 25, 10, 15),
            total=Decimal("480.00"),
            impuesto=Decimal("0.00"),
            forma_pago="TRANSFERENCIA",
            estado="REGISTRADA",
        )

        db_session.add_all([sale_15, sale_18, sale_exempt, purchase_15, purchase_18, purchase_exempt])
        db_session.commit()

        expected = _load_expected_totals()

        sales_response = client.get(
            "/reports/fiscal/books",
            params={"year": 2024, "month": 5, "book_type": "sales"},
            headers=headers,
        )
        assert sales_response.status_code == status.HTTP_200_OK
        sales_payload = sales_response.json()
        assert sales_payload["totals"]["registros"] == 3
        assert sales_payload["totals"]["base_15"] == pytest.approx(expected["sales"]["totals"]["base_15"])
        assert sales_payload["totals"]["impuesto_15"] == pytest.approx(expected["sales"]["totals"]["impuesto_15"])
        assert sales_payload["totals"]["base_18"] == pytest.approx(expected["sales"]["totals"]["base_18"])
        assert sales_payload["totals"]["impuesto_18"] == pytest.approx(expected["sales"]["totals"]["impuesto_18"])
        assert sales_payload["totals"]["base_exenta"] == pytest.approx(expected["sales"]["totals"]["base_exenta"])
        assert sales_payload["totals"]["total_general"] == pytest.approx(expected["sales"]["totals"]["total_general"])

        purchases_response = client.get(
            "/reports/fiscal/books",
            params={"year": 2024, "month": 5, "book_type": "purchases"},
            headers=headers,
        )
        assert purchases_response.status_code == status.HTTP_200_OK
        purchases_payload = purchases_response.json()
        assert purchases_payload["totals"]["registros"] == 3
        assert purchases_payload["totals"]["base_15"] == pytest.approx(expected["purchases"]["totals"]["base_15"])
        assert purchases_payload["totals"]["impuesto_15"] == pytest.approx(expected["purchases"]["totals"]["impuesto_15"])
        assert purchases_payload["totals"]["base_18"] == pytest.approx(expected["purchases"]["totals"]["base_18"])
        assert purchases_payload["totals"]["impuesto_18"] == pytest.approx(expected["purchases"]["totals"]["impuesto_18"])
        assert purchases_payload["totals"]["base_exenta"] == pytest.approx(expected["purchases"]["totals"]["base_exenta"])
        assert purchases_payload["totals"]["total_general"] == pytest.approx(expected["purchases"]["totals"]["total_general"])

        export_without_reason = client.get(
            "/reports/fiscal/books",
            params={"year": 2024, "month": 5, "book_type": "sales", "format": "pdf"},
            headers=headers,
        )
        assert export_without_reason.status_code == status.HTTP_400_BAD_REQUEST

        export_headers = {**headers, "X-Reason": "Descarga fiscal QA"}
        export_response = client.get(
            "/reports/fiscal/books",
            params={"year": 2024, "month": 5, "book_type": "sales", "format": "xml"},
            headers=export_headers,
        )
        assert export_response.status_code == status.HTTP_200_OK
        assert "application/xml" in export_response.headers["content-type"].lower()
    finally:
        settings.enable_purchases_sales = previous_flag
