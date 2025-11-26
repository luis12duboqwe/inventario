import os

from fastapi.testclient import TestClient

from backend.app.config import settings


def test_help_context_exposes_guides_and_status(client: TestClient):
    response = client.get("/help/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["manuals_base_path"] == "docs/capacitacion"
    assert isinstance(payload.get("guides"), list)
    assert any(guide["module"] == "inventory" for guide in payload["guides"])
    assert payload["demo_mode_enabled"] is False


def test_demo_preview_respects_flag(client: TestClient):
    original = settings.demo_mode_enabled
    settings.demo_mode_enabled = True
    os.environ["SOFTMOBILE_DEMO_MODE"] = "1"

    try:
        response = client.get("/help/demo")
        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is True
        assert payload["dataset"]
        assert payload["dataset"]["inventory"]
    finally:
        settings.demo_mode_enabled = original
        os.environ.pop("SOFTMOBILE_DEMO_MODE", None)
