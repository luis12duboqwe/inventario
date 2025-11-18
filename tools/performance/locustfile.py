"""Escenarios de carga pico para Softmobile POS usando Locust."""
from __future__ import annotations

import os
import random
from typing import Any

from locust import HttpUser, between, task

API_BASE = os.getenv("SOFTMOBILE_API_BASE", "http://localhost:8000")
AUTH_TOKEN = os.getenv("SOFTMOBILE_TOKEN", "")
STORE_ID = int(os.getenv("SOFTMOBILE_STORE_ID", "1"))
CUSTOMER_ID = os.getenv("SOFTMOBILE_CUSTOMER_ID")
REASON = os.getenv("SOFTMOBILE_REASON", "Carga pico QA")


class POSPeakUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:  # pragma: no cover - ejercido por Locust
        self.client.base_url = API_BASE

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"X-Reason": REASON}
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
        return headers

    @task(3)
    def list_inventory_paginated(self) -> None:
        params = {"page": 1, "size": 50, "store_id": STORE_ID}
        self.client.get("/inventory/devices", params=params, headers=self._headers)

    @task(2)
    def fetch_pos_config(self) -> None:
        self.client.get(f"/pos/config?store_id={STORE_ID}", headers=self._headers)

    @task(2)
    def paginated_cash_history(self) -> None:
        page = random.randint(1, 3)
        size = random.choice([10, 25, 50])
        params = {"store_id": STORE_ID, "page": page, "size": size}
        self.client.get("/pos/cash/history/paginated", params=params, headers=self._headers)

    @task(1)
    def recover_pos_session(self) -> None:
        self.client.get(f"/pos/cash/recover?store_id={STORE_ID}", headers=self._headers)

    @task(1)
    def warm_receipts_async(self) -> None:
        session_id = int(os.getenv("SOFTMOBILE_SESSION_ID", "1"))
        params = {"run_inline": "false"}
        self.client.post(
            f"/pos/cash/register/{session_id}/report/async",
            params=params,
            headers=self._headers,
        )

    @task(1)
    def lightweight_sale_draft(self) -> None:
        payload: dict[str, Any] = {
            "store_id": STORE_ID,
            "save_as_draft": True,
            "items": [
                {
                    "device_id": int(os.getenv("SOFTMOBILE_DEVICE_ID", "1")),
                    "quantity": 1,
                    "unit_price": "10.00",
                }
            ],
        }
        if CUSTOMER_ID:
            payload["customer_id"] = int(CUSTOMER_ID)
        self.client.post("/pos/sale", json=payload, headers=self._headers)
