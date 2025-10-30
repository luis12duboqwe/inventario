"""Pruebas dedicadas a los flujos JWT de PACK28."""
from __future__ import annotations

from fastapi import status

# // [PACK28-tests]
REFRESH_COOKIE_NAME = "softmobile_refresh_token"


# // [PACK28-tests]
def _bootstrap_admin(client):
    payload = {
        "username": "pack28_admin@example.com",
        "password": "Pack28Segura!",
        "full_name": "Pack28 Admin",
        "roles": ["ADMIN"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return payload


# // [PACK28-tests]
def test_login_sets_refresh_cookie_and_returns_token(client):
    credentials = _bootstrap_admin(client)
    login_response = client.post(
        "/auth/login",
        json={"username": credentials["username"], "password": credentials["password"]},
    )
    assert login_response.status_code == status.HTTP_200_OK
    body = login_response.json()
    assert "access_token" in body and body["token_type"] == "bearer"
    assert login_response.cookies.get(REFRESH_COOKIE_NAME) is not None

    profile_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert profile_response.status_code == status.HTTP_200_OK
    profile = profile_response.json()
    assert profile["email"] == credentials["username"]
    assert profile["role"] == "ADMIN"
    assert profile["name"] == "Pack28 Admin"


# // [PACK28-tests]
def test_refresh_renews_access_token(client):
    credentials = _bootstrap_admin(client)
    login_response = client.post(
        "/auth/login",
        json={"username": credentials["username"], "password": credentials["password"]},
    )
    assert login_response.status_code == status.HTTP_200_OK
    first_token = login_response.json()["access_token"]

    refresh_response = client.post("/auth/refresh")
    assert refresh_response.status_code == status.HTTP_200_OK
    renewed_token = refresh_response.json()["access_token"]
    assert renewed_token != first_token

    profile_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {renewed_token}"},
    )
    assert profile_response.status_code == status.HTTP_200_OK
    assert profile_response.json()["role"] == "ADMIN"


# // [PACK28-tests]
def test_refresh_requires_cookie(client):
    response = client.post("/auth/refresh")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Token de refresco ausente."


def test_logout_revokes_refresh_cookie(client):
    credentials = _bootstrap_admin(client)
    login_response = client.post(
        "/auth/login",
        json={"username": credentials["username"], "password": credentials["password"]},
    )
    assert login_response.status_code == status.HTTP_200_OK
    assert login_response.cookies.get(REFRESH_COOKIE_NAME) is not None

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT
    assert logout_response.cookies.get(REFRESH_COOKIE_NAME) is None

    refresh_response = client.post("/auth/refresh")
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.json()["detail"] in {
        "Token de refresco ausente.",
        "Sesión expirada o revocada.",
    }
