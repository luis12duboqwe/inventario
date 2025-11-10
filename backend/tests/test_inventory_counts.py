from fastapi import status

from backend.app import models
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client) -> dict[str, str]:
    payload = {
        "username": "counts_admin",
        "password": "ConteoSegur0*",
        "full_name": "Supervisor Inventario",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion inventario QA"}


def test_inventory_receiving_and_cycle_count(client) -> None:
    headers = _bootstrap_admin(client)

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Conteo", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-CYC-001",
        "name": "Equipo Conteo QA",
        "quantity": 2,
        "unit_price": 8999.0,
        "imei": "490154203237519",
        "serial": "SN-CYCLE-01",
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    receiving_payload = {
        "store_id": store_id,
        "note": "Recepción inventario QA",
        "responsible": "Jefe de almacén",
        "reference": "RCV-001",
        "lines": [
            {
                "imei": device_payload["imei"],
                "quantity": 1,
                "unit_cost": 8700.0,
            }
        ],
    }
    receiving_headers = {**headers, "X-Reason": receiving_payload["note"]}
    receiving_response = client.post(
        "/inventory/counts/receipts",
        json=receiving_payload,
        headers=receiving_headers,
    )
    assert receiving_response.status_code == status.HTTP_201_CREATED
    receiving_data = receiving_response.json()
    assert receiving_data["totals"]["lines"] == 1
    assert receiving_data["totals"]["total_quantity"] == 1
    movement_entry = receiving_data["processed"][0]["movement"]
    assert movement_entry["tipo_movimiento"] == "entrada"

    device_after_receiving = client.get(
        f"/stores/{store_id}/devices/{device_id}", headers=headers
    )
    assert device_after_receiving.status_code == status.HTTP_200_OK
    assert device_after_receiving.json()["quantity"] == 3

    cycle_payload = {
        "store_id": store_id,
        "note": "Conteo cíclico QA",
        "responsible": "Auditor interno",
        "reference": "CC-001",
        "lines": [
            {"imei": device_payload["imei"], "counted": 2},
        ],
    }
    cycle_headers = {**headers, "X-Reason": cycle_payload["note"]}
    cycle_response = client.post(
        "/inventory/counts/cycle",
        json=cycle_payload,
        headers=cycle_headers,
    )
    assert cycle_response.status_code == status.HTTP_201_CREATED
    cycle_data = cycle_response.json()
    assert cycle_data["totals"]["adjusted"] == 1
    discrepancy = cycle_data["adjustments"][0]
    assert discrepancy["expected"] == 3
    assert discrepancy["counted"] == 2
    assert discrepancy["delta"] == -1
    assert discrepancy["movement"]["tipo_movimiento"] == "ajuste"

    device_after_cycle = client.get(
        f"/stores/{store_id}/devices/{device_id}", headers=headers
    )
    assert device_after_cycle.status_code == status.HTTP_200_OK
    assert device_after_cycle.json()["quantity"] == 2

    export_headers = {**headers, "X-Reason": "Reporte ajustes QA"}
    csv_response = client.get(
        "/inventory/counts/adjustments/report",
        params={"format": "csv", "store_ids": store_id},
        headers=export_headers,
    )
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")

    pdf_response = client.get(
        "/inventory/counts/adjustments/report",
        params={"format": "pdf", "store_ids": store_id},
        headers=export_headers,
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"].startswith("application/pdf")

    audit_headers = {**headers, "X-Reason": "Reporte auditoria QA"}
    audit_csv = client.get(
        "/inventory/counts/audit/report",
        params={"format": "csv"},
        headers=audit_headers,
    )
    assert audit_csv.status_code == status.HTTP_200_OK
    assert audit_csv.headers["content-type"].startswith("text/csv")

    audit_pdf = client.get(
        "/inventory/counts/audit/report",
        params={"format": "pdf"},
        headers=audit_headers,
    )
    assert audit_pdf.status_code == status.HTTP_200_OK
    assert audit_pdf.headers["content-type"].startswith("application/pdf")


def test_inventory_receiving_auto_distribution(client, db_session) -> None:
    headers = _bootstrap_admin(client)

    central_response = client.post(
        "/stores",
        json={"name": "Almacén Central", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert central_response.status_code == status.HTTP_201_CREATED
    central_id = central_response.json()["id"]

    branch_response = client.post(
        "/stores",
        json={"name": "Sucursal Test", "location": "GDL", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert branch_response.status_code == status.HTTP_201_CREATED
    branch_id = branch_response.json()["id"]

    device_payload = {
        "sku": "SKU-DIST-001",
        "name": "Equipo Auto Distribución",
        "quantity": 0,
        "unit_price": 2500.0,
    }
    device_response = client.post(
        f"/stores/{central_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    receiving_payload = {
        "store_id": central_id,
        "note": "Recepción central con distribución",
        "responsible": "Coordinador",
        "reference": "RCV-DIST-001",
        "lines": [
            {
                "device_id": device_id,
                "quantity": 5,
                "unit_cost": 2100.0,
                "distributions": [
                    {"store_id": branch_id, "quantity": 3},
                ],
            }
        ],
    }
    receiving_headers = {**headers, "X-Reason": receiving_payload["note"]}
    response = client.post(
        "/inventory/counts/receipts",
        json=receiving_payload,
        headers=receiving_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["totals"]["total_quantity"] == 5
    assert data.get("auto_transfers")
    transfer = data["auto_transfers"][0]
    assert transfer["destination_store_id"] == branch_id
    assert transfer["origin_store_id"] == central_id
    assert transfer["status"] in {"EN_TRANSITO", "SOLICITADA"}
    assert transfer["items"][0]["device_id"] == device_id
    assert transfer["items"][0]["quantity"] == 3

    outbox_entries = (
        db_session.query(models.SyncOutbox)
        .filter(models.SyncOutbox.entity_type == "transfer_order")
        .all()
    )
    assert outbox_entries, "Debe registrarse una transferencia en la cola de sincronización"
    assert all(entry.priority == models.SyncOutboxPriority.HIGH for entry in outbox_entries)
