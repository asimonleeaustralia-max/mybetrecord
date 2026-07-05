"""Tests for visitor header parsing."""

from betrecord_shared.visitor import client_country, is_bot, parse_browser, parse_os


def test_parse_browser_chrome():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    assert parse_browser(ua) == "Chrome 120"


def test_parse_os_windows():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    assert parse_os(ua) == "Windows"


def test_parse_os_android():
    ua = "Mozilla/5.0 (Linux; Android 13; Pixel 7) Chrome/120.0.0.0 Mobile Safari/537.36"
    assert parse_os(ua) == "Android 13"


def test_is_bot_detects_crawler():
    assert is_bot("Googlebot/2.1") is True
    assert is_bot("Mozilla/5.0 Chrome/120.0.0.0") is False


def test_client_country_from_headers():
    assert client_country({"cf-ipcountry": "gb"}) == "GB"
    assert client_country({"x-forwarded-for": "1.2.3.4"}) is None
