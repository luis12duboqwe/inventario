"""Pruebas para la vista y servicio de valoración de inventario."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app import models
from backend.app.services import inventory as inventory_service


@pytest.mark.usefixtures("db_session")
def test_inventory_valuation_view_and_service(db_session):
    store = models.Store(name="Central", timezone="UTC")
    db_session.add(store)
    db_session.flush()

    device_phone_a = models.Device(
        store_id=store.id,
        sku="SKU-PHONE-A",
        name="Smartphone A",
        quantity=10,
        unit_price=Decimal("150"),
        costo_unitario=Decimal("110"),
        categoria="Telefonía",
    )
    device_phone_b = models.Device(
        store_id=store.id,
        sku="SKU-PHONE-B",
        name="Smartphone B",
        quantity=5,
        unit_price=Decimal("250"),
        costo_unitario=Decimal("200"),
        categoria="Telefonía",
    )
    device_accessory = models.Device(
        store_id=store.id,
        sku="SKU-ACC-01",
        name="Cargador Rápido",
        quantity=2,
        unit_price=Decimal("80"),
        costo_unitario=Decimal("50"),
        categoria="Accesorios",
    )
    db_session.add_all([device_phone_a, device_phone_b, device_accessory])
    db_session.flush()

    order = models.PurchaseOrder(
        store_id=store.id,
        supplier="Proveedor Demo",
        status=models.PurchaseStatus.COMPLETADA,
    )
    db_session.add(order)
    db_session.flush()

    item_phone_a = models.PurchaseOrderItem(
        purchase_order_id=order.id,
        device_id=device_phone_a.id,
        quantity_ordered=10,
        quantity_received=8,
        unit_cost=Decimal("95"),
    )
    item_phone_b = models.PurchaseOrderItem(
        purchase_order_id=order.id,
        device_id=device_phone_b.id,
        quantity_ordered=5,
        quantity_received=5,
        unit_cost=Decimal("210"),
    )
    db_session.add_all([item_phone_a, item_phone_b])
    db_session.flush()

    valuations = inventory_service.calculate_inventory_valuation(db_session)
    assert len(valuations) == 3

    by_sku = {valuation.sku: valuation for valuation in valuations}
    assert float(by_sku["SKU-PHONE-A"].costo_promedio_ponderado) == pytest.approx(95.0)
    assert float(by_sku["SKU-ACC-01"].costo_promedio_ponderado) == pytest.approx(50.0)

    expected_store_total = 10 * 150 + 5 * 250 + 2 * 80
    assert float(by_sku["SKU-PHONE-A"].valor_total_tienda) == pytest.approx(expected_store_total)
    assert float(by_sku["SKU-PHONE-B"].valor_total_general) == pytest.approx(expected_store_total)

    assert float(by_sku["SKU-PHONE-A"].margen_unitario) == pytest.approx(55.0)
    assert float(by_sku["SKU-PHONE-A"].margen_producto_porcentaje) == pytest.approx(36.67, rel=1e-3)
    assert float(by_sku["SKU-PHONE-B"].margen_categoria_valor) == pytest.approx(750.0)
    assert float(by_sku["SKU-PHONE-B"].margen_categoria_porcentaje) == pytest.approx(27.27, rel=1e-3)

    accessories = inventory_service.calculate_inventory_valuation(
        db_session, categories=["Accesorios"], store_ids=[store.id]
    )
    assert len(accessories) == 1
    assert accessories[0].sku == "SKU-ACC-01"
