from __future__ import annotations

from pathlib import Path

from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client) -> str:
    payload = {
        "username": "pos_session_admin",
        "password": "PosSession123*",
        "full_name": "Admin Sesiones POS",
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
    return token_response.json()["access_token"]


def _create_store(client, headers: dict[str, str]) -> int:
    store_payload = {
        "name": "POS Centro Sesiones",
        "location": "CDMX",
        "timezone": "America/Mexico_City",
    }
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    return store_response.json()["id"]


def test_recover_cash_session_returns_open_session(client) -> None:
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Recuperar POS"}
    store_id = _create_store(client, headers)

    open_response = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 100.0},
        headers=headers,
    )
    assert open_response.status_code == status.HTTP_201_CREATED

    recovery_response = client.get(
        f"/pos/cash/recover?store_id={store_id}", headers=headers
    )
    assert recovery_response.status_code == status.HTTP_200_OK
    payload = recovery_response.json()
    assert payload["status"] == "ABIERTO"
    assert payload["branch_id"] == store_id
    settings.enable_purchases_sales = previous_flag


def test_cash_history_paginated_supports_metadata(client) -> None:
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Historial POS"}
    store_id = _create_store(client, headers)

    first_open = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 50},
        headers=headers,
    )
    assert first_open.status_code == status.HTTP_201_CREATED
    session_id = first_open.json()["id"]

    close_response = client.post(
        "/pos/cash/close",
        json={
            "session_id": session_id,
            "closing_amount": 50,
            "payment_breakdown": {"EFECTIVO": 50},
        },
        headers=headers,
    )
    assert close_response.status_code == status.HTTP_200_OK

    second_open = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 25},
        headers=headers,
    )
    assert second_open.status_code == status.HTTP_201_CREATED

    paginated = client.get(
        f"/pos/cash/history/paginated?store_id={store_id}&page=1&size=1",
        headers=headers,
    )
    assert paginated.status_code == status.HTTP_200_OK
    result = paginated.json()
    assert result["total"] >= 2
    assert result["page"] == 1
    assert result["size"] == 1
    assert len(result["items"]) == 1
    settings.enable_purchases_sales = previous_flag


def test_async_cash_report_job_runs_inline(client, tmp_path: Path) -> None:
    previous_flag = settings.enable_purchases_sales
    previous_logs_dir = settings.logs_directory
    settings.enable_purchases_sales = True
    settings.logs_directory = str(tmp_path)
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Exportar POS"}
    store_id = _create_store(client, headers)

    session_response = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 15},
        headers=headers,
    )
    assert session_response.status_code == status.HTTP_201_CREATED
    session_id = session_response.json()["id"]

    job_response = client.post(
        f"/pos/cash/register/{session_id}/report/async?run_inline=true",
        headers=headers,
    )
    assert job_response.status_code == status.HTTP_202_ACCEPTED
    job_payload = job_response.json()
    assert job_payload["status"] in {"running", "completed"}

    status_response = client.get(
        f"/pos/cash/report/jobs/{job_payload['id']}", headers=headers
    )
    assert status_response.status_code == status.HTTP_200_OK
    job_status = status_response.json()
    if job_status.get("output_path"):
        assert Path(job_status["output_path"]).exists()
    settings.enable_purchases_sales = previous_flag
    settings.logs_directory = previous_logs_dir
