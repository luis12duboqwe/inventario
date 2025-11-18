from backend.app.config import settings


def test_lan_discovery_respects_advertised_host(light_client, monkeypatch):
    monkeypatch.setattr(settings, "lan_advertised_host", "192.168.10.25")
    monkeypatch.setattr(settings, "lan_advertised_port", 9000)
    response = light_client.get("/discovery/lan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["host"] == "192.168.10.25"
    assert payload["port"] == 9000
    assert payload["api_base_url"].startswith("http://192.168.10.25:9000")
    assert payload["database"]["engine"]
    assert payload["database"]["location"]


def test_lan_discovery_reports_disabled_state(light_client, monkeypatch):
    monkeypatch.setattr(settings, "lan_discovery_enabled", False)
    response = light_client.get("/discovery/lan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert any("desactiv" in note.lower() for note in payload["notes"])
