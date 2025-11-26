from fastapi import status

from backend.app import models


def _admin_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
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
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Reason": "Prueba de borrado logico"}


def test_soft_delete_store_preserves_inventory(client, db_session):
    headers = _admin_headers(client)
    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-001", "name": "Galaxy S24", "quantity": 2, "unit_price": 12000.0}
    create_device_response = client.post(
        f"/stores/{store_id}/devices", json=device_payload, headers=headers
    )
    assert create_device_response.status_code == status.HTTP_201_CREATED

    delete_response = client.delete(f"/stores/{store_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/stores/{store_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

    blocked_device_response = client.post(
        f"/stores/{store_id}/devices", json=device_payload, headers=headers
    )
    assert blocked_device_response.status_code == status.HTTP_404_NOT_FOUND

    store = db_session.get(models.Store, store_id)
    assert store is not None
    assert store.is_deleted is True
    assert store.deleted_at is not None

    device_count = db_session.query(models.Device).filter_by(store_id=store_id).count()
    assert device_count == 1


def test_soft_delete_user_blocks_access(client, db_session):
    headers = _admin_headers(client)
    user_payload = {
        "username": "usuario_pruebas",
        "password": "ClaveSegura123*",
        "full_name": "Usuario Temporal",
        "roles": ["OPERADOR"],
    }
    user_response = client.post("/users", json=user_payload, headers=headers)
    assert user_response.status_code == status.HTTP_201_CREATED
    user_id = user_response.json()["id"]

    delete_response = client.delete(f"/users/{user_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    login_response = client.post(
        "/auth/token",
        data={"username": user_payload["username"], "password": user_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

    update_status_response = client.patch(
        f"/users/{user_id}", json={"is_active": True}, headers=headers
    )
    assert update_status_response.status_code == status.HTTP_404_NOT_FOUND

    user = db_session.get(models.User, user_id)
    assert user is not None
    assert user.is_deleted is True
    assert user.is_active is False
    assert user.estado == "DESACTIVADO"
