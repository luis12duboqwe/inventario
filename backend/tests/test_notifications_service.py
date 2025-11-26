from __future__ import annotations

import pytest
import httpx

from backend.app.config import settings
from backend.app.services import notifications


class DummySMTP:
    """Stub mínimo para capturar el envío de correos."""

    last_instance: DummySMTP | None = None

    def __init__(self, host: str, port: int, timeout: int):  # noqa: D401 - interfaz SMTP
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged = None
        self.sent_messages: list = []
        DummySMTP.last_instance = self

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged = (username, password)

    def send_message(self, message) -> None:
        self.sent_messages.append(message)

    def quit(self) -> None:  # noqa: D401 - interfaz SMTP
        self.closed = True


@pytest.fixture(autouse=True)
def restore_notification_settings():
    original = {
        "email_host": settings.notifications_email_host,
        "email_from": settings.notifications_email_from,
        "email_port": settings.notifications_email_port,
        "email_user": settings.notifications_email_username,
        "email_pass": settings.notifications_email_password,
        "email_tls": settings.notifications_email_use_tls,
        "wa_url": settings.notifications_whatsapp_api_url,
        "wa_token": settings.notifications_whatsapp_token,
        "wa_sender": settings.notifications_whatsapp_sender,
        "wa_timeout": settings.notifications_whatsapp_timeout,
    }
    try:
        yield
    finally:
        settings.notifications_email_host = original["email_host"]
        settings.notifications_email_from = original["email_from"]
        settings.notifications_email_port = original["email_port"]
        settings.notifications_email_username = original["email_user"]
        settings.notifications_email_password = original["email_pass"]
        settings.notifications_email_use_tls = original["email_tls"]
        settings.notifications_whatsapp_api_url = original["wa_url"]
        settings.notifications_whatsapp_token = original["wa_token"]
        settings.notifications_whatsapp_sender = original["wa_sender"]
        settings.notifications_whatsapp_timeout = original["wa_timeout"]


def test_send_email_notification(monkeypatch):
    settings.notifications_email_host = "smtp.test"
    settings.notifications_email_from = "noreply@test"
    settings.notifications_email_username = "api"
    settings.notifications_email_password = "secret"
    settings.notifications_email_use_tls = True
    monkeypatch.setattr(notifications.smtplib, "SMTP", DummySMTP)

    notifications.send_email_notification(
        recipients=["destino@test"],
        subject="Recibo POS",
        body="Adjunto recibo",
        attachments=[notifications.Attachment(filename="ticket.pdf", content=b"PDF", content_type="application/pdf")],
    )

    smtp = DummySMTP.last_instance
    assert smtp is not None
    assert smtp.started_tls is True
    assert smtp.logged == ("api", "secret")
    assert smtp.sent_messages
    message = smtp.sent_messages[0]
    assert message["Subject"] == "Recibo POS"
    assert "destino@test" in message["To"]


def test_send_email_notification_missing_config(monkeypatch):
    settings.notifications_email_host = None
    settings.notifications_email_from = None
    with pytest.raises(notifications.EmailNotConfiguredError):
        notifications.send_email_notification(
            recipients=["demo@test"],
            subject="Recibo",
            body="hola",
        )


class DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {"status": "ok"}
        self.text = "ok"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=httpx.Request("POST", "https://api"), response=self)

    def json(self) -> dict:
        return self._payload


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict, headers: dict):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return DummyResponse()


@pytest.mark.asyncio
async def test_send_whatsapp_message(monkeypatch):
    settings.notifications_whatsapp_api_url = "https://api.whatsapp.test/messages"
    settings.notifications_whatsapp_token = "token"
    settings.notifications_whatsapp_sender = "5215500000000"

    dummy_client = DummyAsyncClient()

    def client_factory(*args, **kwargs):
        dummy_client.calls.clear()
        return dummy_client

    monkeypatch.setattr(notifications.httpx, "AsyncClient", client_factory)

    result = await notifications.send_whatsapp_message(
        to_number="5215511112222",
        message="Hola",
        media_url="https://cdn.test/recibo.pdf",
        reference="SALE-1",
    )

    assert result == {"status": "ok"}
    assert dummy_client.calls
    payload = dummy_client.calls[0]["json"]
    assert payload["from"] == "5215500000000"
    assert payload["to"] == "5215511112222"
    assert payload["media_url"] == "https://cdn.test/recibo.pdf"
    headers = dummy_client.calls[0]["headers"]
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.asyncio
async def test_send_whatsapp_message_missing_config():
    settings.notifications_whatsapp_api_url = None
    settings.notifications_whatsapp_token = None
    settings.notifications_whatsapp_sender = None

    with pytest.raises(notifications.WhatsAppNotConfiguredError):
        await notifications.send_whatsapp_message(
            to_number="5215511112222",
            message="Hola",
        )
