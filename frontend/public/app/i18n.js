/* Internationalisation — locale bundles, cookies, and DOM helpers. */

const LOCALE_COOKIE = "mbr_locale";
const LOCALE_COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year
const LOCALE_BASE = "/app/locales";

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

/** Login screen: browser language unless returning user (locale cookie). */
function getLoginLocale() {
  const saved = getLocaleCookie();
  if (saved) return saved;
  return browserLocale();
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
  if (!res.ok && code !== "en") return loadLocale("en");
  let data;
  try {
    data = await res.json();
  } catch {
    if (code !== "en") return loadLocale("en");
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

async function setLocale(locale, { persistCookie = false } = {}) {
  await loadCatalog();
  const code = normalizeLocale(locale) || "en";
  await loadLocale(code);
  if (persistCookie) setLocaleCookie(code);
  document.title = t("meta.title");
  applyI18n(document);
  return code;
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
    } else if (el.dataset.i18nHtml) {
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
  getLocaleCookie,
  setLocaleCookie,
  currentLocale,
  localeTag,
  languageOptions,
  normalizeLocale,
  formatLocaleDate,
  formatLocaleTime,
  formatLocaleNumber,
  loadCatalog,
};
