"""Prueba de escenario complejo de costo promedio ponderado con recepciones parciales,
   devolucion parcial y venta posterior verificando margen y costo final.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings


@pytest.mark.usefixtures("client", "db_session")
def test_complex_cost_flow(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        # Bootstrap usuario admin
        # reutilizamos helper existente
        from backend.tests.test_purchases import _bootstrap_admin
        token, user_id = _bootstrap_admin(client, db_session)
        auth = {"Authorization": f"Bearer {token}",
                "X-Reason": "Flujo complejo costos"}

        # Crear sucursal
        store_resp = client.post(
            "/stores",
            json={"name": "Costos Demo", "location": "CDMX", "timezone": "UTC"},
            headers=auth,
        )
        assert store_resp.status_code == status.HTTP_201_CREATED
        store_id = store_resp.json()["id"]

        # Crear dispositivo inicial sin stock
        device_payload = {
            "sku": "SKU-COST-CPLX",
            "name": "Dispositivo Margen",
            "quantity": 0,
            "unit_price": 500.0,  # precio venta actual
            "costo_unitario": 0.0,  # arranca en 0 hasta primera recepción
            "margen_porcentaje": 10.0,
        }
        device_resp = client.post(
            f"/stores/{store_id}/devices", json=device_payload, headers=auth)
        assert device_resp.status_code == status.HTTP_201_CREATED
        device_id = device_resp.json()["id"]

        # Orden de compra con 20 unidades a diferentes costos recibidas en dos tandas
        order_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Escalonado",
            "items": [
                {"device_id": device_id, "quantity_ordered": 20, "unit_cost": 260.0},
            ],
        }
        order_resp = client.post(
            "/purchases", json=order_payload, headers=auth)
        assert order_resp.status_code == status.HTTP_201_CREATED
        order_id = order_resp.json()["id"]

        # Recepción parcial 1: 8 unidades a costo 260 (usa unit_cost del item)
        receive_1 = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 8}]},
            headers={**auth, "X-Reason": "Recepcion parcial A"},
        )
        assert receive_1.status_code == status.HTTP_200_OK

        # Ajustamos el costo para la segunda recepción simulando cambio de proveedor (editamos item en DB)
        item_record = db_session.execute(
            select(models.PurchaseOrderItem).where(
                models.PurchaseOrderItem.purchase_order_id == order_id)
        ).scalar_one()
        item_record.unit_cost = Decimal("300")
        db_session.flush()

        # Recepción parcial 2: 7 unidades a nuevo costo 300
        receive_2 = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 7}]},
            headers={**auth, "X-Reason": "Recepcion parcial B"},
        )
        assert receive_2.status_code == status.HTTP_200_OK

        # Devolución parcial: 3 unidades (toma del último costo recibido preferentemente, política FIFO/AVG heredada)
        return_resp = client.post(
            f"/purchases/{order_id}/returns",
            json={"device_id": device_id, "quantity": 3,
                  "reason": "Defecto parcial"},
            headers={**auth, "X-Reason": "Devolucion parcial"},
        )
        assert return_resp.status_code == status.HTTP_200_OK

        # Stock esperado tras operaciones: 8 + 7 - 3 = 12 unidades
        device_record = db_session.execute(select(models.Device).where(
            models.Device.id == device_id)).scalar_one()
        assert device_record.quantity == 12

        # Calculo manual costo promedio ponderado esperado:
        # Recepcion A: 8 * 260 = 2080
        # Recepcion B: 7 * 300 = 2100  => Total 15 unidades costo acumulado 4180
        # Devolucion 3 unidades (tomamos costo promedio al momento de la devolución si lógica AVG):
        # Costo promedio previo a devolución = 4180 / 15 = 278.6667
        # Valor devuelto = 3 * 278.6667 = 836.0 (aprox)
        # Costo restante = 4180 - 836 = 3344
        # Unidades restantes = 12 => costo promedio final esperado ~ 278.67
        expected_avg_cost = Decimal("3344") / Decimal("12")

        # Tolerancia +/- 0.02 por redondeos internos
        assert Decimal(str(device_record.costo_unitario)).quantize(
            Decimal("0.01")) == expected_avg_cost.quantize(Decimal("0.01"))

        # Registrar una venta de 4 unidades para validar margen y no romper cálculo
        sale_payload = {
            "store_id": store_id,
            "items": [{"device_id": device_id, "quantity": 4, "unit_price": 500.0}],
            "payment_method": "EFECTIVO",
            "discount": 0.0,
        }
        sale_resp = client.post(
            "/sales", json=sale_payload, headers={**auth, "X-Reason": "Venta prueba"})
        assert sale_resp.status_code == status.HTTP_201_CREATED

        # Verificar que el stock y costo no se alteran fuera de la lógica de movimientos (AVG mantiene costo)
        post_sale_device = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)).scalar_one()
        assert post_sale_device.quantity == 8  # 12 - 4
        assert Decimal(str(post_sale_device.costo_unitario)).quantize(
            Decimal("0.01")) == expected_avg_cost.quantize(Decimal("0.01"))

        # Margen unitario actual = 500 - expected_avg_cost
        margen_unitario = Decimal(
            "500") - expected_avg_cost.quantize(Decimal("0.01"))
        assert margen_unitario > 0
    finally:
        settings.enable_purchases_sales = previous_flag
