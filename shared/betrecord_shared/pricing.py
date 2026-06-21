"""Pro subscription pricing.

A single source of truth for what Pro costs, shared by the payments service
(to build Stripe checkout sessions) and exposed to the frontend (to render the
upgrade options). The target is roughly 5 USD / month; each currency is rounded
to a tidy, recognisable local price point rather than a live FX conversion, so
the bettor always sees a stable, "clean" number. The business absorbs the FX
swing between currencies — that's an accepted trade-off.

Amounts are the human-facing price per month. Stripe wants the amount in the
currency's smallest unit (e.g. cents), with zero-decimal currencies (JPY, KRW)
passed as the whole number — `stripe_unit_amount` handles both cases.
"""

from __future__ import annotations

# Currencies that Stripe expects WITHOUT a fractional component. The amount is
# passed to Stripe as-is rather than multiplied by 100.
# https://stripe.com/docs/currencies#zero-decimal
ZERO_DECIMAL_CURRENCIES = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG",
    "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
}

DEFAULT_CURRENCY = "USD"

# The world's top 20 currencies (by FX turnover / economic weight), each priced
# at a clean local value near 5 USD / month. Mirrors the first 20 entries of the
# frontend CURRENCIES list so the upgrade currency picker stays consistent.
PRO_MONTHLY_PRICES: dict[str, float] = {
    "USD": 4.99,
    "EUR": 4.99,
    "JPY": 700,      # zero-decimal
    "GBP": 3.99,
    "CNY": 35.00,
    "AUD": 7.99,
    "CAD": 6.99,
    "CHF": 4.50,
    "HKD": 39.00,
    "SGD": 6.99,
    "SEK": 49.00,
    "KRW": 6900,     # zero-decimal
    "NOK": 49.00,
    "NZD": 8.99,
    "INR": 399.00,
    "MXN": 89.00,
    "TWD": 149.00,
    "ZAR": 89.00,
    "BRL": 24.90,
    "DKK": 35.00,
}

# Order to present currencies in the picker (largest economic weight first).
SUPPORTED_CURRENCIES: list[str] = list(PRO_MONTHLY_PRICES.keys())


def is_supported_currency(currency: str | None) -> bool:
    return bool(currency) and currency.upper() in PRO_MONTHLY_PRICES


def normalise_currency(currency: str | None) -> str:
    """Return a supported currency code, falling back to USD."""
    if currency and currency.upper() in PRO_MONTHLY_PRICES:
        return currency.upper()
    return DEFAULT_CURRENCY


def price_amount(currency: str) -> float:
    """Human-facing monthly price for the given currency."""
    return PRO_MONTHLY_PRICES[normalise_currency(currency)]


def stripe_unit_amount(currency: str) -> int:
    """Amount in the smallest currency unit, as Stripe expects it."""
    code = normalise_currency(currency)
    amount = PRO_MONTHLY_PRICES[code]
    if code in ZERO_DECIMAL_CURRENCIES:
        return int(round(amount))
    return int(round(amount * 100))


def pricing_table() -> list[dict]:
    """Serialisable list of {currency, amount, interval} for the frontend."""
    return [
        {"currency": code, "amount": amount, "interval": "month"}
        for code, amount in PRO_MONTHLY_PRICES.items()
    ]
