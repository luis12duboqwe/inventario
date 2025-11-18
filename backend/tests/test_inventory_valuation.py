"""Pruebas para la vista y servicio de valoración de inventario."""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app import models
from backend.app.services import inventory as inventory_service


@pytest.mark.usefixtures("db_session")
def test_inventory_valuation_view_and_service(db_session):
    store = models.Store(name="Central", code="SUC-001", timezone="UTC")
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
    assert len(valuations) == 3, "La vista debe devolver una fila por dispositivo"

    # Construir cálculos directos (fuente de verdad) en memoria.
    # Costos promedio ponderados: para cada dispositivo con items de compra usamos sum(cost)/sum(qty); si no, costo_unitario.
    avg_cost_phone_a = (8 * 95) / 8  # Solo cantidad recibida influye
    avg_cost_phone_b = (5 * 210) / 5
    avg_cost_accessory = 50  # Sin items de compra => costo_unitario

    # Totales por producto
    costo_total_phone_a = 10 * avg_cost_phone_a
    costo_total_phone_b = 5 * avg_cost_phone_b
    costo_total_accessory = 2 * avg_cost_accessory
    valor_total_phone_a = 10 * 150
    valor_total_phone_b = 5 * 250
    valor_total_accessory = 2 * 80

    # Totales de tienda / generales (solo una tienda)
    expected_store_total = valor_total_phone_a + \
        valor_total_phone_b + valor_total_accessory
    expected_store_cost = costo_total_phone_a + \
        costo_total_phone_b + costo_total_accessory

    # Márgenes por producto
    margen_unit_phone_a = 150 - avg_cost_phone_a
    margen_unit_phone_b = 250 - avg_cost_phone_b
    margen_unit_accessory = 80 - avg_cost_accessory
    margen_total_phone_a = 10 * margen_unit_phone_a
    margen_total_phone_b = 5 * margen_unit_phone_b
    margen_total_accessory = 2 * margen_unit_accessory
    expected_margen_total_store = margen_total_phone_a + \
        margen_total_phone_b + margen_total_accessory

    # Categoría Telefonía
    valor_total_categoria_telefonia = valor_total_phone_a + valor_total_phone_b
    margen_categoria_valor_telefonia = margen_total_phone_a + margen_total_phone_b
    margen_categoria_porcentaje_telefonia = (
        margen_categoria_valor_telefonia / valor_total_categoria_telefonia) * 100

    by_sku = {valuation.sku: valuation for valuation in valuations}

    # Verificaciones de costos promedio ponderados
    assert float(
        by_sku["SKU-PHONE-A"].costo_promedio_ponderado) == pytest.approx(avg_cost_phone_a)
    assert float(
        by_sku["SKU-PHONE-B"].costo_promedio_ponderado) == pytest.approx(avg_cost_phone_b)
    assert float(
        by_sku["SKU-ACC-01"].costo_promedio_ponderado) == pytest.approx(avg_cost_accessory)

    # Valor y costo por producto
    assert float(
        by_sku["SKU-PHONE-A"].valor_costo_producto) == pytest.approx(costo_total_phone_a)
    assert float(
        by_sku["SKU-PHONE-B"].valor_costo_producto) == pytest.approx(costo_total_phone_b)
    assert float(
        by_sku["SKU-ACC-01"].valor_costo_producto) == pytest.approx(costo_total_accessory)

    # Totales de tienda y global replicados en cada fila
    for sku in by_sku:
        assert float(by_sku[sku].valor_total_tienda) == pytest.approx(
            expected_store_total)
        assert float(by_sku[sku].valor_total_general) == pytest.approx(
            expected_store_total)
        assert float(by_sku[sku].valor_costo_tienda) == pytest.approx(
            expected_store_cost)
        assert float(by_sku[sku].valor_costo_general) == pytest.approx(
            expected_store_cost)
        assert float(by_sku[sku].margen_total_tienda) == pytest.approx(
            expected_margen_total_store)
        assert float(by_sku[sku].margen_total_general) == pytest.approx(
            expected_margen_total_store)

    # Márgenes unitarios y porcentajes por producto
    assert float(
        by_sku["SKU-PHONE-A"].margen_unitario) == pytest.approx(margen_unit_phone_a)
    assert float(
        by_sku["SKU-PHONE-B"].margen_unitario) == pytest.approx(margen_unit_phone_b)
    assert float(
        by_sku["SKU-ACC-01"].margen_unitario) == pytest.approx(margen_unit_accessory)
    assert float(by_sku["SKU-PHONE-A"].margen_producto_porcentaje) == pytest.approx(
        (margen_unit_phone_a / 150) * 100, rel=1e-3)
    assert float(by_sku["SKU-PHONE-B"].margen_producto_porcentaje) == pytest.approx(
        (margen_unit_phone_b / 250) * 100, rel=1e-3)
    assert float(by_sku["SKU-ACC-01"].margen_producto_porcentaje) == pytest.approx(
        (margen_unit_accessory / 80) * 100, rel=1e-3)

    # Categoría Telefonía
    assert float(by_sku["SKU-PHONE-A"].valor_total_categoria) == pytest.approx(
        valor_total_categoria_telefonia)
    assert float(by_sku["SKU-PHONE-B"].valor_total_categoria) == pytest.approx(
        valor_total_categoria_telefonia)
    assert float(by_sku["SKU-PHONE-A"].margen_categoria_valor) == pytest.approx(
        margen_categoria_valor_telefonia)
    assert float(by_sku["SKU-PHONE-B"].margen_categoria_valor) == pytest.approx(
        margen_categoria_valor_telefonia)
    assert float(by_sku["SKU-PHONE-A"].margen_categoria_porcentaje) == pytest.approx(
        margen_categoria_porcentaje_telefonia, rel=1e-3)
    assert float(by_sku["SKU-PHONE-B"].margen_categoria_porcentaje) == pytest.approx(
        margen_categoria_porcentaje_telefonia, rel=1e-3)

    accessories = inventory_service.calculate_inventory_valuation(
        db_session, categories=["Accesorios"], store_ids=[store.id]
    )
    assert len(accessories) == 1
    assert accessories[0].sku == "SKU-ACC-01"
