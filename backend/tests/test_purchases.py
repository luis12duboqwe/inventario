import json
from decimal import Decimal
from typing import Any, Iterable

from fastapi import status
from sqlalchemy import select, text

import tempfile

from backend.app import crud, models
from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.services import purchase_documents


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "compras_admin",
        "password": "Compras123*",
        "full_name": "Compras Admin",
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


def _create_store(client, headers):
    response = client.post(
        "/stores",
        json={"name": "Compras Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(client, store_id: int, headers):
    device_payload = {
        "sku": "SKU-COMP-001",
        "name": "Smartphone corporativo",
        "quantity": 10,
        "unit_price": 1500.0,
        "costo_unitario": 1000.0,
        "margen_porcentaje": 15.0,
    }
    response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_get_purchase_order_detail_includes_items_and_returns(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}"}
    headers_with_reason = {**base_headers, "X-Reason": "Operación compras"}

    try:
        store_id = _create_store(client, headers_with_reason)
        device_id = _create_device(client, store_id, headers_with_reason)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Mayorista",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 6, "unit_cost": 820.0},
                ],
            },
            headers=headers_with_reason,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 4}]},
            headers={**base_headers, "X-Reason": "Recepción parcial"},
        )
        assert receive_response.status_code == status.HTTP_200_OK

        return_response = client.post(
            f"/purchases/{order_id}/returns",
            json={"device_id": device_id, "quantity": 1, "reason": "Equipo defectuoso"},
            headers={**base_headers, "X-Reason": "Devolución proveedor"},
        )
        assert return_response.status_code == status.HTTP_200_OK

        detail_response = client.get(f"/purchases/{order_id}", headers=base_headers)
        assert detail_response.status_code == status.HTTP_200_OK
        payload = detail_response.json()

        assert payload["id"] == order_id
        assert payload["supplier"] == "Proveedor Mayorista"
        assert payload["items"], "La respuesta debe incluir artículos"
        assert payload["items"][0]["quantity_ordered"] == 6
        assert payload["items"][0]["quantity_received"] == 4
        assert payload["returns"]
        assert payload["returns"][0]["quantity"] == 1
        assert payload["returns"][0]["reason"] == "Equipo defectuoso"
        assert payload["returns"][0]["disposition"] == "defectuoso"
        assert payload["returns"][0]["warehouse_id"] is None
    finally:
        settings.enable_purchases_sales = previous_flag


def test_get_purchase_order_not_found_returns_404(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}"}
    try:
        response = client.get("/purchases/999999", headers=base_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_receipt_and_return_flow(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operacion de compra"}

    try:
        store_response = client.post(
            "/stores",
            json={"name": "Compras Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_payload = {
            "sku": "SKU-COMP-001",
            "name": "Smartphone corporativo",
            "quantity": 10,
            "unit_price": 1500.0,
            "costo_unitario": 1000.0,
            "margen_porcentaje": 15.0,
        }
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        order_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Mayorista",
            "items": [
                {"device_id": device_id, "quantity_ordered": 10, "unit_cost": 850.0},
            ],
        }
        order_response = client.post("/purchases", json=order_payload, headers=auth_headers)
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        partial_receive = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 5}]},
            headers={**auth_headers, "X-Reason": "Recepcion parcial"},
        )
        assert partial_receive.status_code == status.HTTP_200_OK
        partial_data = partial_receive.json()
        assert partial_data["status"] == "PARCIAL"

        devices_after_partial = client.get(
            f"/stores/{store_id}/devices", headers=auth_headers
        )
        assert devices_after_partial.status_code == status.HTTP_200_OK
        stored_device = next(
            item
            for item in _extract_items(devices_after_partial.json())
            if item["id"] == device_id
        )
        assert stored_device["quantity"] == 15
        assert Decimal(str(stored_device["costo_unitario"])) == Decimal("950.00")

        complete_receive = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 5}]},
            headers={**auth_headers, "X-Reason": "Recepcion final"},
        )
        assert complete_receive.status_code == status.HTTP_200_OK
        assert complete_receive.json()["status"] == "COMPLETADA"

        return_response = client.post(
            f"/purchases/{order_id}/returns",
            json={"device_id": device_id, "quantity": 2, "reason": "Equipo danado"},
            headers={**auth_headers, "X-Reason": "Devolucion proveedor"},
        )
        assert return_response.status_code == status.HTTP_200_OK

        inventory_after_return = client.get(
            f"/stores/{store_id}/devices", headers=auth_headers
        )
        assert inventory_after_return.status_code == status.HTTP_200_OK
        device_post_return = next(
            item
            for item in _extract_items(inventory_after_return.json())
            if item["id"] == device_id
        )
        assert device_post_return["quantity"] == 18

        movements = list(
            db_session.execute(
                select(models.InventoryMovement)
                .where(models.InventoryMovement.device_id == device_id)
                .order_by(models.InventoryMovement.created_at)
            ).scalars()
        )
        assert len(movements) == 3
        received_movements = [m for m in movements if m.movement_type == models.MovementType.IN]
        assert {movement.quantity for movement in received_movements} == {5}
        for movement in received_movements:
            assert movement.performed_by_id == user_id
            assert movement.comment is not None and "Proveedor Mayorista" in movement.comment
            assert "Recepción OC" in movement.comment
        return_movement = next(m for m in movements if m.movement_type == models.MovementType.OUT)
        assert return_movement.quantity == 2
        assert return_movement.performed_by_id == user_id
        assert "Devolución proveedor" in return_movement.comment
        assert "Proveedor Mayorista" in return_movement.comment

        legacy_rows = db_session.execute(
            text(
                """
                SELECT tipo_movimiento, cantidad, comentario, usuario_id
                FROM movimientos_inventario
                WHERE producto_id = :device_id
                ORDER BY fecha
                """
            ),
            {"device_id": device_id},
        ).mappings().all()
        assert len(legacy_rows) == len(movements)
        assert {row["tipo_movimiento"] for row in legacy_rows} == {
            movement.movement_type.value for movement in movements
        }
        assert all(row["usuario_id"] == user_id for row in legacy_rows)
        assert any("Proveedor Mayorista" in row["comentario"] for row in legacy_rows)

        settings.enable_purchases_sales = False
        disabled_list = client.get("/purchases/vendors", headers=auth_headers)
        assert disabled_list.status_code == status.HTTP_404_NOT_FOUND

        disabled_create = client.post(
            "/purchases",
            json=order_payload,
            headers=auth_headers,
        )
        assert disabled_create.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = previous_flag


def test_large_purchase_requires_approval_before_receiving(client, db_session):
    previous_flag = settings.enable_purchases_sales
    previous_threshold = settings.purchases_large_order_threshold
    settings.enable_purchases_sales = True
    settings.purchases_large_order_threshold = Decimal("1000")
    token, user_id = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}
    headers_with_reason = {**headers, "X-Reason": "Compra mayor"}

    try:
        store_id = _create_store(client, headers_with_reason)
        device_id = _create_device(client, store_id, headers_with_reason)

        order_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Mayorista",
            "items": [
                {"device_id": device_id, "quantity_ordered": 10, "unit_cost": 150.0},
            ],
        }
        order_response = client.post(
            "/purchases", json=order_payload, headers=headers_with_reason
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_data = order_response.json()
        assert order_data["requires_approval"] is True

        receive_response = client.post(
            f"/purchases/{order_data['id']}/receive",
            json={"items": [{"device_id": device_id, "quantity": 2}]},
            headers=headers_with_reason,
        )
        assert receive_response.status_code == status.HTTP_409_CONFLICT

        approval_response = client.post(
            f"/purchases/{order_data['id']}/status",
            json={"status": "APROBADA"},
            headers=headers,
        )
        assert approval_response.status_code == status.HTTP_200_OK
        assert approval_response.json()["approved_by_id"] == user_id

        received_after_approval = client.post(
            f"/purchases/{order_data['id']}/receive",
            json={"items": [{"device_id": device_id, "quantity": 2}]},
            headers=headers_with_reason,
        )
        assert received_after_approval.status_code == status.HTTP_200_OK
        assert received_after_approval.json()["status"] == "PARCIAL"
        assert received_after_approval.json()["pending_items"] == 8
    finally:
        settings.enable_purchases_sales = previous_flag
        settings.purchases_large_order_threshold = previous_threshold


def test_purchase_completes_after_covering_pending_items(client, db_session):
    previous_flag = settings.enable_purchases_sales
    previous_threshold = settings.purchases_large_order_threshold
    settings.enable_purchases_sales = True
    settings.purchases_large_order_threshold = Decimal("0")
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}
    headers_with_reason = {**headers, "X-Reason": "Recepcion escalonada"}

    try:
        store_id = _create_store(client, headers_with_reason)
        device_id = _create_device(client, store_id, headers_with_reason)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Parcial",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 4, "unit_cost": 90.0},
                ],
            },
            headers=headers_with_reason,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        first_receive = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 2}]},
            headers=headers_with_reason,
        )
        assert first_receive.status_code == status.HTTP_200_OK
        assert first_receive.json()["status"] == "PARCIAL"
        assert first_receive.json()["pending_items"] == 2

        second_receive = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 2}]},
            headers=headers_with_reason,
        )
        assert second_receive.status_code == status.HTTP_200_OK
        assert second_receive.json()["status"] == "COMPLETADA"
        assert second_receive.json()["pending_items"] == 0

        devices_after = client.get(f"/stores/{store_id}/devices", headers=headers)
        assert devices_after.status_code == status.HTTP_200_OK
        stored_device = next(
            item for item in _extract_items(devices_after.json()) if item["id"] == device_id
        )
        assert stored_device["quantity"] >= 14
    finally:
        settings.enable_purchases_sales = previous_flag
        settings.purchases_large_order_threshold = previous_threshold


def test_upload_purchase_order_document_and_download(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación compras"}

    previous_backend = settings.purchases_documents_backend
    previous_path = settings.purchases_documents_local_path
    purchase_documents.get_storage.cache_clear()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            settings.purchases_documents_backend = "local"
            settings.purchases_documents_local_path = tmpdir
            purchase_documents.get_storage.cache_clear()

            store_id = _create_store(client, base_headers)
            device_id = _create_device(client, store_id, base_headers)

            order_response = client.post(
                "/purchases",
                json={
                    "store_id": store_id,
                    "supplier": "Proveedor Mayorista",
                    "items": [
                        {"device_id": device_id, "quantity_ordered": 3, "unit_cost": 720.0},
                    ],
                },
                headers=base_headers,
            )
            assert order_response.status_code == status.HTTP_201_CREATED
            order_id = order_response.json()["id"]

            pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            upload_response = client.post(
                f"/purchases/{order_id}/documents",
                files={"file": ("orden.pdf", pdf_bytes, "application/pdf")},
                headers=base_headers,
            )
            assert upload_response.status_code == status.HTTP_201_CREATED
            document_payload = upload_response.json()
            assert document_payload["filename"] == "orden.pdf"
            assert document_payload["download_url"].endswith(
                f"/purchases/{order_id}/documents/{document_payload['id']}"
            )

            detail_response = client.get(
                f"/purchases/{order_id}", headers={"Authorization": f"Bearer {token}"}
            )
            assert detail_response.status_code == status.HTTP_200_OK
            detail_payload = detail_response.json()
            assert detail_payload["documents"], "La orden debe incluir adjuntos"
            fetched_document = detail_payload["documents"][0]
            assert fetched_document["filename"] == "orden.pdf"
            assert fetched_document["download_url"].endswith(
                f"/purchases/{order_id}/documents/{document_payload['id']}"
            )

            download_response = client.get(
                f"/purchases/{order_id}/documents/{document_payload['id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert download_response.status_code == status.HTTP_200_OK
            assert download_response.content == pdf_bytes
    finally:
        purchase_documents.get_storage.cache_clear()
        settings.purchases_documents_backend = previous_backend
        settings.purchases_documents_local_path = previous_path
        settings.enable_purchases_sales = previous_flag


def test_purchase_status_transition_records_history(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación compras"}

    try:
        store_id = _create_store(client, base_headers)
        device_id = _create_device(client, store_id, base_headers)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Corporativo",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 2, "unit_cost": 680.0},
                ],
            },
            headers=base_headers,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        transition_response = client.post(
            f"/purchases/{order_id}/status",
            json={"status": "APROBADA"},
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Aprobación de orden"},
        )
        assert transition_response.status_code == status.HTTP_200_OK
        payload = transition_response.json()
        assert payload["status"] == "APROBADA"
        statuses = [event["status"] for event in payload["status_history"]]
        assert "APROBADA" in statuses
        approval_event = next(
            event for event in payload["status_history"] if event["status"] == "APROBADA"
        )
        assert approval_event["note"] == "Aprobación de orden"
        assert approval_event["created_by_name"] == "Compras Admin"

        conflict_response = client.post(
            f"/purchases/{order_id}/status",
            json={"status": "APROBADA"},
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Aprobación duplicada"},
        )
        assert conflict_response.status_code == status.HTTP_409_CONFLICT
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_status_transition_rejects_invalid_status(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación compras"}

    try:
        store_id = _create_store(client, base_headers)
        device_id = _create_device(client, store_id, base_headers)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Corporativo",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 2, "unit_cost": 680.0},
                ],
            },
            headers=base_headers,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        invalid_response = client.post(
            f"/purchases/{order_id}/status",
            json={"status": "CANCELADA"},
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Cancelación manual"},
        )
        assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert invalid_response.json()["detail"] == "Estado de orden inválido."
    finally:
        settings.enable_purchases_sales = previous_flag


def test_send_purchase_order_email_uses_notification_service(client, db_session, monkeypatch):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación compras"}

    captured: dict[str, object] = {}

    def fake_send_purchase_order_email(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(crud.purchase_documents, "send_purchase_order_email", fake_send_purchase_order_email)

    try:
        store_id = _create_store(client, base_headers)
        device_id = _create_device(client, store_id, base_headers)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Corporativo",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 1, "unit_cost": 500.0},
                ],
            },
            headers=base_headers,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        send_response = client.post(
            f"/purchases/{order_id}/send",
            json={
                "recipients": ["compras@example.com"],
                "message": "Adjuntamos la orden",
                "include_documents": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert send_response.status_code == status.HTTP_200_OK
        assert captured["order"].id == order_id
        assert captured["recipients"] == ["compras@example.com"]
        assert captured["message"] == "Adjuntamos la orden"
        assert captured["include_documents"] is True
    finally:
        settings.enable_purchases_sales = previous_flag


def test_upload_purchase_order_document_handles_storage_errors(client, db_session, monkeypatch):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación compras"}

    class _FailingStorage(purchase_documents.PurchaseDocumentStorage):
        backend_name = "failing"

        def save(self, *, filename: str, content_type: str, content: bytes):
            raise purchase_documents.PurchaseDocumentStorageError("forced_error")

        def open(self, path: str) -> bytes:  # pragma: no cover - no se usa
            raise NotImplementedError

        def delete(self, path: str) -> None:  # pragma: no cover - no se usa
            return None

    monkeypatch.setattr(crud.purchase_documents, "get_storage", lambda: _FailingStorage())

    try:
        store_id = _create_store(client, base_headers)
        device_id = _create_device(client, store_id, base_headers)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Mayorista",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 3, "unit_cost": 720.0},
                ],
            },
            headers=base_headers,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        upload_response = client.post(
            f"/purchases/{order_id}/documents",
            files={"file": ("orden.pdf", pdf_bytes, "application/pdf")},
            headers=base_headers,
        )
        assert upload_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert (
            upload_response.json()["detail"]
            == "No fue posible almacenar el documento adjunto."
        )
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_audit_logs_include_reason(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**base_headers, "X-Reason": "Auditoria compras"}

    try:
        store_id = _create_store(client, reason_headers)
        device_id = _create_device(client, store_id, reason_headers)

        order_response = client.post(
            "/purchases",
            json={
                "store_id": store_id,
                "supplier": "Proveedor Auditado",
                "items": [
                    {"device_id": device_id, "quantity_ordered": 3, "unit_cost": 780.0},
                ],
            },
            headers=reason_headers,
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        receive_reason = "Recepcion auditada"
        receive_headers = {**base_headers, "X-Reason": receive_reason}
        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 2}]},
            headers=receive_headers,
        )
        assert receive_response.status_code == status.HTTP_200_OK

        received_log = db_session.execute(
            select(models.AuditLog)
            .where(
                models.AuditLog.action == "purchase_order_received",
                models.AuditLog.entity_type == "purchase_order",
                models.AuditLog.entity_id == str(order_id),
            )
            .order_by(models.AuditLog.created_at.desc())
        ).scalars().first()
        assert received_log is not None
        received_details = json.loads(received_log.details)
        assert received_details["reason"] == receive_reason

        return_headers = {**base_headers, "X-Reason": "Reingreso auditado"}
        return_payload = {
            "device_id": device_id,
            "quantity": 1,
            "reason": "Equipo defectuoso",
        }
        return_response = client.post(
            f"/purchases/{order_id}/returns",
            json=return_payload,
            headers=return_headers,
        )
        assert return_response.status_code == status.HTTP_200_OK

        return_log = db_session.execute(
            select(models.AuditLog)
            .where(
                models.AuditLog.action == "purchase_return_registered",
                models.AuditLog.entity_type == "purchase_order",
                models.AuditLog.entity_id == str(order_id),
            )
            .order_by(models.AuditLog.created_at.desc())
        ).scalars().first()
        assert return_log is not None
        return_details = json.loads(return_log.details)
        assert return_details["return_reason"] == return_payload["reason"]
        assert return_details["request_reason"] == return_headers["X-Reason"]
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_cancellation_reverts_inventory_and_records_movement(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Motivo compras"}

    try:
        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Serial", "location": "GDL", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-SERIAL-01",
                "name": "Equipo con serie",
                "quantity": 0,
                "unit_price": 2500.0,
                "costo_unitario": 2000.0,
                "margen_porcentaje": 10.0,
                "serial": "SERIE-UNICA-001",
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        order_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Serializado",
            "items": [
                {"device_id": device_id, "quantity_ordered": 1, "unit_cost": 1800.0},
            ],
        }
        order_response = client.post("/purchases", json=order_payload, headers=auth_headers)
        assert order_response.status_code == status.HTTP_201_CREATED
        order_id = order_response.json()["id"]

        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 1}]},
            headers={**auth_headers, "X-Reason": "Recepcion serial"},
        )
        assert receive_response.status_code == status.HTTP_200_OK

        device_record = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        assert device_record.quantity == 1

        cancel_response = client.post(
            f"/purchases/{order_id}/cancel",
            headers={**auth_headers, "X-Reason": "Proveedor cancela"},
        )
        assert cancel_response.status_code == status.HTTP_200_OK
        assert cancel_response.json()["status"] == "CANCELADA"

        updated_device = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        assert updated_device.quantity == 0
        assert Decimal(str(updated_device.costo_unitario)) == Decimal("0.00")

        movements = list(
            db_session.execute(
                select(models.InventoryMovement)
                .where(models.InventoryMovement.device_id == device_id)
                .order_by(models.InventoryMovement.created_at)
            ).scalars()
        )
        assert len(movements) == 2
        reversal = next(m for m in movements if m.movement_type == models.MovementType.OUT)
        assert reversal.quantity == 1
        assert reversal.performed_by_id == user_id
        assert "Reversión OC" in reversal.comment
        assert "Proveedor Serializado" in reversal.comment
        assert "Serie: SERIE-UNICA-001" in reversal.comment

        settings.enable_purchases_sales = False
        disabled_receive = client.post(
            f"/purchases/{order_id}/receive",
            json={"items": [{"device_id": device_id, "quantity": 1}]},
            headers=auth_headers,
        )
        assert disabled_receive.status_code == status.HTTP_404_NOT_FOUND

        disabled_cancel = client.post(
            f"/purchases/{order_id}/cancel",
            headers=auth_headers,
        )
        assert disabled_cancel.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_records_and_vendor_statistics(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    base_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Gestion compras"}

    try:
        vendor_response = client.post(
            "/purchases/vendors",
            json={
                "nombre": "Proveedor Integrado",
                "telefono": "555-0101",
                "correo": "ventas@integrado.mx",
                "direccion": "Av. Central 101",
                "tipo": "Mayorista",
            },
            headers=base_headers,
        )
        assert vendor_response.status_code == status.HTTP_201_CREATED
        vendor_id = vendor_response.json()["id_proveedor"]

        store_response = client.post(
            "/stores",
            json={"name": "Compras Norte", "location": "MTY", "timezone": "America/Mexico_City"},
            headers=base_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "PRC-001",
                "name": "Equipo corporativo",
                "quantity": 5,
                "unit_price": 1500.0,
                "costo_unitario": 900.0,
                "margen_porcentaje": 20.0,
            },
            headers=base_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        record_payload = {
            "proveedor_id": vendor_id,
            "forma_pago": "TRANSFERENCIA",
            "impuesto_tasa": 0.16,
            "items": [
                {"producto_id": device_id, "cantidad": 3, "costo_unitario": 850.0},
                {"producto_id": device_id, "cantidad": 1, "costo_unitario": 800.0},
            ],
        }
        record_response = client.post(
            "/purchases/records",
            json=record_payload,
            headers=base_headers,
        )
        assert record_response.status_code == status.HTTP_201_CREATED
        record = record_response.json()
        assert record["proveedor_id"] == vendor_id
        assert Decimal(str(record["total"])) > Decimal(str(record["subtotal"]))
        assert len(record["items"]) == 2

        list_response = client.get(
            "/purchases/records",
            params={"proveedor_id": vendor_id, "limit": 200, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == status.HTTP_200_OK
        listed_payload = _extract_items(list_response.json())
        assert any(entry["id_compra"] == record["id_compra"] for entry in listed_payload)

        history_response = client.get(
            f"/purchases/vendors/{vendor_id}/history",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 200, "offset": 0},
        )
        assert history_response.status_code == status.HTTP_200_OK
        history_payload = history_response.json()
        assert history_payload["proveedor"]["id_proveedor"] == vendor_id
        assert history_payload["registros"] >= 1

        csv_response = client.get(
            "/purchases/vendors/export/csv",
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte proveedores"},
        )
        assert csv_response.status_code == status.HTTP_200_OK
        assert csv_response.headers["content-type"] == "text/csv"

        pdf_response = client.get(
            "/purchases/records/export/pdf",
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte compras"},
        )
        assert pdf_response.status_code == status.HTTP_200_OK
        assert pdf_response.headers["content-type"] == "application/pdf"

        excel_response = client.get(
            "/purchases/records/export/xlsx",
            headers={"Authorization": f"Bearer {token}", "X-Reason": "Reporte compras"},
        )
        assert excel_response.status_code == status.HTTP_200_OK
        assert (
            excel_response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        stats_response = client.get(
            "/purchases/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert stats_response.status_code == status.HTTP_200_OK
        stats_payload = stats_response.json()
        assert stats_payload["compras_registradas"] >= 1
        assert stats_payload["total"] >= float(record["total"])

        status_response = client.post(
            f"/purchases/vendors/{vendor_id}/status",
            json={"estado": "inactivo"},
            headers=base_headers,
        )
        assert status_response.status_code == status.HTTP_200_OK
        assert status_response.json()["estado"].lower() == "inactivo"

        settings.enable_purchases_sales = False
        disabled_records = client.get(
            "/purchases/records",
            params={"proveedor_id": vendor_id, "limit": 200, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disabled_records.status_code == status.HTTP_404_NOT_FOUND

        disabled_stats = client.get(
            "/purchases/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disabled_stats.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = previous_flag
