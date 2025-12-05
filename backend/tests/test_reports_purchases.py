from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "purchases_admin",
        "password": "Compras123*",
        "full_name": "Compras Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_purchases_report_combines_metrics(client, db_session: Session):
    previous_analytics = settings.enable_analytics_adv
    previous_sales = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        headers = {"Authorization": f"Bearer {token}"}

        store_resp = client.post(
            "/stores",
            json={"name": "Compras Centro", "location": "CDMX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_resp.status_code == status.HTTP_201_CREATED
        store_id = store_resp.json()["id"]

        device_resp = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "CMP-001",
                "name": "Sensor Compras",
                "quantity": 20,
                "unit_price": 950.0,
                "costo_unitario": 600.0,
                "margen_porcentaje": 22.0,
                "fecha_compra": date(2024, 3, 1).isoformat(),
            },
            headers=headers,
        )
        assert device_resp.status_code == status.HTTP_201_CREATED
        device_id = device_resp.json()["id"]

        supplier_name = "Proveedor Norte"
        device = db_session.get(models.Device, device_id)
        device.proveedor = supplier_name
        device.fecha_compra = date.today() - timedelta(days=10)
        db_session.commit()

        purchase_order = models.PurchaseOrder(
            store_id=store_id,
            supplier=supplier_name,
            status=models.PurchaseStatus.RECIBIDA_TOTAL,
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        db_session.add(purchase_order)
        db_session.flush()

        order_item = models.PurchaseOrderItem(
            purchase_order_id=purchase_order.id,
            device_id=device_id,
            quantity_ordered=10,
            quantity_received=8,
            unit_cost=Decimal("500"),
        )
        db_session.add(order_item)
        db_session.commit()

        sale_resp = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 4}],
            },
            headers={**headers, "X-Reason": "Venta de prueba"},
        )
        assert sale_resp.status_code == status.HTTP_201_CREATED

        report_response = client.get("/reports/purchases", headers=headers)
        assert report_response.status_code == status.HTTP_200_OK
        items = report_response.json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["supplier"] == supplier_name
        assert item["store_id"] == store_id
        assert item["device_count"] == 1
        assert item["total_ordered"] == 10
        assert item["total_received"] == 8
        assert item["pending_backorders"] == 2
        assert item["total_cost"] == 4000.0
        assert item["average_unit_cost"] == 500.0
        assert item["average_rotation"] == 0.5
        assert pytest.approx(item["average_days_in_stock"], rel=0.1) == 10.0

        filtered_response = client.get(
            f"/reports/purchases?supplier={supplier_name}",
            headers=headers,
        )
        assert filtered_response.status_code == status.HTTP_200_OK
        assert len(filtered_response.json()["items"]) == 1

        empty_response = client.get(
            "/reports/purchases?supplier=Proveedor%20Sur",
            headers=headers,
        )
        assert empty_response.status_code == status.HTTP_200_OK
        assert empty_response.json()["items"] == []
    finally:
        settings.enable_analytics_adv = previous_analytics
        settings.enable_purchases_sales = previous_sales
