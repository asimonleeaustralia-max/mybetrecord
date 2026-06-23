"""Parse visitor metadata from HTTP headers (user agent, country, bot detection)."""

from __future__ import annotations

import re

# Common crawlers and automated clients — case-insensitive substring match.
_BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|slurp|mediapartners|facebookexternalhit|"
    r"linkedinbot|twitterbot|whatsapp|telegrambot|discordbot|"
    r"googlebot|bingbot|duckduckbot|baiduspider|yandexbot|applebot|"
    r"semrush|ahrefs|mj12bot|dotbot|petalbot|bytespider|"
    r"curl/|wget/|python-requests|python-urllib|httpx/|go-http-client|"
    r"headlesschrome|phantomjs|selenium|scrapy",
    re.I,
)

_BROWSER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Edg(?:e|A|IOS)?/([\d.]+)", re.I), "Edge"),
    (re.compile(r"OPR/([\d.]+)", re.I), "Opera"),
    (re.compile(r"Chrome/([\d.]+)", re.I), "Chrome"),
    (re.compile(r"Firefox/([\d.]+)", re.I), "Firefox"),
    (re.compile(r"Version/([\d.]+).*Safari/", re.I), "Safari"),
    (re.compile(r"Safari/([\d.]+)", re.I), "Safari"),
    (re.compile(r"MSIE ([\d.]+)", re.I), "IE"),
    (re.compile(r"Trident/.*rv:([\d.]+)", re.I), "IE"),
]


def is_bot(user_agent: str | None) -> bool:
    if not user_agent or len(user_agent.strip()) < 8:
        return True
    return bool(_BOT_PATTERNS.search(user_agent))


def parse_browser(user_agent: str | None) -> str:
    if not user_agent:
        return "Unknown"
    for pattern, name in _BROWSER_PATTERNS:
        m = pattern.search(user_agent)
        if m:
            version = m.group(1).split(".")[0]
            return f"{name} {version}" if version.isdigit() else name
    return "Unknown"


def client_country(headers: dict[str, str]) -> str | None:
    """Best-effort ISO country code from common CDN / proxy headers."""
    for key in (
        "cf-ipcountry",
        "cloudfront-viewer-country",
        "x-country-code",
        "x-appengine-country",
        "x-vercel-ip-country",
        "x-azure-client-country",
    ):
        val = headers.get(key)
        if val and val.strip() and val.strip().upper() != "XX":
            return val.strip().upper()[:2]
    return None
