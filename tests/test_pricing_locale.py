"""Tests for Pro pricing helpers."""

from betrecord_shared import pricing


def test_currency_for_locale_maps_german_to_eur():
    assert pricing.currency_for_locale("de") == "EUR"


def test_currency_for_locale_maps_english_to_usd():
    assert pricing.currency_for_locale("en") == "USD"


def test_stripe_checkout_locale_maps_chinese():
    assert pricing.stripe_checkout_locale("zh-CN") == "zh"
    assert pricing.stripe_checkout_locale("zh-TW") == "zh-TW"


def test_stripe_checkout_locale_unknown_falls_back_to_auto():
    assert pricing.stripe_checkout_locale("xx") == "auto"
