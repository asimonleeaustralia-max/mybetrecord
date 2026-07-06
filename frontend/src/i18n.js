/* Internationalisation — locale bundles, cookies, and DOM helpers. */

const LOCALE_COOKIE = "mbr_locale";
const LOCALE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year
const LOCALE_BASE = "/app/locales";

// Map UI locale to billing currency (mirrors shared/betrecord_shared/pricing.py top-20 list).
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

const CURRENCY_FORMAT_LOCALES = {
  USD: "en-US", GBP: "en-GB", EUR: "de-DE", AUD: "en-AU", CAD: "en-CA",
  NZD: "en-NZ", JPY: "ja-JP", CNY: "zh-CN", TWD: "zh-TW", HKD: "zh-HK",
  SGD: "en-SG", INR: "en-IN", KRW: "ko-KR", CHF: "de-CH", SEK: "sv-SE",
  NOK: "nb-NO", DKK: "da-DK", ZAR: "en-ZA", BRL: "pt-BR", MXN: "es-MX",
};

let _catalog = null;
let _strings = {};
let _locale = "en";

async function loadCatalog() {
  if (_catalog) return _catalog;
  const res = await fetch(`${LOCALE_BASE}/languages.json`);
  _catalog = await res.json();
  return _catalog;
}

function supportedCodes() {
  return Object.keys(_catalog?.all || { en: "English" });
}

function normalizeLocale(raw) {
  if (!raw) return null;
  const tag = String(raw).trim().replace(/_/g, "-");
  const codes = supportedCodes();
  if (codes.includes(tag)) return tag;
  const lower = tag.toLowerCase();
  const hit = codes.find(c => c.toLowerCase() === lower);
  if (hit) return hit;
  const base = lower.split("-")[0];
  if (base === "zh") {
    if (/hant|tw|hk|mo/i.test(tag)) return codes.includes("zh-TW") ? "zh-TW" : null;
    return codes.includes("zh-CN") ? "zh-CN" : null;
  }
  const baseHit = codes.find(c => c.toLowerCase() === base || c.toLowerCase().startsWith(base + "-"));
  return baseHit || null;
}

function browserLocale() {
  const langs = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const lang of langs) {
    const n = normalizeLocale(lang);
    if (n) return n;
  }
  return "en";
}

function getCookie(name) {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

function setLocaleCookie(locale) {
  document.cookie = `${LOCALE_COOKIE}=${encodeURIComponent(locale)};path=/;max-age=${LOCALE_COOKIE_MAX_AGE};SameSite=Lax`;
}

function getLocaleCookie() {
  return normalizeLocale(getCookie(LOCALE_COOKIE));
}

/** First visit: browser language. Returning visitor: locale cookie (if set). */
async function getLoginLocale() {
  await loadCatalog();
  const saved = getLocaleCookie();
  if (saved) return saved;
  return browserLocale();
}

async function bindLocaleSelect(select, { persistCookie = true, updateTitle = true, onChange } = {}) {
  if (!select || select.dataset.localeBound) return;
  await loadCatalog();
  const code = currentLocale();
  select.innerHTML = languageOptions(code);
  select.value = code;
  select.dataset.localeBound = "1";
  select.addEventListener("change", async () => {
    await setLocale(select.value, { persistCookie, updateTitle });
    onChange?.();
  });
}

function currentLocale() {
  return _locale;
}

function localeTag() {
  if (_locale === "zh-CN") return "zh-Hans";
  if (_locale === "zh-TW") return "zh-Hant";
  if (_locale === "no") return "nb";
  return _locale;
}

async function loadLocale(locale) {
  const code = normalizeLocale(locale) || "en";
  if (!_strings.en) {
    const enRes = await fetch(`${LOCALE_BASE}/en.json`);
    if (enRes.ok) _strings.en = await enRes.json();
  }
  if (_strings[code]) {
    _locale = code;
    document.documentElement.lang = localeTag();
    return;
  }
  const res = await fetch(`${LOCALE_BASE}/${code}.json`);
  if (!res.ok && code !== "en") {
    window.__localeFallback = true;
    return loadLocale("en");
  }
  let data;
  try {
    data = await res.json();
  } catch {
    if (code !== "en") {
      window.__localeFallback = true;
      return loadLocale("en");
    }
    throw new Error("Invalid en.json");
  }
  _strings[code] = data;
  _locale = code;
  document.documentElement.lang = localeTag();
}

async function initI18n(locale) {
  await loadCatalog();
  const code = normalizeLocale(locale) || "en";
  await loadLocale(code);
  return _locale;
}

async function setLocale(locale, { persistCookie = false, updateTitle = true } = {}) {
  await loadCatalog();
  const code = normalizeLocale(locale) || "en";
  await loadLocale(code);
  if (persistCookie) setLocaleCookie(code);
  if (updateTitle) document.title = t("meta.title");
  applyI18n(document);
  return code;
}

function currencyForLocale(locale) {
  const code = normalizeLocale(locale) || "en";
  if (LOCALE_CURRENCIES[code]) return LOCALE_CURRENCIES[code];
  const base = code.split("-")[0];
  return LOCALE_CURRENCIES[base] || "USD";
}

/** Stripe Checkout locale — https://docs.stripe.com/api/checkout/sessions/create#create_checkout_session-locale */
function stripeLocale(locale) {
  const code = normalizeLocale(locale) || "en";
  const map = { "zh-CN": "zh", "zh-TW": "zh-TW", no: "nb", en: "en", "en-GB": "en-GB" };
  if (map[code]) return map[code];
  const base = code.split("-")[0];
  const direct = new Set([
    "bg", "cs", "da", "de", "el", "es", "et", "fi", "fr", "hr", "hu", "id", "it",
    "ja", "ko", "lt", "lv", "ms", "mt", "nb", "nl", "pl", "pt", "ro", "ru", "sk",
    "sl", "sv", "th", "tr", "vi",
  ]);
  if (direct.has(base)) return base;
  if (base === "pt") return "pt-BR";
  if (base === "fr" && /-ca/i.test(code)) return "fr-CA";
  if (base === "es" && /-(419|mx|ar|co|cl)/i.test(code)) return "es-419";
  return "auto";
}

function moneyFormatLocale(currency) {
  const c = (currency || "USD").toUpperCase();
  return CURRENCY_FORMAT_LOCALES[c] || "en-US";
}

function get(obj, path) {
  return path.split(".").reduce((o, k) => (o && o[k] != null ? o[k] : undefined), obj);
}

function interpolate(str, vars) {
  if (!vars || !str) return str;
  return str.replace(/\{\{(\w+)\}\}/g, (_, k) => (vars[k] != null ? String(vars[k]) : ""));
}

function t(key, vars) {
  const val = get(_strings[_locale], key) ?? get(_strings.en, key) ?? key;
  return typeof val === "string" ? interpolate(val, vars) : key;
}

function applyI18n(root = document) {
  root.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    const val = t(key);
    if (el.dataset.i18nAttr) {
      el.setAttribute(el.dataset.i18nAttr, val);
    } else if (el.hasAttribute("data-i18n-html")) {
      el.innerHTML = val;
    } else {
      el.textContent = val;
    }
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

function languageOptions(selected = "en") {
  const cat = _catalog;
  if (!cat) return "";
  const top = cat.top20 || [];
  const all = cat.all || {};
  const rest = Object.keys(all)
    .filter(c => !top.includes(c))
    .sort((a, b) => all[a].localeCompare(all[b], undefined, { sensitivity: "base" }));
  const order = [...top, ...rest];
  const sel = normalizeLocale(selected) || "en";
  return order.map(code =>
    `<option value="${code}"${code === sel ? " selected" : ""}>${all[code] || code}</option>`
  ).join("");
}

function formatLocaleDate(d, opts) {
  return d.toLocaleDateString(localeTag(), opts);
}

function formatLocaleTime(d, opts) {
  return d.toLocaleTimeString(localeTag(), opts);
}

function formatLocaleNumber(n, opts) {
  return n.toLocaleString(localeTag(), opts);
}

window.i18n = {
  initI18n,
  setLocale,
  t,
  applyI18n,
  getLoginLocale,
  bindLocaleSelect,
  getLocaleCookie,
  setLocaleCookie,
  currentLocale,
  localeTag,
  languageOptions,
  normalizeLocale,
  currencyForLocale,
  stripeLocale,
  moneyFormatLocale,
  formatLocaleDate,
  formatLocaleTime,
  formatLocaleNumber,
  loadCatalog,
};
