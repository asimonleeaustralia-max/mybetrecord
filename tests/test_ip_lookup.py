"""Tests for IP geolocation lookup."""

from unittest.mock import MagicMock, patch

from betrecord_shared.ip_lookup import IpLookupResult, is_public_ip, lookup_ip


def test_is_public_ip():
    assert is_public_ip("8.8.8.8") is True
    assert is_public_ip("127.0.0.1") is False
    assert is_public_ip("10.0.0.1") is False
    assert is_public_ip(None) is False
    assert is_public_ip("not-an-ip") is False


def test_lookup_ip_success():
    lookup_ip.cache_clear()
    payload = b'{"status":"success","countryCode":"US","isp":"Google LLC","query":"8.8.8.8"}'
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("betrecord_shared.ip_lookup.urllib.request.urlopen", return_value=mock_resp):
        result = lookup_ip("8.8.8.8")
    assert result == IpLookupResult(isp="Google LLC", country="US")


def test_lookup_ip_private_skipped():
    lookup_ip.cache_clear()
    assert lookup_ip("127.0.0.1") is None


def test_lookup_ip_failure():
    lookup_ip.cache_clear()
    with patch("betrecord_shared.ip_lookup.urllib.request.urlopen", side_effect=TimeoutError):
        assert lookup_ip("8.8.8.8") is None
