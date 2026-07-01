"""Unit tests for outbound email helpers."""

import pytest

from betrecord_shared.config import get_settings
from betrecord_shared.email import EmailDeliveryError, send_email


def test_send_email_raises_without_smtp_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://www.example.com")
    monkeypatch.setenv("SMTP_HOST", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(EmailDeliveryError, match="SMTP not configured"):
            send_email("user@example.com", "Subject", "Body")
    finally:
        monkeypatch.setenv("ENVIRONMENT", "development")
        get_settings.cache_clear()
