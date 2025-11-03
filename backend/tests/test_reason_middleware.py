import pytest

from backend.app.middleware.reason import (
    ReasonHeaderError,
    ensure_reason_header,
    requires_reason_header,
)


class TestRequiresReasonHeader:
    def test_sensitive_write_requires_reason(self) -> None:
        assert requires_reason_header("POST", "/sales/confirm") is True

    def test_sensitive_read_requires_reason(self) -> None:
        assert requires_reason_header("GET", "/reports/metrics") is True

    def test_non_sensitive_route_does_not_require_reason(self) -> None:
        assert requires_reason_header("GET", "/health") is False
        assert requires_reason_header("DELETE", "/public/info") is False


class TestEnsureReasonHeader:
    def test_accepts_valid_reason(self) -> None:
        sanitized = ensure_reason_header("   Venta auditoria POS   ")
        assert sanitized == "Venta auditoria POS"

    def test_rejects_short_reason(self) -> None:
        with pytest.raises(ReasonHeaderError):
            ensure_reason_header(" ok ")

    def test_rejects_reason_without_alphanumeric_content(self) -> None:
        with pytest.raises(ReasonHeaderError):
            ensure_reason_header("-----_____")

    def test_rejects_reason_with_control_characters(self) -> None:
        with pytest.raises(ReasonHeaderError):
            ensure_reason_header("Auditoria\nPOS")

    def test_rejects_reason_too_long(self) -> None:
        with pytest.raises(ReasonHeaderError):
            ensure_reason_header("A" * 205)
