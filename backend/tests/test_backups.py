from pathlib import Path

from fastapi import status

from backend.app.config import settings


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
        "roles": ["admin"],
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
    return {"Authorization": f"Bearer {token}"}


def test_backup_generation_and_pdf(client, tmp_path) -> None:
    headers = _auth_headers(client)
    settings.backup_directory = str(tmp_path / "respaldos")

    store_payload = {"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-XYZ", "name": "iPhone 15", "quantity": 3, "unit_price": 18999.99}
    device_payload = {"sku": "SKU-XYZ", "name": "iPhone 15", "quantity": 3}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED

    backup_response = client.post("/backups/run", json={"nota": "Respaldo QA"}, headers=headers)
    assert backup_response.status_code == status.HTTP_201_CREATED
    backup_data = backup_response.json()

    pdf_path = Path(backup_data["pdf_path"])
    archive_path = Path(backup_data["archive_path"])
    assert pdf_path.exists()
    assert archive_path.exists()
    assert backup_data["total_size_bytes"] == pdf_path.stat().st_size + archive_path.stat().st_size

    history_response = client.get("/backups/history", headers=headers)
    assert history_response.status_code == status.HTTP_200_OK
    history = history_response.json()
    assert history
    assert history[0]["notes"] == "Respaldo QA"

    pdf_response = client.get("/reports/inventory/pdf", headers=headers)
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
