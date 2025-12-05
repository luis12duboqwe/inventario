from fastapi import status
from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN
from sqlalchemy import select


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "transfer_get_admin",
        "password": "Transfer123*",
        "full_name": "Transfer Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    # If user already exists, we just login

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_get_transfer_detail(client, db_session):
    previous_flag = settings.enable_transfers
    settings.enable_transfers = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}"}

        # Create stores
        origin = client.post(
            "/stores",
            json={"name": "Origin Store", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        destination = client.post(
            "/stores",
            json={"name": "Destination Store", "location": "MX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert origin.status_code == status.HTTP_201_CREATED
        assert destination.status_code == status.HTTP_201_CREATED
        origin_id = origin.json()["id"]
        destination_id = destination.json()["id"]

        # Memberships
        client.put(f"/stores/{origin_id}/memberships/{user_id}", json={"user_id": user_id,
                   "store_id": origin_id, "can_create_transfer": True, "can_receive_transfer": False}, headers=headers)
        client.put(f"/stores/{destination_id}/memberships/{user_id}", json={"user_id": user_id,
                   "store_id": destination_id, "can_create_transfer": False, "can_receive_transfer": True}, headers=headers)

        # Create device
        device = client.post(
            f"/stores/{origin_id}/devices",
            json={"sku": "TEST-SKU-123", "name": "Test Device", "quantity": 10,
                  "unit_price": 100, "costo_unitario": 50, "margen_porcentaje": 10},
            headers=headers,
        )
        assert device.status_code == status.HTTP_201_CREATED
        device_id = device.json()["id"]

        # Create transfer
        transfer = client.post(
            "/transfers",
            json={
                "origin_store_id": origin_id,
                "destination_store_id": destination_id,
                "reason": "Test Transfer",
                "items": [{"device_id": device_id, "quantity": 5}]
            },
            headers={**headers, "X-Reason": "Test Transfer"}
        )
        assert transfer.status_code == status.HTTP_201_CREATED
        transfer_id = transfer.json()["id"]

        # Test GET /transfers/{id}
        response = client.get(f"/transfers/{transfer_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == transfer_id
        assert data["origin_store_name"] == "Origin Store"
        assert data["destination_store_name"] == "Destination Store"
        assert len(data["items"]) == 1
        assert data["items"][0]["device_name"] == "Test Device"
        assert data["items"][0]["sku"] == "TEST-SKU-123"
        assert data["items"][0]["quantity"] == 5

    finally:
        settings.enable_transfers = previous_flag
