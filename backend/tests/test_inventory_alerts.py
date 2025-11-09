from __future__ import annotations

from decimal import Decimal

from fastapi import status

from backend.app import models, schemas
from backend.app.core.settings import InventoryAlertSettings
from backend.app.services.inventory_alerts import InventoryAlertsService
from backend.app.services.stock_alerts import StockAlertsService


def _bootstrap_admin(client):
    payload = {
        "username": "alerts_admin",
        "password": "Alerts123*",
        "full_name": "Alerts Admin",
        "roles": ["ADMIN"],
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


def _seed_inventory_alerts_dataset(
    db_session,
) -> tuple[models.Store, models.Store, list[models.Device]]:
    store_central = models.Store(name="Central", code="SUC-ALERT", timezone="UTC")
    store_norte = models.Store(name="Norte", code="SUC-NORTE", timezone="UTC")
    db_session.add_all([store_central, store_norte])
    db_session.flush()

    devices = [
        models.Device(
            store_id=store_central.id,
            sku="AL-001",
            name="Teléfono A",
            quantity=1,
            unit_price=Decimal("120.00"),
            minimum_stock=2,
            reorder_point=3,
        ),
        models.Device(
            store_id=store_central.id,
            sku="AL-002",
            name="Teléfono B",
            quantity=3,
            unit_price=Decimal("80.00"),
            minimum_stock=2,
            reorder_point=4,
        ),
        models.Device(
            store_id=store_central.id,
            sku="AL-003",
            name="Teléfono C",
            quantity=6,
            unit_price=Decimal("70.00"),
            minimum_stock=2,
            reorder_point=5,
        ),
        models.Device(
            store_id=store_norte.id,
            sku="AL-004",
            name="Tablet Norte",
            quantity=2,
            unit_price=Decimal("150.00"),
            minimum_stock=1,
            reorder_point=2,
        ),
    ]
    db_session.add_all(devices)
    db_session.flush()

    return store_central, store_norte, devices


def test_inventory_alerts_service_evaluation() -> None:
    settings = InventoryAlertSettings(
        default_low_stock_threshold=6,
        min_low_stock_threshold=0,
        max_low_stock_threshold=50,
        warning_ratio=0.5,
        critical_ratio=0.25,
        minimum_warning_units=2,
        minimum_critical_units=1,
        adjustment_variance_threshold=4,
    )
    service = InventoryAlertsService(settings=settings)
    devices = [
        schemas.LowStockDevice(
            store_id=1,
            store_name="Central",
            device_id=1,
            sku="SKU-ALPHA",
            name="Alpha",
            quantity=1,
            unit_price=Decimal("120.00"),
            minimum_stock=2,
            reorder_point=3,
        ),
        schemas.LowStockDevice(
            store_id=1,
            store_name="Central",
            device_id=2,
            sku="SKU-BETA",
            name="Beta",
            quantity=3,
            unit_price=Decimal("95.00"),
            minimum_stock=2,
            reorder_point=4,
        ),
        schemas.LowStockDevice(
            store_id=2,
            store_name="Norte",
            device_id=3,
            sku="SKU-GAMMA",
            name="Gamma",
            quantity=5,
            unit_price=Decimal("80.00"),
            minimum_stock=1,
            reorder_point=6,
        ),
    ]

    evaluation = service.evaluate(devices, threshold=6)

    assert evaluation.thresholds.warning == 3
    assert evaluation.thresholds.critical == 2
    severities = [item.severity for item in evaluation.items]
    assert severities == ["critical", "warning", "notice"]
    assert evaluation.summary.total == 3
    assert evaluation.summary.critical == 1
    assert evaluation.summary.warning == 1
    assert evaluation.summary.notice == 1


def test_inventory_alerts_endpoint_returns_summary(client, db_session) -> None:
    store_central, _, _ = _seed_inventory_alerts_dataset(db_session)

    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/alerts/inventory", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["summary"]["total"] == 3
    severities = {item["severity"] for item in payload["items"]}
    assert severities == {"critical", "warning"}
    first_item = payload["items"][0]
    assert "minimum_stock" in first_item
    assert "reorder_point" in first_item
    assert "projected_days" in first_item
    assert isinstance(first_item.get("insights"), list)

    response_store = client.get(
        f"/alerts/inventory?store_id={store_central.id}&threshold=3",
        headers=headers,
    )
    assert response_store.status_code == status.HTTP_200_OK
    store_payload = response_store.json()
    assert store_payload["settings"]["threshold"] == 3
    assert store_payload["summary"] == {
        "total": 2,
        "critical": 1,
        "warning": 1,
        "notice": 0,
    }
    assert {item["sku"] for item in store_payload["items"]} == {"AL-001", "AL-002"}
    for item in store_payload["items"]:
        assert item["minimum_stock"] >= 0
        assert item["reorder_point"] >= item["minimum_stock"]
        assert isinstance(item.get("insights"), list)


def test_inventory_alerts_endpoint_clamps_threshold_range(
    client, db_session
) -> None:
    _, _, devices = _seed_inventory_alerts_dataset(db_session)
    service = InventoryAlertsService()

    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    response_high = client.get("/alerts/inventory?threshold=999", headers=headers)
    assert response_high.status_code == status.HTTP_200_OK
    payload_high = response_high.json()
    assert payload_high["settings"]["threshold"] == service.max_threshold
    assert payload_high["summary"]["total"] == len(devices)

    response_low = client.get("/alerts/inventory?threshold=-5", headers=headers)
    assert response_low.status_code == status.HTTP_200_OK
    payload_low = response_low.json()
    assert payload_low["settings"]["threshold"] == service.min_threshold
    assert payload_low["summary"] == {
        "total": 0,
        "critical": 0,
        "warning": 0,
        "notice": 0,
    }


def test_stock_alerts_service_generates_insights(db_session) -> None:
    store_central, _, _ = _seed_inventory_alerts_dataset(db_session)
    service = StockAlertsService()

    result = service.generate(db_session, store_id=store_central.id, threshold=3)

    assert result.settings.threshold == 3
    assert result.summary.total == 2
    critical_item = next(item for item in result.items if item.severity == "critical")
    assert critical_item.minimum_stock == 2
    assert "Por debajo del stock mínimo" in critical_item.insights
