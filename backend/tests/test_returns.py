from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytest
from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.settings import return_policy_settings
from backend.app.core.roles import ADMIN
from backend.app.security import hash_password


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "returns_admin",
        "password": "Retornos123*",
        "full_name": "Operador Devoluciones",
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

    token = token_response.json()["access_token"]

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_returns_overview_includes_reasons(client, db_session):
    original_flag = settings.enable_purchases_sales
    original_defective_store = settings.defective_returns_store_id
    settings.enable_purchases_sales = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        store_response = client.post(
            "/stores",
            json={
                "name": "Sucursal Auditoría",
                "location": "MX",
                "timezone": "America/Mexico_City",
            },
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "RET-001",
            "name": "Lector Inventario",
            "quantity": 0,
            "unit_price": 120.0,
            "costo_unitario": 80.0,
            "margen_porcentaje": 20.0,
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    try:
        purchase_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Central",
            "items": [{"device_id": device_id, "quantity_ordered": 5, "unit_cost": 90.0}],
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "RET-001",
                "name": "Lector Inventario",
                "quantity": 0,
                "unit_price": 120.0,
                "costo_unitario": 80.0,
                "margen_porcentaje": 20.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        purchase_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Central",
            "items": [
                {"device_id": device_id, "quantity_ordered": 5, "unit_cost": 90.0}
            ],
        }
        purchase_response = client.post(
            "/purchases",
            json=purchase_payload,
            headers={**auth_headers, "X-Reason": "Planeación inventario"},
        )
        assert purchase_response.status_code == status.HTTP_201_CREATED
        order_id = purchase_response.json()["id"]

        receive_payload = {"items": [{"device_id": device_id, "quantity": 5}]}
        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json=receive_payload,
            headers={**auth_headers, "X-Reason": "Recepción inicial"},
        )
        assert receive_response.status_code == status.HTTP_200_OK

        defective_store_response = client.post(
            "/stores",
            json={
                "name": "Almacén Defectuosos",
                "location": "MX",
                "timezone": "America/Mexico_City",
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        purchase_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Central",
            "items": [
                {"device_id": device_id, "quantity_ordered": 5, "unit_cost": 90.0}
            ],
        }
        purchase_response = client.post(
            "/purchases",
            json=purchase_payload,
            headers={**auth_headers, "X-Reason": "Planeación inventario"},
        )
        assert purchase_response.status_code == status.HTTP_201_CREATED
        order_id = purchase_response.json()["id"]

        receive_payload = {"items": [{"device_id": device_id, "quantity": 5}]}
        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json=receive_payload,
            headers={**auth_headers, "X-Reason": "Recepción inicial"},
        )
        assert receive_response.status_code == status.HTTP_200_OK

        defective_store_id = settings.defective_returns_store_id
        if defective_store_id is None:
            defective_store_response = client.post(
                "/stores",
                json={
                    "name": "Almacén Defectuosos",
                    "location": "MX",
                    "timezone": "America/Mexico_City",
                },
                headers=auth_headers,
            )
            assert defective_store_response.status_code == status.HTTP_201_CREATED
            defective_store_id = defective_store_response.json()["id"]
            settings.defective_returns_store_id = defective_store_id

        purchase_return_payload = {
            "device_id": device_id,
            "quantity": 2,
            "reason": "Proveedor defectuoso",
        }
        purchase_return_response = client.post(
            f"/purchases/{order_id}/returns",
            json=purchase_return_payload,
            headers={**auth_headers, "X-Reason": "Devolución a proveedor"},
        )
        assert purchase_return_response.status_code == status.HTTP_200_OK

        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 2}],
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers={**auth_headers, "X-Reason": "Venta mostrador"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_return_payload = {
            "sale_id": sale_id,
            "items": [
                {
                    "device_id": device_id,
                    "quantity": 1,
                    "reason": "Cliente arrepentido",
                    "disposition": "defectuoso",
                }
            ],
        }
        sale_return_response = client.post(
            "/sales/returns",
            json=sale_return_payload,
            headers={**auth_headers, "X-Reason": "Reingreso cliente"},
        )
        assert sale_return_response.status_code == status.HTTP_200_OK
        sale_return_body = sale_return_response.json()
        assert sale_return_body
        first_sale_return = sale_return_body[0]
        assert first_sale_return["disposition"] == "defectuoso"
        assert first_sale_return["warehouse_id"] == defective_store_id

        returns_response = client.get(
            "/returns",
            params={"store_id": store_id, "limit": 10},
            headers=auth_headers,
        )
        assert returns_response.status_code == status.HTTP_200_OK
        payload = returns_response.json()

        assert payload["totals"]["total"] == 2
        assert payload["totals"]["sales"] == 1
        assert payload["totals"]["purchases"] == 1
        assert payload["totals"]["categories"]["cliente"] == 1
        assert payload["totals"]["categories"]["defecto"] == 1

        reasons_by_type = {entry["type"]: entry["reason"] for entry in payload["items"]}
        assert reasons_by_type["sale"] == "Cliente arrepentido"
        assert reasons_by_type["purchase"] == "Proveedor defectuoso"

        processed = next(
            (entry for entry in payload["items"] if entry["type"] == "sale"),
            None,
        )
        assert processed is not None
        assert processed["processed_by_id"] == user_id
        assert "Venta #" in processed["reference_label"]
        assert processed["disposition"] == "defectuoso"
        assert processed["warehouse_id"] == defective_store_id
        assert processed["reason_category"] == "cliente"

        purchase_record = next(
            (entry for entry in payload["items"] if entry["type"] == "purchase"),
            None,
        )
        assert purchase_record is not None
        assert purchase_record["reason_category"] == "defecto"

        sale_item = db_session.execute(
            select(models.SaleItem).where(
                models.SaleItem.sale_id == sale_id,
                models.SaleItem.device_id == device_id,
            )
        ).scalar_one()
        unit_total = Decimal(sale_item.total_line)
        unit_quantity = Decimal(sale_item.quantity)
        expected_refund = (unit_total / unit_quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        assert processed["payment_method"] == "EFECTIVO"
        assert processed["refund_amount"] == pytest.approx(float(expected_refund))
        assert payload["totals"]["refund_total_amount"] == pytest.approx(
            float(expected_refund)
        )
        assert payload["totals"]["refunds_by_method"]["EFECTIVO"] == pytest.approx(
            float(expected_refund)
        )
    finally:
        settings.enable_purchases_sales = original_flag
        settings.defective_returns_store_id = original_defective_store


def test_sale_return_requires_supervisor_pin_when_limit_exceeded(client, db_session):
    original_flag = settings.enable_purchases_sales
    original_limit = return_policy_settings.sale_without_supervisor_days
    settings.enable_purchases_sales = True
    return_policy_settings.sale_without_supervisor_days = 0
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Sur", "location": "MX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={"sku": "PIN-001", "name": "Lector PIN", "quantity": 1, "unit_price": 90.0},
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers={**auth_headers, "X-Reason": "Venta tardía"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_record = db_session.get(models.Sale, sale_id)
        assert sale_record is not None
        sale_record.created_at = sale_record.created_at - timedelta(days=2)
        db_session.add(sale_record)
        db_session.commit()

        response = client.post(
            "/sales/returns",
            json={
                "sale_id": sale_id,
                "items": [
                    {
                        "device_id": device_id,
                        "quantity": 1,
                        "reason": "Cliente requiere autorización",
                    }
                ],
            },
            headers={**auth_headers, "X-Reason": "Devolución tardía"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "[sale_return_supervisor_required]" in response.json()["detail"]

        supervisor = db_session.get(models.User, user_id)
        supervisor.supervisor_pin_hash = hash_password("4321")
        db_session.add(supervisor)
        db_session.commit()

        invalid_response = client.post(
            "/sales/returns",
            json={
                "sale_id": sale_id,
                "items": [
                    {
                        "device_id": device_id,
                        "quantity": 1,
                        "reason": "Cliente requiere autorización",
                    }
                ],
                "approval": {
                    "supervisor_username": supervisor.username,
                    "pin": "0000",
                },
            },
            headers={**auth_headers, "X-Reason": "Devolución tardía"},
        )
        assert invalid_response.status_code == status.HTTP_403_FORBIDDEN
        assert "[sale_return_invalid_supervisor_pin]" in invalid_response.json()["detail"]

        valid_response = client.post(
            "/sales/returns",
            json={
                "sale_id": sale_id,
                "items": [
                    {
                        "device_id": device_id,
                        "quantity": 1,
                        "reason": "Cliente requiere autorización",
                    }
                ],
                "approval": {
                    "supervisor_username": supervisor.username,
                    "pin": "4321",
                },
            },
            headers={**auth_headers, "X-Reason": "Devolución tardía"},
        )
        assert valid_response.status_code == status.HTTP_200_OK
        body = valid_response.json()
        assert body
        first_return = body[0]
        assert first_return["approved_by_id"] == user_id
        assert first_return["reason_category"] == "cliente"
    finally:
        settings.enable_purchases_sales = original_flag
        return_policy_settings.sale_without_supervisor_days = original_limit
