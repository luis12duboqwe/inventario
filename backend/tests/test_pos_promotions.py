from __future__ import annotations

from decimal import Decimal

from backend.app.config import settings

from .test_pos import _bootstrap_admin


def test_pos_promotions_flow(client):
    settings.enable_purchases_sales = True
    settings.enable_pos_promotions = True
    settings.enable_pos_promotions_volume = True
    settings.enable_pos_promotions_combo = True
    settings.enable_pos_promotions_coupons = True

    token = _bootstrap_admin(client)
    base_headers = {
        "Authorization": f"Bearer {token}",
        "X-Reason": "Configurar promociones POS",
    }

    store_response = client.post(
        "/stores",
        json={"name": "Tienda Promos", "location": "QRO", "timezone": "America/Mexico_City"},
        headers=base_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_payloads = [
        {"sku": "PROMO-A", "name": "Equipo volumen", "quantity": 10, "unit_price": 100.0},
        {"sku": "PROMO-B", "name": "Equipo combo 1", "quantity": 10, "unit_price": 80.0},
        {"sku": "PROMO-C", "name": "Equipo combo 2", "quantity": 10, "unit_price": 60.0},
        {"sku": "PROMO-D", "name": "Accesorio libre", "quantity": 10, "unit_price": 40.0},
    ]
    device_ids: list[int] = []
    for payload in device_payloads:
        response = client.post(
            f"/stores/{store_id}/devices",
            json=payload,
            headers=base_headers,
        )
        assert response.status_code == 201
        device_ids.append(response.json()["id"])

    promotions_payload = {
        "store_id": store_id,
        "feature_flags": {"volume": True, "combos": True, "coupons": True},
        "volume_promotions": [
            {"id": "VOL-10", "device_id": device_ids[0], "min_quantity": 3, "discount_percent": 10},
        ],
        "combo_promotions": [
            {
                "id": "COM-12",
                "items": [
                    {"device_id": device_ids[1], "quantity": 1},
                    {"device_id": device_ids[2], "quantity": 1},
                ],
                "discount_percent": 12,
            }
        ],
        "coupons": [
            {"code": "BIENVENIDA", "discount_percent": 5, "description": "Clientes nuevos"},
        ],
    }

    update_response = client.put("/pos/promotions", json=promotions_payload, headers=base_headers)
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["feature_flags"]["volume"] is True
    assert body["volume_promotions"]

    fetch_response = client.get(
        "/pos/promotions",
        params={"store_id": store_id},
        headers=base_headers,
    )
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert fetched["combo_promotions"][0]["id"] == "COM-12"

    sale_payload = {
        "store_id": store_id,
        "items": [
            {"device_id": device_ids[0], "quantity": 3},
            {"device_id": device_ids[1], "quantity": 1},
            {"device_id": device_ids[2], "quantity": 1},
            {"device_id": device_ids[3], "quantity": 1},
        ],
        "payment_method": "EFECTIVO",
        "confirm": True,
        "coupons": ["bienvenida"],
    }

    sale_response = client.post("/pos/sale", json=sale_payload, headers=base_headers)
    assert sale_response.status_code == 201, sale_response.text
    sale_body = sale_response.json()
    assert sale_body["status"] == "registered"
    applied = sale_body.get("applied_promotions", [])
    assert len(applied) >= 2
    types = {entry["promotion_type"] for entry in applied}
    assert {"volume", "combo", "coupon"}.issubset(types)
    total_discount = sum(Decimal(str(entry.get("discount_amount", 0))) for entry in applied)
    assert total_discount > Decimal("0")
