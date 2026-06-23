/* Marketing site — locale boot, language selector, and pricing display. */
(function () {
  "use strict";

  // Mirrors shared/betrecord_shared/pricing.py — fallback when /payments/pricing is unavailable.
  const FALLBACK_PRICES = {
    USD: 4.99, EUR: 4.99, JPY: 700, GBP: 3.99, CNY: 35, AUD: 7.99, CAD: 6.99,
    CHF: 4.5, HKD: 39, SGD: 6.99, SEK: 49, KRW: 6900, NOK: 49, NZD: 8.99,
    INR: 399, MXN: 89, TWD: 149, ZAR: 89, BRL: 24.9, DKK: 35,
  };

  // Map UI locale to a supported billing currency (top-20 FX list in pricing.py).
  const LOCALE_CURRENCIES = {
    en: "USD", "zh-CN": "CNY", "zh-TW": "TWD", hi: "INR", bn: "INR", mr: "INR",
    te: "INR", ta: "INR", gu: "INR", kn: "INR", ml: "INR", pa: "INR", or: "INR", ne: "INR",
    es: "EUR", fr: "EUR", de: "EUR", it: "EUR", nl: "EUR", pt: "BRL", ca: "EUR",
    el: "EUR", fi: "EUR", da: "DKK", sv: "SEK", no: "NOK", pl: "EUR", cs: "EUR",
    sk: "EUR", sl: "EUR", hr: "EUR", ro: "EUR", bg: "EUR", hu: "EUR", et: "EUR",
    lv: "EUR", lt: "EUR", be: "EUR", bs: "EUR", sq: "EUR", sr: "EUR", mt: "EUR",
    lb: "EUR", ga: "EUR", gl: "EUR", eu: "EUR", cy: "GBP", gd: "GBP", fy: "EUR",
    ja: "JPY", ko: "KRW", af: "ZAR", mi: "NZD",
    ar: "USD", ru: "USD", id: "USD", ur: "USD", sw: "USD", tr: "USD", vi: "USD",
    he: "USD", fa: "USD", ps: "USD", uk: "USD", th: "USD", ms: "USD", tl: "USD",
    my: "USD", km: "USD", lo: "USD", mn: "USD", ka: "USD", hy: "USD", kk: "USD",
    ky: "USD", uz: "USD", az: "USD", am: "USD", ha: "USD", ig: "USD", yo: "USD",
    zu: "USD", xh: "USD", rw: "USD", so: "USD", mg: "USD", ny: "USD", ht: "USD",
    jv: "USD", su: "USD", ceb: "USD", tg: "USD", tk: "USD", tt: "USD", ug: "CNY",
    si: "USD", mk: "USD", is: "USD", eo: "EUR",
  };

  let _prices = null;

  function applyHomeTitle() {
    document.title = window.i18n.t("home.meta.title");
  }

  function currencyForLocale(locale) {
    const code = window.i18n.normalizeLocale(locale) || "en";
    if (LOCALE_CURRENCIES[code]) return LOCALE_CURRENCIES[code];
    const base = code.split("-")[0];
    return LOCALE_CURRENCIES[base] || "USD";
  }

  function formatPrice(amount, currency) {
    try {
      return window.i18n.formatLocaleNumber(amount, { style: "currency", currency });
    } catch {
      return `${amount} ${currency}`;
    }
  }

  function priceListFromFallback() {
    return Object.entries(FALLBACK_PRICES).map(([currency, amount]) => ({ currency, amount }));
  }

  function trackLandingVisit() {
    const path = window.location.pathname;
    if (path !== "/" && path !== "/index.html") return;
    const payload = JSON.stringify({
      path: "/",
      referrer: document.referrer || null,
    });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/auth/track/landing", new Blob([payload], { type: "application/json" }));
      return;
    }
    fetch("/auth/track/landing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  }

  async function loadPricing() {
    if (_prices) return _prices;
    try {
      const res = await fetch("/payments/pricing");
      if (res.ok) {
        const data = await res.json();
        _prices = data.prices || priceListFromFallback();
        return _prices;
      }
    } catch { /* static fallback */ }
    _prices = priceListFromFallback();
    return _prices;
  }

  function priceForLocale(prices, locale) {
    const currency = currencyForLocale(locale);
    return prices.find(p => p.currency === currency)
      || prices.find(p => p.currency === "USD")
      || prices[0];
  }

  function updateProPrice() {
    const el = document.getElementById("proPrice");
    if (!el || !_prices) return;
    const hit = priceForLocale(_prices, window.i18n.currentLocale());
    if (!hit) return;
    el.textContent = window.i18n.t("home.pricingProPrice", {
      price: formatPrice(hit.amount, hit.currency),
    });
  }

  async function boot() {
    trackLandingVisit();
    const loc = window.i18n.getLoginLocale();
    await window.i18n.initI18n(loc);
    applyHomeTitle();
    await loadPricing();
    updateProPrice();

    const select = document.getElementById("localeSelect");
    if (select) {
      select.innerHTML = window.i18n.languageOptions(window.i18n.currentLocale());
      select.addEventListener("change", async () => {
        await window.i18n.setLocale(select.value, { persistCookie: true });
        applyHomeTitle();
        updateProPrice();
      });
    }

    window.i18n.applyI18n(document);
    updateProPrice();
  }

  document.addEventListener("DOMContentLoaded", () => {
    boot().catch(e => console.error("Marketing i18n boot failed:", e));
  });
})();
