"""Pruebas unitarias para el proveedor de sesiones en sincronización."""
from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from backend.app import models
from backend.app.core import SessionProvider
from backend.app.services import scheduler as scheduler_service
from backend.app.services import sync as sync_service


class FakeManagedSession:
    """Sesión simulada que implementa el protocolo de contexto."""

    def __init__(self) -> None:
        self.closed = False
        self.data: dict[str, Any] = {}

    def __enter__(self) -> "FakeManagedSession":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.closed = True


def _build_provider(registry: list[FakeManagedSession]) -> SessionProvider:
    def _factory() -> FakeManagedSession:
        session = FakeManagedSession()
        registry.append(session)
        return session

    return _factory


@pytest.fixture
def fake_entries() -> list[Any]:
    return [
        SimpleNamespace(
            id=1,
            status=models.SyncOutboxStatus.PENDING,
            payload="{\"store_id\": 5}",
        )
    ]


def test_run_sync_cycle_with_fake_provider(monkeypatch: pytest.MonkeyPatch, fake_entries: list[Any]) -> None:
    """Valida que run_sync_cycle utilice la sesión proporcionada y retorne métricas."""

    sessions: list[FakeManagedSession] = []
    provider = _build_provider(sessions)
    fake_session = provider()

    def fake_list_sync_outbox(db: Any, *, statuses: Any, limit: int) -> list[Any]:
        assert db is fake_session
        assert statuses == (models.SyncOutboxStatus.PENDING,)
        assert limit == 500
        return fake_entries

    processed_ids: list[int] = []

    def fake_mark_outbox_entries_sent(db: Any, ids: Callable[[], Any], *, performed_by_id: int | None) -> list[Any]:
        assert db is fake_session
        processed = list(ids)
        processed_ids.extend(processed)
        assert performed_by_id == 7
        return fake_entries

    fake_discrepancies = [{"sku": "SKU-1"}]

    monkeypatch.setattr(sync_service.crud, "list_sync_outbox", fake_list_sync_outbox, raising=True)
    monkeypatch.setattr(sync_service.crud, "mark_outbox_entries_sent", fake_mark_outbox_entries_sent, raising=True)
    monkeypatch.setattr(sync_service.crud, "log_sync_discrepancies", lambda db, discrepancies, performed_by_id=None: None, raising=True)
    monkeypatch.setattr(sync_service, "detect_inventory_discrepancies", lambda db: fake_discrepancies, raising=True)

    result = sync_service.run_sync_cycle(
        fake_session,
        store_id=5,
        performed_by_id=7,
    )

    assert result == {"processed": 1, "discrepancies": fake_discrepancies}
    assert processed_ids == [1]


def test_sync_job_uses_injected_session_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comprueba que _sync_job solicite la sesión mediante el proveedor inyectado."""

    sessions: list[FakeManagedSession] = []
    provider = _build_provider(sessions)

    monkeypatch.setattr(
        scheduler_service.sync_service,
        "requeue_failed_outbox_entries",
        lambda session: [],
        raising=True,
    )

    def fake_run_sync_cycle(session: FakeManagedSession, performed_by_id: int | None = None) -> dict[str, Any]:
        session.data["cycle"] = True
        return {"processed": 2, "discrepancies": [{"id": 99}, {"id": 100}]}

    recorded_payload: dict[str, Any] = {}

    def fake_record_sync_session(
        session: FakeManagedSession,
        *,
        store_id: int | None,
        mode: models.SyncMode,
        status: models.SyncStatus,
        triggered_by_id: int | None,
        error_message: str | None,
        processed_events: int,
        differences_detected: int,
    ) -> None:
        recorded_payload.update(
            {
                "session": session,
                "store_id": store_id,
                "mode": mode,
                "status": status,
                "triggered_by_id": triggered_by_id,
                "error_message": error_message,
                "processed_events": processed_events,
                "differences_detected": differences_detected,
            }
        )

    @contextmanager
    def fake_transactional_session(session: FakeManagedSession):
        session.data["transaction"] = True
        yield session

    monkeypatch.setattr(scheduler_service.sync_service, "run_sync_cycle", fake_run_sync_cycle, raising=True)
    monkeypatch.setattr(scheduler_service.crud, "record_sync_session", fake_record_sync_session, raising=True)
    monkeypatch.setattr(scheduler_service, "transactional_session", fake_transactional_session, raising=True)

    scheduler_service._sync_job(provider)

    assert len(sessions) == 1
    session = sessions[0]
    assert session.closed is True
    assert session.data["cycle"] is True
    assert session.data["transaction"] is True
    assert recorded_payload["session"] is session
    assert recorded_payload["status"] is models.SyncStatus.SUCCESS
    assert recorded_payload["processed_events"] == 2
    assert recorded_payload["differences_detected"] == 2
    assert recorded_payload["error_message"] is None
    assert recorded_payload["mode"] is models.SyncMode.AUTOMATIC
