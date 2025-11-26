from __future__ import annotations

from fastapi import status

from backend.app.config import settings

from .test_pos import _bootstrap_admin


def _auth_headers(client) -> dict[str, str]:
    token = _bootstrap_admin(client)
    return {"Authorization": f"Bearer {token}"}


def _reason_header(reason: str) -> dict[str, str]:
    return {"X-Reason": reason}


def test_pack34_pos_end_to_end(client, db_session):
    """Ejecuta el flujo solicitado para validar sesiones, venta y devolución POS."""

    # // [PACK34-test]
    settings.enable_purchases_sales = True
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal POS", "location": "GDL",
              "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    # // [PACK34-test]
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "PACK34-01",
            "name": "Smartphone POS",
            "quantity": 3,
            "unit_price": 150.0,
            "costo_unitario": 90.0,
            "imei": "353001159753462",
        },
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_data = device_response.json()
    device_id = device_data["id"]
    imei_value = device_data.get("imei") or "353001159753462"

    # // [PACK34-test]
    accessory_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "PACK34-ACC",
            "name": "Cargador POS",
            "quantity": 5,
            "unit_price": 25.5,
            "costo_unitario": 10.0,
        },
        headers=headers,
    )
    assert accessory_response.status_code == status.HTTP_201_CREATED
    accessory_id = accessory_response.json()["id"]

    open_response = client.post(
        "/pos/sessions/open",
        json={"branchId": store_id, "opening_amount": 500.0},
        headers={**headers, **_reason_header("Inicio jornada POS")},
    )
    assert open_response.status_code == status.HTTP_201_CREATED
    session_id = open_response.json()["session_id"]

    # // [PACK34-test]
    last_open_response = client.get(
        f"/pos/sessions/last?branchId={store_id}",
        headers={**headers, **_reason_header("Consultar ultima sesion")},
    )
    assert last_open_response.status_code == status.HTTP_200_OK
    last_open_data = last_open_response.json()
    assert last_open_data["session_id"] == session_id
    assert last_open_data["status"].upper() == "ABIERTO"

    sale_payload = {
        "branchId": store_id,
        "sessionId": session_id,
        "confirm": True,
        "items": [
            {
                "imei": imei_value,
                "qty": 1,
                "price": "219.99",
                "discount": 10.0,
            },
            {
                "productId": accessory_id,
                "qty": 1,
                "price": "25.50",
                "discount": 0.0,
            },
        ],
        "payments": [{"method": "EFECTIVO", "amount": 245.49}],
        "note": "Venta mostrador pack34",
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers={**headers, **_reason_header("Registrar venta POS")},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    assert sale_data["status"] == "registered"
    assert sale_data["receipt_pdf_base64"]
    assert sale_data.get("debt_summary") is None
    assert sale_data.get("payment_receipts") == []
    sale_id = sale_data["sale"]["id"]

    detail_response = client.get(
        f"/pos/sale/{sale_id}",
        headers={**headers, **_reason_header("Consultar venta POS")},
    )
    assert detail_response.status_code == status.HTTP_200_OK
    detail_data = detail_response.json()
    assert detail_data["sale"]["id"] == sale_id
    assert detail_data["receipt_pdf_base64"]
    assert detail_data.get("debt_summary") is None

    taxes_response = client.get(
        "/pos/taxes",
        headers={**headers, **_reason_header("Listar impuestos POS")},
    )
    assert taxes_response.status_code == status.HTTP_200_OK
    assert isinstance(taxes_response.json(), list)

    close_response = client.post(
        "/pos/sessions/close",
        json={
            "session_id": session_id,
            "closing_amount": 700.0,
            "payments": {"EFECTIVO": 199.99},
            "difference_reason": "Diferencia por fondo de cambio inicial no registrado",
        },
        headers={**headers, **_reason_header("Cerrar caja POS")},
    )
    assert close_response.status_code == status.HTTP_200_OK
    assert close_response.json()["status"] == "CERRADO"

    # // [PACK34-test]
    last_closed_response = client.get(
        f"/pos/sessions/last?branchId={store_id}",
        headers={**headers, **_reason_header("Consultar sesion cerrada")},
    )
    assert last_closed_response.status_code == status.HTTP_200_OK
    last_closed_data = last_closed_response.json()
    assert last_closed_data["session_id"] == session_id
    assert last_closed_data["status"].upper() == "CERRADO"

    return_payload = {
        "originalSaleId": sale_id,
        "reason": "Cliente devolvio equipo principal",
        "items": [{"imei": imei_value, "qty": 1}],
    }
    return_response = client.post(
        "/pos/return",
        json=return_payload,
        headers={**headers, **_reason_header("Registrar devolucion POS")},
    )
    assert return_response.status_code == status.HTTP_201_CREATED
    return_data = return_response.json()
    assert return_data["sale_id"] == sale_id
    assert isinstance(return_data["return_ids"],
                      list) and return_data["return_ids"]

    # // [PACK34-test]
    remaining_detail = client.get(
        f"/pos/sale/{sale_id}",
        headers={**headers, **
                 _reason_header("Consultar venta POS tras devolucion")},
    )
    assert remaining_detail.status_code == status.HTTP_200_OK
    remaining_items = remaining_detail.json()["sale"].get("items", [])
    assert len(remaining_items) >= 1
