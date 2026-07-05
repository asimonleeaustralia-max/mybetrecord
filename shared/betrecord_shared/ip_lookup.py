"""Best-effort ISP and country lookup from a public IP address."""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class IpLookupResult:
    isp: str
    country: str  # ISO 3166-1 alpha-2


def is_public_ip(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_reserved
        or addr.is_link_local
        or addr.is_multicast
    )


@lru_cache(maxsize=2048)
def lookup_ip(ip: str) -> IpLookupResult | None:
    """Resolve ISP and country for a public IP. Returns None when lookup fails."""
    if not is_public_ip(ip):
        return None
    url = (
        f"http://ip-api.com/json/{ip.strip()}"
        "?fields=status,countryCode,isp,query"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mybetrecord/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if data.get("status") != "success":
        return None
    isp = (data.get("isp") or "").strip()
    country = (data.get("countryCode") or "").strip().upper()[:2]
    if not isp or not country:
        return None
    return IpLookupResult(isp=isp[:128], country=country)
