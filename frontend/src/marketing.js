/* Marketing site — locale boot, language selector, and pricing display. */
(function () {
  "use strict";

  // Mirrors shared/betrecord_shared/pricing.py — fallback when /payments/pricing is unavailable.
  const FALLBACK_PRICES = {
    USD: 4.99, EUR: 4.99, JPY: 700, GBP: 3.99, CNY: 35, AUD: 7.99, CAD: 6.99,
    CHF: 4.5, HKD: 39, SGD: 6.99, SEK: 49, KRW: 6900, NOK: 49, NZD: 8.99,
    INR: 399, MXN: 89, TWD: 149, ZAR: 89, BRL: 24.9, DKK: 35,
  };

  let _prices = null;

  function pageKind() {
    const path = window.location.pathname.replace(/\/index\.html$/, "");
    if (path === "/pricing" || path.endsWith("/pricing")) return "pricing";
    if (path === "/blog" || path.endsWith("/blog")) return "blog-index";
    const blogPost = path.match(/\/blog\/([^/]+)\.html$/);
    if (blogPost) return { kind: "blog-post", slug: blogPost[1] };
    return "home";
  }

  function applyPageMeta() {
    const kind = pageKind();
    let titleKey = "home.meta.title";
    let descKey = "home.meta.description";

    if (kind === "pricing") {
      titleKey = "home.meta.pricingTitle";
      descKey = "home.meta.pricingDescription";
    } else if (kind === "blog-index") {
      titleKey = "blog.meta.title";
      descKey = "blog.meta.description";
    } else if (kind?.kind === "blog-post") {
      const base = window.i18n.t(`blog.posts.${kind.slug}.title`);
      document.title = base === `blog.posts.${kind.slug}.title`
        ? document.title
        : `${base} — mybetrecord`;
      const desc = window.i18n.t(`blog.posts.${kind.slug}.description`);
      const meta = document.querySelector('meta[name="description"]');
      if (meta && desc !== `blog.posts.${kind.slug}.description`) {
        meta.setAttribute("content", desc);
      }
      return;
    }

    document.title = window.i18n.t(titleKey);
    const meta = document.querySelector('meta[name="description"]');
    if (meta) meta.setAttribute("content", window.i18n.t(descKey));
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
    const params = new URLSearchParams(window.location.search);
    const promo = params.get("promo");
    const payload = JSON.stringify({
      path: "/",
      referrer: document.referrer || null,
      promo_code: promo ? promo.trim() : null,
      browser_language: navigator.language || null,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
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
    for (const path of ["/sub/pricing", "/pro/pricing", "/billing/pricing"]) {
      try {
        const res = await fetch(path);
        if (res.ok) {
          const data = await res.json();
          _prices = data.prices || priceListFromFallback();
          return _prices;
        }
      } catch { /* try next path */ }
    }
    _prices = priceListFromFallback();
    return _prices;
  }

  function priceForLocale(prices, locale) {
    const currency = window.i18n.currencyForLocale(locale);
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
    const loc = await window.i18n.getLoginLocale();
    await window.i18n.initI18n(loc);

    const select = document.getElementById("localeSelect");
    await window.i18n.bindLocaleSelect(select, {
      persistCookie: true,
      updateTitle: false,
      onChange: () => {
        applyPageMeta();
        updateProPrice();
      },
    });

    window.i18n.applyI18n(document);
    applyPageMeta();

    loadPricing().then(() => updateProPrice()).catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    boot().catch(e => console.error("Marketing i18n boot failed:", e));
  });
})();
