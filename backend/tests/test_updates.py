import json

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


def test_update_status_and_history(client, tmp_path) -> None:
    headers = _auth_headers(client)

    feed_path = tmp_path / "releases.json"
    feed_data = {
        "producto": "Softmobile 2025",
        "releases": [
            {
                "version": "2.2.0",
                "release_date": "2025-02-01",
                "notes": "Versión estable",
                "download_url": "https://example.com/softmobile-2.2.0.exe",
            },
            {
                "version": "2.1.0",
                "release_date": "2024-11-10",
                "notes": "Actualización de auditoría",
                "download_url": "https://example.com/softmobile-2.1.0.exe",
            },
        ],
    }
    feed_path.write_text(json.dumps(feed_data), encoding="utf-8")

    original_feed = settings.update_feed_path
    original_version = settings.version
    settings.update_feed_path = str(feed_path)

    try:
        settings.version = "2.2.0"
        status_response = client.get("/updates/status", headers=headers)
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["current_version"] == "2.2.0"
        assert status_data["latest_version"] == "2.2.0"
        assert status_data["is_update_available"] is False

        history_response = client.get("/updates/history", headers=headers)
        assert history_response.status_code == status.HTTP_200_OK
        history = history_response.json()
        assert len(history) == 2
        assert history[0]["version"] == "2.2.0"

        settings.version = "2.1.0"
        update_response = client.get("/updates/status", headers=headers)
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["is_update_available"] is True
        assert update_data["latest_version"] == "2.2.0"
    finally:
        settings.update_feed_path = original_feed
        settings.version = original_version

