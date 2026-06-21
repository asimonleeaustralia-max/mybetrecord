/* mybetrecord — single-page client.
   Talks to the services through the same origin; nginx proxies
   /auth, /bets, /reports, /payments to the right container. */
(function () {
"use strict";

const TOKEN_KEY = "mbr_token";
const state = { user: null, sports: [], betTypes: [], tipsters: [], currencies: [], charts: {} };

const translate = (key, vars) => window.i18n?.t(key, vars) ?? key;
const t = translate;

function apiErrorMessage(detail) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const msg = detail.map(e => (e && e.msg) || "").filter(Boolean).join("; ");
    if (msg) return msg;
  }
  return translate("errors.requestFailed");
}

function clone(id) {
  const node = document.importNode($(`#${id}`).content, true);
  if (window.i18n) i18n.applyI18n(node);
  return node;
}

// Top currencies by forex turnover / economic weight, largest first.
const CURRENCIES = [
  ["USD", "US Dollar"], ["EUR", "Euro"], ["JPY", "Japanese Yen"], ["GBP", "British Pound"],
  ["CNY", "Chinese Yuan"], ["AUD", "Australian Dollar"], ["CAD", "Canadian Dollar"],
  ["CHF", "Swiss Franc"], ["HKD", "Hong Kong Dollar"], ["SGD", "Singapore Dollar"],
  ["SEK", "Swedish Krona"], ["KRW", "South Korean Won"], ["NOK", "Norwegian Krone"],
  ["NZD", "New Zealand Dollar"], ["INR", "Indian Rupee"], ["MXN", "Mexican Peso"],
  ["TWD", "New Taiwan Dollar"], ["ZAR", "South African Rand"], ["BRL", "Brazilian Real"],
  ["DKK", "Danish Krone"], ["PLN", "Polish Zloty"], ["THB", "Thai Baht"],
  ["IDR", "Indonesian Rupiah"], ["HUF", "Hungarian Forint"], ["CZK", "Czech Koruna"],
  ["ILS", "Israeli Shekel"], ["CLP", "Chilean Peso"], ["PHP", "Philippine Peso"],
  ["AED", "UAE Dirham"], ["COP", "Colombian Peso"], ["SAR", "Saudi Riyal"],
  ["MYR", "Malaysian Ringgit"], ["RON", "Romanian Leu"], ["TRY", "Turkish Lira"],
  ["BGN", "Bulgarian Lev"], ["ARS", "Argentine Peso"], ["PEN", "Peruvian Sol"],
  ["RUB", "Russian Ruble"], ["ISK", "Icelandic Króna"], ["EGP", "Egyptian Pound"],
  ["VND", "Vietnamese Dong"], ["NGN", "Nigerian Naira"], ["PKR", "Pakistani Rupee"],
  ["UAH", "Ukrainian Hryvnia"], ["BDT", "Bangladeshi Taka"], ["MAD", "Moroccan Dirham"],
  ["QAR", "Qatari Riyal"], ["KWD", "Kuwaiti Dinar"], ["BHD", "Bahraini Dinar"],
];

function currencyCodes(limit) {
  return new Set(CURRENCIES.slice(0, limit).map(([c]) => c));
}

function fillCurrencyDatalist(datalist, limit) {
  datalist.innerHTML = CURRENCIES.slice(0, limit).map(([code, name]) =>
    `<option value="${code}">${esc(name)}</option>`
  ).join("");
}

function fillCurrencySelect(select, limit, selected = "") {
  const list = CURRENCIES.slice(0, limit);
  const codes = currencyCodes(limit);
  const sel = (selected || "").toUpperCase();
  let html = "";
  if (sel && !codes.has(sel)) {
    html += `<option value="${esc(sel)}" selected>${esc(sel)}</option>`;
  }
  html += list.map(([code, name]) =>
    `<option value="${code}"${code === sel ? " selected" : ""}>${code} — ${esc(name)}</option>`
  ).join("");
  select.innerHTML = html;
}

function browserTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

function timezoneOffsetLabel(tz) {
  try {
    const part = new Intl.DateTimeFormat("en-GB", { timeZone: tz, timeZoneName: "shortOffset" })
      .formatToParts(new Date())
      .find(p => p.type === "timeZoneName");
    return part ? part.value : "";
  } catch {
    return "";
  }
}

function fillTimezoneSelect(select, selected = "UTC") {
  let zones;
  try {
    zones = Intl.supportedValuesOf("timeZone");
  } catch {
    zones = ["UTC"];
  }
  zones.sort();
  const sel = selected || "UTC";
  const known = new Set(zones);
  let html = "";
  if (sel && !known.has(sel)) {
    html += `<option value="${esc(sel)}" selected>${esc(sel)}</option>`;
  }
  html += zones.map(tz => {
    const off = timezoneOffsetLabel(tz);
    const label = off ? `${tz} (${off})` : tz;
    return `<option value="${esc(tz)}"${tz === sel ? " selected" : ""}>${esc(label)}</option>`;
  }).join("");
  select.innerHTML = html;
}

// Popular sports by global betting handle, largest first.
const SPORTS = [
  // Major markets
  "Soccer", "Horse racing", "American football", "Basketball", "Tennis",
  "Cricket", "Golf", "Baseball", "Rugby union", "Ice hockey",
  "Boxing", "MMA", "Greyhound racing", "Harness racing", "Darts",
  "Snooker", "Rugby league", "Rugby sevens", "Cycling", "Formula 1",
  "Esports", "Volleyball", "Handball", "Table tennis", "Futsal",
  // Regional & secondary team sports
  "Australian rules football", "Gaelic football", "Hurling", "Field hockey",
  "Beach volleyball", "Water polo", "Lacrosse", "Floorball", "Netball",
  "Bandy", "Softball", "Kabaddi",
  // Motorsport
  "Motorsport", "NASCAR", "MotoGP", "IndyCar", "Rally",
  // Winter sports
  "Alpine skiing", "Cross-country skiing", "Ski jumping", "Biathlon",
  "Curling", "Figure skating", "Bobsleigh", "Luge", "Skeleton",
  // Combat & racket
  "Muay Thai", "Kickboxing", "Wrestling", "Pro wrestling", "Badminton",
  "Squash", "Padel", "Pickleball",
  // Athletics & aquatics
  "Athletics", "Swimming", "Diving", "Triathlon", "Rowing", "Sailing",
  "Surfing", "Skateboarding", "Climbing", "Gymnastics",
  // Other sports & games
  "Pool", "Bowls", "Chess", "Equestrian", "Polo", "Shooting", "Archery",
  // Non-sport / specials
  "Virtual sports", "Olympics", "Politics", "Entertainment", "TV & film",
  "Music awards", "Financial markets", "Lottery", "Specials",
];

// Common bet types by market, largest / most common first.
const BET_TYPES = [
  // Match result
  "Win", "Each way", "Place", "Outright", "Ante-post", "Draw no bet", "Double chance",
  "Match odds", "Moneyline", "To qualify", "To be relegated", "Top scorer",
  // Handicap & spread
  "Handicap", "Asian handicap", "European handicap", "Spread", "Puck line", "Run line",
  "Game handicap", "Set handicap",
  // Totals
  "Over / Under", "Asian totals", "Team totals", "Total goals", "Total points",
  "Total games", "Total sets", "Total runs", "Total corners", "Total cards",
  // Accumulators & full cover
  "Accumulator", "Multi / Acca", "Parlay", "Full cover", "System bet",
  "Double", "Treble", "Trixie", "Patent", "Yankee", "Canadian", "Heinz",
  "Super Heinz", "Goliath", "Lucky 15", "Lucky 31", "Lucky 63", "Alphabet",
  // Score & time
  "Correct score", "Half-time / Full-time", "Half-time result", "Full-time result",
  "Winning margin", "Race to points", "Next goal", "Next scorer",
  // Goals & scoring
  "Both teams to score", "Clean sheet", "First goalscorer", "Anytime goalscorer",
  "Last goalscorer", "To score", "Goal line", "Odd / Even goals",
  // Tennis & racket
  "Set betting", "Set winner", "Game winner", "Total aces",
  // Racing
  "Forecast", "Tricast", "Reverse forecast", "Without favourite", "Match bet",
  "Distance", "Faller insurance",
  // Props & specials
  "Prop", "Player prop", "Team prop", "Special", "Method of victory", "Round betting",
  "Cards", "Corners", "Penalties", "Bookings", "Shots on target",
  "First team to score", "Highest scoring half", "Win to nil",
  // Exchange & trading
  "Back", "Lay", "Trading",
  // Other
  "In-play", "Cash out", "Boosted odds", "Request a bet", "Same game parlay",
  "Bet builder", "Insurance", "Free bet",
];

// Legacy snake_case values stored before free-text bet types.
const BET_TYPE_LABELS = {
  win: "Win",
  each_way: "Each way",
  over_under: "Over / Under",
  multi: "Multi / Acca",
  handicap: "Handicap",
  other: "Other",
};

function betTypeLabel(v) {
  if (!v) return "";
  const mapped = BET_TYPE_LABELS[v] || BET_TYPE_LABELS[v.toLowerCase()];
  if (mapped) return mapped;
  if (v.includes("_")) {
    return v.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }
  return v;
}

function betTypeChoices(extra = []) {
  const seen = new Set();
  const items = [];
  for (const t of [...extra, ...BET_TYPES]) {
    const key = (t || "").trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    items.push(t.trim());
  }
  return items.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

function fillBetTypeDatalist(datalist, extra = []) {
  fillNameDatalist(datalist, BET_TYPES, extra);
}

function betTypeFilterOptions(selected = "") {
  const types = betTypeChoices(state.betTypes || []);
  const opts = types.map(betType => {
    const sel = betType === selected ? " selected" : "";
    return `<option value="${esc(betType)}"${sel}>${esc(betTypeLabel(betType))}</option>`;
  }).join("");
  return `<option value="">${t("bets.all")}</option>${opts}`;
}

// Major bookmakers & betting exchanges worldwide (largest / most common first).
const BOOKMAKERS = [
  // Global / multi-market operators
  "Bet365", "FanDuel", "DraftKings", "BetMGM", "Caesars Sportsbook",
  "Betway", "Paddy Power", "Betfair", "Sky Bet", "William Hill",
  "Ladbrokes", "Coral", "bwin", "Unibet", "888sport",
  "Betsson", "Pinnacle", "Stake", "Betano", "Tipico",
  "Betfred", "BetVictor", "Spreadex", "BoyleSports", "QuinnBet",
  "Virgin Bet", "LiveScore Bet", "Novibet", "Coolbet", "ComeOn",
  "LeoVegas", "Mr Green", "PlayOJO", "Grosvenor", "NordicBet",
  "Betsafe", "Expekt", "Rizk", "Betclic", "Winamax",
  "Sisal", "GoldBet", "Lottomatica", "Snai", "Eurobet",
  "Planetwin365", "Codere", "OPAP", "Fortuna", "Superbet",
  "Mozzart Bet", "STS", "OlyBet", "Optibet", "TonyBet",
  "Marathonbet", "Interwetten", "Admiral", "Cashpoint", "Bet3000",
  "Merkur Bets", "Happybet", "NetBet", "ZEbet", "PMU",
  "Parions Sport", "FDJ", "Svenska Spel", "ATG", "Danske Spil",
  "LOTTO24", "Lottoland", "GGPoker", "BetKing", "Hollywoodbets",
  "1xBet", "22Bet", "Melbet", "Dafabet", "SBOBET",
  "188Bet", "M88", "W88", "Fun88", "12Bet",
  // US & Canada sportsbooks
  "Fanatics Sportsbook", "BetRivers", "Hard Rock Bet", "theScore Bet", "ESPN BET",
  "PointsBet", "Bally Bet", "WynnBET", "SugarHouse", "SuperBook",
  "Circa Sports", "BetOnline", "Bovada", "MyBookie", "BetUS",
  "BetOnline.ag", "Sports Interaction", "Bet99", "Proline+", "PlayUp",
  "Underdog Sportsbook", "Fliff", "Rebet", "Golden Nugget", "Horseshoe",
  // Australia & New Zealand
  "Sportsbet", "TAB", "TAB NZ", "Neds", "BetRight",
  "PointsBet AU", "BlueBet", "TopSport", "Palmerbet", "BetDeluxe",
  "Ladbrokes AU", "Unibet AU",
  // Latin America
  "Caliente", "Betcris", "Rivalo", "Betplay", "Rushbet",
  "Betwarrior", "Pixbet", "EstrelaBet", "KTO", "Betnacional",
  "Sportingbet", "Blaze",
  // Asia-Pacific state & racing
  "HKJC", "Singapore Pools",
  // UK & Ireland independents
  "AK Bets", "Star Sports", "McBookie", "Jennings Bet", "BetGoodwin",
  "PricedUp", "talkSPORT BET", "Betzone", "DragonBet", "VBet",
  "10bet", "SBK", "Marshalls World of Sport",
  // Africa
  "Supabets", "World Sports Betting", "Sunbet", "Gbets", "Bet.co.za",
  // Betting exchanges
  "Betfair Exchange", "Smarkets", "Matchbook", "Betdaq", "SX Bet",
  "Prophet Exchange", "Sporttrade", "Novig", "SportX", "Orbit Exchange",
  "Betconnect",
  // Prediction markets
  "Kalshi", "Polymarket", "PredictIt",
];

function fillNameDatalist(datalist, defaults, extra = []) {
  const seen = new Set();
  const items = [];
  for (const name of [...extra, ...defaults]) {
    const key = (name || "").trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    items.push(name.trim());
  }
  datalist.innerHTML = items.map(s => `<option value="${esc(s)}">`).join("");
}

function fillSportDatalist(datalist, extra = []) {
  fillNameDatalist(datalist, SPORTS, extra);
}

function fillBookmakerDatalist(datalist, extra = []) {
  fillNameDatalist(datalist, BOOKMAKERS, extra);
}

/* ----------------------------- API client ----------------------------- */
function token() { return localStorage.getItem(TOKEN_KEY); }
function setToken(value) {
  if (value) localStorage.setItem(TOKEN_KEY, value);
  else localStorage.removeItem(TOKEN_KEY);
}

async function api(path, { method = "GET", body, raw = false, allow401 = false, timeoutMs = 15000 } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  const authToken = token();
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw new Error(translate("errors.requestTimeout"));
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (res.status === 401 && !allow401) { setToken(null); showAuth(); throw new Error(translate("auth.sessionExpired")); }
  if (!res.ok) {
    let detail = res.statusText;
    const text = await res.text();
    if (text) {
      try {
        detail = JSON.parse(text).detail ?? detail;
      } catch {
        detail = text;
      }
    }
    throw new Error(apiErrorMessage(detail));
  }
  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

/* ------------------------------- helpers ------------------------------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const ccy = () => state.user?.base_currency || "GBP";

function money(v, withSign = false) {
  if (v == null) return "—";
  const n = Number(v);
  const s = i18n.formatLocaleNumber(n, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (withSign && n > 0 ? "+" : "") + s;
}
function plClass(v) { return v > 0 ? "pl-pos" : v < 0 ? "pl-neg" : "pl-zero"; }
function pct(v) { return v == null ? "—" : `${Number(v).toFixed(2)}%`; }
function esc(s) { return (s ?? "").toString().replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function formatDt(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const tzOpt = state.user?.timezone ? { timeZone: state.user.timezone } : {};
  const date = i18n.formatLocaleDate(d, { day: "2-digit", month: "short", year: "numeric", ...tzOpt });
  const time = i18n.formatLocaleTime(d, { hour: "2-digit", minute: "2-digit", ...tzOpt });
  return `${date} ${time}`;
}

function toast(msg, isErr = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast" + (isErr ? " toast--err" : "");
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.hidden = true), 2600);
}

function getShareToken() {
  if (window.__MBR_SHARE_TOKEN) return window.__MBR_SHARE_TOKEN;
  const pathMatch = location.pathname.match(/\/share\/([^/]+)/);
  if (pathMatch) return pathMatch[1];
  const parts = (location.hash || "").slice(1).split("/").filter(Boolean);
  return parts[0] === "share" && parts[1] ? parts[1] : null;
}

function getResetTokenFromHash() {
  const parts = (location.hash || "").slice(1).split("/").filter(Boolean);
  return parts[0] === "reset-password" && parts[1] ? parts[1] : null;
}

function getAuthRouteFromHash() {
  const parts = (location.hash || "").slice(1).split("/").filter(Boolean);
  const route = parts[0] || "login";
  if (route === "forgot-password") return "forgot";
  if (route === "reset-password") return "reset";
  if (route === "register") return "register";
  return "login";
}

function shareLink(token) {
  return `${location.origin}/share/${token}`;
}

async function publicApi(path) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  let res;
  try {
    res = await fetch(path, { signal: ctrl.signal });
  } catch (err) {
    if (err.name === "AbortError") throw new Error(translate("errors.requestTimeout"));
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    let detail = res.statusText;
    const text = await res.text();
    if (text) {
      try { detail = JSON.parse(text).detail ?? detail; } catch { detail = text; }
    }
    throw new Error(apiErrorMessage(detail));
  }
  return res.json();
}

function hideAllShells() {
  const app = $("#app"), auth = $("#auth"), loading = $("#authLoading"), share = $("#shareView");
  if (app) app.hidden = true;
  if (auth) auth.hidden = true;
  if (loading) loading.hidden = true;
  if (share) share.hidden = true;
}

function showShareView() {
  hideAllShells();
  const share = $("#shareView");
  if (!share) return;
  share.hidden = false;
  if (window.i18n) i18n.applyI18n(share);
}

/* -------------------------------- auth -------------------------------- */
function showAuthLoading() {
  const app = $("#app"), auth = $("#auth"), loading = $("#authLoading");
  if (app) app.hidden = true;
  if (auth) auth.hidden = true;
  if (loading) loading.hidden = false;
}
function showAuth(message = null, { success = null } = {}) {
  const app = $("#app"), auth = $("#auth"), loading = $("#authLoading");
  if (app) app.hidden = true;
  if (loading) loading.hidden = true;
  if (!auth) return;
  auth.hidden = false;
  if (window.i18n) i18n.applyI18n(auth);
  showAuthMode(getAuthRouteFromHash());
  const err = $("#authError");
  const ok = $("#authSuccess");
  if (err) err.hidden = true;
  if (ok) ok.hidden = true;
  if (message && err) { err.textContent = message; err.hidden = false; }
  if (success && ok) { ok.textContent = success; ok.hidden = false; }
}

function showAuthMode(mode) {
  const seg = document.querySelector("#auth .seg");
  const login = $("#loginForm"), reg = $("#registerForm");
  const forgot = $("#forgotPasswordForm"), reset = $("#resetPasswordForm");
  const showTabs = mode === "login" || mode === "register";
  if (seg) seg.hidden = !showTabs;
  if (login) login.hidden = mode !== "login";
  if (reg) reg.hidden = mode !== "register";
  if (forgot) forgot.hidden = mode !== "forgot";
  if (reset) reset.hidden = mode !== "reset";
  if (showTabs) {
    $$("[data-auth-tab]").forEach(btn => {
      btn.classList.toggle("is-active", btn.dataset.authTab === mode);
    });
  }
}
function showApp() {
  const auth = $("#auth"), loading = $("#authLoading"), app = $("#app");
  if (auth) auth.hidden = true;
  if (loading) loading.hidden = true;
  if (!app) return;
  app.hidden = false;
  if (window.i18n) i18n.applyI18n(app);
  updateAdminNav();
}

function updateAdminNav() {
  const tab = document.querySelector('.tab[data-view="admin"]');
  if (tab) tab.hidden = !state.user?.is_admin;
}

function bindEvents() {
  $$("[data-auth-tab]").forEach(btn => btn.addEventListener("click", () => {
    const tab = btn.dataset.authTab;
    location.hash = tab === "register" ? "#/register" : "#/login";
  }));

  document.querySelector("#auth")?.addEventListener("click", e => {
    const back = e.target.closest("[data-auth-back]");
    if (back) {
      e.preventDefault();
      location.hash = "#/login";
    }
  });

  window.addEventListener("hashchange", () => {
    if (getShareToken()) return;
    if (state.user) route();
    else showAuth();
  });

  const loginForm = $("#loginForm");
  if (loginForm) loginForm.addEventListener("submit", async e => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    $("#authError").hidden = true;
    $("#authSuccess").hidden = true;
    showAuthLoading();
    try {
      const { access_token } = await api("/auth/login", { method: "POST", body: f, allow401: true });
      setToken(access_token);
      await boot({ loading: true });
    } catch {
      showAuth(t("auth.loginFailed"));
    }
  });

  const registerForm = $("#registerForm");
  if (registerForm) registerForm.addEventListener("submit", async e => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    if (!f.display_name) delete f.display_name;
    f.timezone = browserTimeZone();
    try {
      showAuthLoading();
      const { access_token } = await api("/auth/register", { method: "POST", body: f });
      setToken(access_token);
      await boot({ loading: true });
    } catch (err) {
      const msg = err.message === "Email already registered"
        ? t("auth.emailAlreadyRegistered")
        : (err.message || t("errors.requestFailed"));
      showAuth(msg);
    }
  });

  const forgotPasswordForm = $("#forgotPasswordForm");
  if (forgotPasswordForm) forgotPasswordForm.addEventListener("submit", async e => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    $("#authError").hidden = true;
    $("#authSuccess").hidden = true;
    try {
      showAuthLoading();
      const res = await api("/auth/password-reset/request", { method: "POST", body: f, allow401: true });
      showAuth(null, { success: res.message || t("auth.resetLinkSent") });
      e.target.reset();
    } catch (err) {
      showAuth();
      authError(err.message);
    }
  });

  const resetPasswordForm = $("#resetPasswordForm");
  if (resetPasswordForm) resetPasswordForm.addEventListener("submit", async e => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    if (f.password !== f.password_confirm) {
      showAuth();
      authError(t("auth.passwordMismatch"));
      return;
    }
    const token = getResetTokenFromHash();
    if (!token) {
      showAuth();
      authError(t("auth.resetLinkInvalid"));
      return;
    }
    $("#authError").hidden = true;
    $("#authSuccess").hidden = true;
    try {
      showAuthLoading();
      const res = await api("/auth/password-reset/confirm", {
        method: "POST",
        body: { token, password: f.password },
        allow401: true,
      });
      location.hash = "#/login";
      showAuth(null, { success: res.message || t("auth.passwordUpdated") });
      e.target.reset();
    } catch (err) {
      showAuth();
      authError(err.message || t("auth.resetLinkInvalid"));
    }
  });

  const logoutBtn = $("#logoutBtn");
  if (logoutBtn) logoutBtn.addEventListener("click", () => { setToken(null); showAuth(); location.hash = "#/login"; });
}

function authError(msg) {
  const el = $("#authError"), ok = $("#authSuccess");
  if (ok) ok.hidden = true;
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
}

/* ------------------------------- ticker ------------------------------- */
async function refreshTicker() {
  try {
    const s = await api("/reports/summary?use_primary_currency=true");
    if (state.user && s.bankroll != null) state.user.bankroll = s.bankroll;
    $("#tkBankroll").textContent = s.bankroll ? money(s.bankroll) : "—";
    const pl = $("#tkPL");
    pl.textContent = money(s.profit, true);
    pl.className = "num " + plClass(s.profit);
    const plLabel = pl.closest(".ticker__item")?.querySelector(".ticker__label");
    if (plLabel) plLabel.textContent = s.currency ? t("ticker.plCurrency", { currency: s.currency }) : t("ticker.pl");
    $("#tkYield").textContent = pct(s.yield_pct);
  } catch {}
}

/* ------------------------------- router ------------------------------- */
const routes = {
  "/bets": renderBets,
  "/new": () => renderForm(null),
  "/reports": renderReports,
  "/settings": renderSettings,
  "/admin": renderAdmin,
};

async function route() {
  const shareToken = getShareToken();
  if (shareToken) {
    await renderPublicShare(shareToken);
    return;
  }
  if (!state.user) return;
  showApp();
  const hash = location.hash || "#/bets";
  const [path, id] = hash.slice(1).split("/").filter(Boolean).reduce((a, p, i) => (i === 0 ? ["/" + p] : [a[0], p]), ["", ""]);
  if (path === "/admin" && !state.user.is_admin) {
    location.hash = "#/bets";
    return;
  }
  $$(".tab").forEach(t => t.classList.toggle("is-active", t.getAttribute("href") === `#${path}`));

  if (path === "/edit" && id) return renderForm(id);
  const handler = routes[path] || renderBets;
  await handler();
}

/* -------------------------------- boot -------------------------------- */
async function boot({ loading = false } = {}) {
  if (loading) showAuthLoading();
  try {
    state.user = await api("/auth/me");
    await i18n.setLocale(state.user.preferred_locale || "en", { persistCookie: true });
    showApp();
    await refreshTicker();
    if (!location.hash) location.hash = "#/bets";
    await route();
  } catch {
    setToken(null);
    showAuth();
  }
}

/* ============================ Bets list ============================ */
async function renderBets() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-bets"));

  state.sports = await api("/bets/sports").catch(() => []);
  state.betTypes = await api("/bets/bet-types").catch(() => []);
  buildBetFilters();
  await Promise.all([loadBets(), loadUsageBanner()]);
}

async function loadUsageBanner() {
  const banner = $("#usageBanner");
  if (!banner) return;
  let usage;
  try {
    usage = await api("/bets/usage");
  } catch {
    banner.hidden = true;
    return;
  }
  if (!usage || usage.limit == null) {  // Pro / unlimited
    banner.hidden = true;
    return;
  }
  const reached = usage.remaining <= 0;
  banner.className = "usage-banner" + (reached ? " usage-banner--full" : "");
  banner.innerHTML = `
    <span>${esc(t("plan.betsToday", { count: usage.count, limit: usage.limit }))}</span>
    <a href="#/settings" class="usage-banner__cta">${esc(t(reached ? "plan.limitReached" : "plan.upgradeCta"))}</a>`;
  banner.hidden = false;
}

function currentFilters(prefix) {
  const root = $(`#${prefix}`);
  const f = {};
  $$("select, input", root).forEach(el => { if (el.value) f[el.name] = el.value; });
  return f;
}

function qs(f) {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => v && p.set(k, v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

function buildBetFilters() {
  const root = $("#betsFilters");
  root.innerHTML = `
    <label>${t("bets.sport")}<select name="sport"><option value="">${t("bets.all")}</option>${state.sports.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
    <label>${t("bets.result")}<select name="outcome"><option value="">${t("bets.all")}</option><option value="win">${t("outcomes.win")}</option><option value="loss">${t("outcomes.loss")}</option><option value="void">${t("outcomes.void")}</option><option value="pending">${t("outcomes.pending")}</option></select></label>
    <label>${t("bets.type")}<select name="bet_type">${betTypeFilterOptions()}</select></label>
    <label>${t("bets.from")}<input type="date" name="date_from" /></label>
    <label>${t("bets.to")}<input type="date" name="date_to" /></label>`;
  $$("select, input", root).forEach(el => el.addEventListener("change", loadBets));
}

const BET_OUTCOMES = ({ eachWay = false } = {}) => {
  const all = [
    { value: "pending", label: t("outcomes.pending") },
    { value: "win", label: t("outcomes.win") },
    { value: "placed", label: t("outcomes.placed") },
    { value: "loss", label: t("outcomes.loss") },
    { value: "void", label: t("outcomes.void") },
    { value: "half_win", label: t("outcomes.half_win") },
    { value: "half_loss", label: t("outcomes.half_loss") },
  ];
  if (eachWay) return all.filter(o => o.value !== "half_win" && o.value !== "half_loss");
  return all.filter(o => o.value !== "placed");
};

function displayOutcome(bet) {
  const outcome = bet.outcome || "pending";
  if (bet.each_way && bet.placed && outcome === "loss") return "placed";
  return outcome;
}

function syncOutcomeOptions(form) {
  if (!form?.outcome) return;
  const eachWay = form.each_way?.checked;
  const prev = form.outcome.value || "pending";
  const valid = new Set(BET_OUTCOMES({ eachWay }).map(o => o.value));
  form.outcome.innerHTML = BET_OUTCOMES({ eachWay }).map(o =>
    `<option value="${esc(o.value)}">${esc(o.label)}</option>`
  ).join("");
  form.outcome.value = valid.has(prev) ? prev : "pending";
}

async function loadBets() {
  const bets = await api("/bets" + qs(currentFilters("betsFilters")));
  const body = $("#betsBody");
  $("#betsEmpty").hidden = bets.length > 0;
  body.innerHTML = bets.map(betRow).join("");
  $$("[data-del]", body).forEach(b => b.addEventListener("click", () => deleteBet(b.dataset.del)));
  $$("[data-share]", body).forEach(b => b.addEventListener("click", () => copyShareLinkForBet(b.dataset.share, b)));
  $$("[data-outcome]", body).forEach(sel => {
    sel.dataset.prev = sel.value;
    sel.addEventListener("change", () => quickSetOutcome(sel));
  });
}

function outcomeTone(o) {
  const map = { win: "win", placed: "win", loss: "loss", void: "void", pending: "pending", half_win: "win", half_loss: "loss", cashed_out: "void" };
  return map[o] || "pending";
}

function outcomeSelect(b) {
  const shown = displayOutcome(b);
  const tone = outcomeTone(shown);
  const opts = BET_OUTCOMES({ eachWay: b.each_way }).map(o =>
    `<option value="${o.value}"${o.value === shown ? " selected" : ""}>${esc(o.label)}</option>`
  ).join("");
  return `<select class="mini-select outcome-select outcome-select--${tone}" data-outcome="${b.id}" aria-label="${esc(t("bets.resultAria", { name: b.selection }))}">${opts}</select>`;
}

const ICON_EDIT = `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;
const ICON_DELETE = `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
const ICON_SHARE = `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>`;

function betRow(b) {
  const d = new Date(b.placed_at);
  const date = i18n.formatLocaleDate(d, { day: "2-digit", month: "short", year: "2-digit" });
  const layBadge = b.side === "lay" ? ` <span class="pill pill--lay">${esc(t("form.sideLay"))}</span>` : "";
  const label = esc(b.selection) + layBadge;
  return `<tr>
    <td class="num">${date}</td>
    <td>${esc(b.sport)}</td>
    <td>${esc(b.event)}<div class="sel">${label}</div></td>
    <td>${esc(betTypeLabel(b.bet_type))}</td>
    <td class="r">${Number(b.odds_decimal).toFixed(2)}</td>
    <td class="r">${money(b.stake)}</td>
    <td>${outcomeSelect(b)}</td>
    <td class="r ${plClass(b.profit)}">${money(b.profit, true)}</td>
    <td class="r">${b.clv_pct == null ? "—" : pct(b.clv_pct)}</td>
    <td class="r"><div class="row-actions">
      <button type="button" class="icon-btn icon-btn--share" data-share="${b.id}" aria-label="${esc(t("bets.shareAria", { name: b.selection }))}">${ICON_SHARE}</button>
      <a class="icon-btn icon-btn--edit" href="#/edit/${b.id}" aria-label="${esc(t("bets.editAria", { name: b.selection }))}">${ICON_EDIT}</a>
      <button type="button" class="icon-btn icon-btn--delete" data-del="${b.id}" aria-label="${esc(t("bets.deleteAria", { name: b.selection }))}">${ICON_DELETE}</button>
    </div></td>
  </tr>`;
}

async function quickSetOutcome(sel) {
  const id = sel.dataset.outcome;
  const prev = sel.dataset.prev;
  const outcome = sel.value;
  if (outcome === prev) return;
  sel.disabled = true;
  try {
    await api(`/bets/${id}`, { method: "PATCH", body: { outcome } });
    await Promise.all([loadBets(), refreshTicker()]);
  } catch (err) {
    sel.value = prev;
    toast(err.message, true);
    sel.disabled = false;
  }
}

async function deleteBet(id) {
  if (!confirm(t("bets.deleteConfirm"))) return;
  await api(`/bets/${id}`, { method: "DELETE" });
  toast(t("bets.deleted"));
  await Promise.all([loadBets(), refreshTicker()]);
}

async function enableBetShare(id) {
  const { share_token } = await api(`/bets/${id}/share`, { method: "POST" });
  return share_token;
}

async function copyShareLinkForBet(id, btn) {
  if (btn) btn.disabled = true;
  try {
    const token = await enableBetShare(id);
    await copyText(shareLink(token));
    toast(t("share.linkCopied"));
  } catch (err) {
    toast(err.message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
}

async function revokeBetShare(id) {
  if (!confirm(t("share.revokeConfirm"))) return;
  try {
    await api(`/bets/${id}/share`, { method: "DELETE" });
    toast(t("share.linkRevoked"));
    return true;
  } catch (err) {
    toast(err.message, true);
    return false;
  }
}

function formatPublicOdds(b) {
  const fmt = b.odds_format || "decimal";
  const formatted = formatOddsFromDecimal(Number(b.odds_decimal), fmt);
  if (fmt === "fractional" && formatted.denominator) {
    return `${formatted.odds}/${formatted.denominator}`;
  }
  return formatted.odds || Number(b.odds_decimal).toFixed(2);
}

function formatPublicDt(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const date = i18n.formatLocaleDate(d, { day: "2-digit", month: "short", year: "numeric" });
  const time = i18n.formatLocaleTime(d, { hour: "2-digit", minute: "2-digit" });
  return `${date} ${time}`;
}

function shareDetailRow(label, value, { mono = false, notes = false } = {}) {
  const cls = [mono ? "num" : "", notes ? "share-detail__notes" : ""].filter(Boolean).join(" ");
  return `<div class="share-detail__row"><dt>${esc(label)}</dt><dd class="${cls}">${value}</dd></div>`;
}

async function renderPublicShare(token) {
  showShareView();
  const main = $("#shareMain");
  main.innerHTML = "";
  main.appendChild(clone("tpl-share"));
  const detail = $("#shareDetail");
  try {
    const b = await publicApi(`/bets/public/${encodeURIComponent(token)}`);
    detail.innerHTML = [
      shareDetailRow(t("form.sport"), esc(b.sport)),
      shareDetailRow(t("form.betType"), esc(betTypeLabel(b.bet_type))),
      ...(b.tournament ? [shareDetailRow(t("form.tournament"), esc(b.tournament))] : []),
      shareDetailRow(t("form.event"), esc(b.event)),
      shareDetailRow(t("form.eventAt"), esc(formatPublicDt(b.event_at))),
      shareDetailRow(t("form.selection"), esc(b.selection)),
      shareDetailRow(t("form.stake"), esc(`${money(b.stake)} ${b.currency}`), { mono: true }),
      shareDetailRow(t("bets.odds"), esc(formatPublicOdds(b)), { mono: true }),
      shareDetailRow(t("form.currency"), esc(b.currency)),
      shareDetailRow(
        t("form.personalImplied"),
        b.personal_implied_odds == null ? "—" : esc(Number(b.personal_implied_odds).toFixed(2)),
        { mono: true }
      ),
      shareDetailRow(t("form.notes"), esc(b.notes || "—"), { notes: true }),
    ].join("");
  } catch {
    detail.innerHTML = `<p class="empty">${esc(t("share.notFound"))}</p>`;
  }
}

function mountShareControls(container, betId, shareToken) {
  container.innerHTML = `
    <fieldset>
      <legend data-i18n="share.shareSection">Share link</legend>
      <p class="hint" data-i18n="share.shareHint">Create a read-only link others can open without signing in.</p>
      <div class="share-actions">
        <button type="button" class="btn btn--ghost btn--sm" id="shareCopyBtn" data-i18n="share.copyLink">Copy link</button>
        <button type="button" class="btn btn--ghost btn--sm" id="shareRevokeBtn" data-i18n="share.revokeLink" ${shareToken ? "" : "hidden"}>Revoke link</button>
      </div>
    </fieldset>`;
  if (window.i18n) i18n.applyI18n(container);
  let token = shareToken;
  $("#shareCopyBtn", container).addEventListener("click", async () => {
    try {
      if (!token) token = await enableBetShare(betId);
      await copyText(shareLink(token));
      toast(t("share.linkCopied"));
      $("#shareRevokeBtn", container).hidden = false;
    } catch (err) {
      toast(err.message, true);
    }
  });
  $("#shareRevokeBtn", container).addEventListener("click", async () => {
    const ok = await revokeBetShare(betId);
    if (ok) {
      token = null;
      $("#shareRevokeBtn", container).hidden = true;
    }
  });
}

/* ============================ Bet form ============================ */
async function renderForm(id) {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-form"));
  state.sports = await api("/bets/sports").catch(() => []);
  state.betTypes = await api("/bets/bet-types").catch(() => []);
  fillSportDatalist($("#sportList"), state.sports);
  fillBookmakerDatalist($("#bookmakerList"));
  fillBetTypeDatalist($("#betTypeList"), state.betTypes);

  const form = $("#betForm");
  // default odds format from user settings
  const defaultFmt = state.user.default_odds_format || "decimal";
  form.odds_format.value = defaultFmt;
  form.odds_format.dataset.prev = defaultFmt;
  fillCurrencyDatalist($("#currencyList"), 50);
  form.currency.value = state.user.base_currency || "GBP";
  syncOddsFormat();
  syncEachWay();
  syncSideUI(form);
  syncOutcomeOptions(form);

  form.odds_format.addEventListener("change", onOddsFormatChange);
  form.side?.addEventListener("change", () => {
    syncSideUI(form);
    syncEachWay();
    syncOutcomeOptions(form);
    updateEffectiveOddsPreview(form);
    updateSettlementPreview(form);
  });
  form.each_way.addEventListener("change", () => { syncEachWay(); syncOutcomeOptions(form); updateSettlementPreview(form); });
  ["odds", "odds_denominator", "personal_implied_odds", "model_implied_odds"].forEach(n => {
    const el = form.elements.namedItem(n);
    if (el) el.addEventListener("input", () => {
      updateModellingCalcs(form);
      updateEffectiveOddsPreview(form);
      updateLiabilityPreview(form);
    });
  });
  ["stake", "cash_out_amount", "place_fraction", "exchange_commission_pct"].forEach(n => {
    const el = form.elements.namedItem(n);
    if (el) el.addEventListener("input", () => {
      updateSettlementPreview(form);
      updateLiabilityPreview(form);
      if (n === "exchange_commission_pct") updateEffectiveOddsPreview(form);
    });
  });
  form.outcome?.addEventListener("change", () => {
    autoFillSettledDate(form);
    updateSettlementPreview(form);
  });
  updateModellingCalcs(form);
  updateEffectiveOddsPreview(form);
  updateLiabilityPreview(form);
  updateSettlementPreview(form);

  if (!id) form.placed_at.value = localDatetimeInputValue();

  let editing = null;
  if (id) {
    $("#formTitle").textContent = t("form.editTitle");
    $("#saveBtn").textContent = t("form.saveChanges");
    editing = await api(`/bets/${id}`);
    fillForm(form, editing);
    syncOddsFormat(); syncEachWay(); syncSideUI(form); syncOutcomeOptions(form); updateModellingCalcs(form); updateEffectiveOddsPreview(form); updateLiabilityPreview(form); updateSettlementPreview(form);
    const shareHost = document.createElement("div");
    form.querySelector(".formactions").before(shareHost);
    mountShareControls(shareHost, editing.id, editing.share_token);
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const payload = readForm(form);
    if (!payload.currency || !/^[A-Z]{3}$/.test(payload.currency)) {
      toast(t("form.invalidCurrency"), true);
      return;
    }
    const cashOut = payload.cash_out_amount;
    const maxReturn = maxCashOutReturn(form);
    if (cashOut != null && maxReturn != null && cashOut > maxReturn + 0.001) {
      toast(t("form.cashOutExceedsMax"), true);
    }
    try {
      if (editing) await api(`/bets/${editing.id}`, { method: "PATCH", body: payload });
      else await api("/bets", { method: "POST", body: payload });
      toast(editing ? t("form.betUpdated") : t("form.betRecorded"));
      await refreshTicker();
      location.hash = "#/bets";
    } catch (err) { toast(err.message, true); }
  });
}

const ODDS_LABELS = () => ({
  decimal: t("form.decimalOdds"),
  american: t("form.americanOdds"),
  fractional: t("form.numerator"),
  hong_kong: t("form.hongKongOdds"),
  malaysian: t("form.malaysianOdds"),
  indonesian: t("form.indonesianOdds"),
});

function parseSignedOdds(raw) {
  const text = String(raw || "").trim().replace(/^\+/, "");
  if (!text) return NaN;
  const n = parseFloat(text);
  return Number.isFinite(n) ? n : NaN;
}

function signedAsianToDecimal(o) {
  if (!Number.isFinite(o) || o === 0) return NaN;
  return o > 0 ? 1 + o : 1 + 1 / Math.abs(o);
}

function decimalToSignedAsian(d, positiveWhenUnderEvens) {
  if (!(d > 1)) return "";
  const o = positiveWhenUnderEvens
    ? (d <= 2 ? d - 1 : -1 / (d - 1))
    : (d >= 2 ? d - 1 : -1 / (d - 1));
  const rounded = Math.round(o * 10000) / 10000;
  return (rounded > 0 ? "+" : "") + String(rounded);
}

function gcd(a, b) {
  a = Math.abs(Math.round(a));
  b = Math.abs(Math.round(b));
  while (b) { const t = b; b = a % b; a = t; }
  return a || 1;
}

function decimalToAmerican(d) {
  if (!(d > 1)) return "";
  if (d >= 2) return "+" + Math.round((d - 1) * 100);
  return String(Math.round(-100 / (d - 1)));
}

function decimalToFractionalParts(d, maxDen = 100) {
  const x = d - 1;
  let bestNum = 1, bestDen = 1, bestErr = Math.abs(x - 1);
  for (let den = 1; den <= maxDen; den++) {
    const num = Math.round(x * den);
    const err = Math.abs(x - num / den);
    if (err < bestErr) { bestErr = err; bestNum = num; bestDen = den; }
  }
  const g = gcd(bestNum, bestDen);
  return { numerator: bestNum / g, denominator: bestDen / g };
}

function parseOddsToDecimal(form, format = form.odds_format.value) {
  const raw = String(form.odds.value || "").trim();
  if (!raw) return NaN;
  if (format === "decimal") return parseFloat(raw);
  if (format === "american") {
    const a = parseSignedOdds(raw);
    if (!Number.isFinite(a) || a === 0) return NaN;
    return a > 0 ? 1 + a / 100 : 1 + 100 / Math.abs(a);
  }
  if (format === "hong_kong") {
    const hk = parseFloat(raw);
    if (!Number.isFinite(hk) || hk < 0) return NaN;
    return 1 + hk;
  }
  if (format === "malaysian" || format === "indonesian") {
    return signedAsianToDecimal(parseSignedOdds(raw));
  }
  const num = parseFloat(raw);
  const den = parseFloat(form.odds_denominator.value);
  if (!Number.isFinite(num) || !Number.isFinite(den) || den === 0) return NaN;
  return 1 + num / den;
}

function formatOddsFromDecimal(d, format) {
  if (!(d > 1)) return { odds: "" };
  if (format === "decimal") return { odds: d.toFixed(2) };
  if (format === "american") return { odds: decimalToAmerican(d) };
  if (format === "hong_kong") return { odds: (Math.round((d - 1) * 10000) / 10000).toFixed(2) };
  if (format === "malaysian") return { odds: decimalToSignedAsian(d, true) };
  if (format === "indonesian") return { odds: decimalToSignedAsian(d, false) };
  const { numerator, denominator } = decimalToFractionalParts(d);
  return { odds: String(numerator), denominator: String(denominator) };
}

function onOddsFormatChange() {
  const form = $("#betForm");
  const prev = form.odds_format.dataset.prev || form.odds_format.value;
  const next = form.odds_format.value;
  const dec = parseOddsToDecimal(form, prev);
  if (dec > 1) {
    const formatted = formatOddsFromDecimal(dec, next);
    form.odds.value = formatted.odds;
    form.odds_denominator.value = next === "fractional" ? (formatted.denominator || "") : "";
  } else if (next !== "fractional") {
    form.odds_denominator.value = "";
  }
  form.odds_format.dataset.prev = next;
  syncOddsFormat();
  updateModellingCalcs($("#betForm"));
  updateEffectiveOddsPreview($("#betForm"));
  updateLiabilityPreview($("#betForm"));
  updateSettlementPreview($("#betForm"));
}

function effectiveDecimalOdds(oddsDec, commissionPct) {
  if (!(oddsDec > 1) || !Number.isFinite(commissionPct) || commissionPct <= 0) return NaN;
  return 1 + (oddsDec - 1) * (1 - commissionPct / 100);
}

function updateEffectiveOddsPreview(form = $("#betForm")) {
  if (!form) return;
  const hint = form.querySelector("#effectiveOddsHint");
  if (!hint) return;
  if (isLaySide(form)) {
    hint.hidden = true;
    return;
  }
  const valueEl = hint.querySelector('[data-role="effective-odds"]');
  const commission = parseFloat(form.exchange_commission_pct?.value);
  const oddsDec = parseOddsToDecimal(form);
  const effDec = effectiveDecimalOdds(oddsDec, commission);

  if (!Number.isFinite(effDec) || !(effDec > 1)) {
    hint.hidden = true;
    return;
  }

  const fmt = form.odds_format.value;
  const formatted = formatOddsFromDecimal(effDec, fmt);
  if (valueEl) {
    valueEl.textContent = fmt === "fractional" && formatted.denominator
      ? `${formatted.odds}/${formatted.denominator}`
      : formatted.odds;
  }
  hint.hidden = false;
}

function syncOddsFormat() {
  const form = $("#betForm");
  const fmt = form.odds_format.value;
  const frac = fmt === "fractional";
  const fields = form.querySelector("#oddsValueFields");
  fields.className = `odds-value-fields odds-value-fields--${fmt}`;
  const oddsInput = form.odds;
  form.querySelector("#oddsFieldLabel").textContent = ODDS_LABELS()[fmt] || t("bets.odds");
  oddsInput.required = true;
  form.odds_denominator.required = frac;
  if (!frac) form.odds_denominator.value = "";
  if (fmt === "american") {
    oddsInput.placeholder = t("form.oddsPlaceholderAmerican");
    oddsInput.inputMode = "text";
  } else if (fmt === "malaysian") {
    oddsInput.placeholder = t("form.oddsPlaceholderMalaysian");
    oddsInput.inputMode = "text";
  } else if (fmt === "indonesian") {
    oddsInput.placeholder = t("form.oddsPlaceholderIndonesian");
    oddsInput.inputMode = "text";
  } else if (fmt === "hong_kong") {
    oddsInput.placeholder = t("form.oddsPlaceholderHongKong");
    oddsInput.inputMode = "decimal";
  } else if (frac) {
    oddsInput.placeholder = t("form.oddsPlaceholderFractional");
    oddsInput.inputMode = "decimal";
  } else {
    oddsInput.placeholder = t("form.oddsPlaceholderDecimal");
    oddsInput.inputMode = "decimal";
  }
}
function syncEachWay() {
  const form = $("#betForm");
  const lay = isLaySide(form);
  if (lay) {
    form.each_way.checked = false;
    form.each_way.disabled = true;
  } else {
    form.each_way.disabled = false;
  }
  $("#ewFields").hidden = !form.each_way.checked;
}

function isLaySide(form) {
  return (form?.side?.value || "back") === "lay";
}

function computeLayLiability(stake, oddsDec) {
  if (!Number.isFinite(stake) || stake <= 0 || !Number.isFinite(oddsDec) || oddsDec <= 1) return null;
  return Math.round(stake * (oddsDec - 1) * 100) / 100;
}

function syncSideUI(form = $("#betForm")) {
  if (!form) return;
  const lay = isLaySide(form);
  const legend = form.querySelector("#betDetailsLegend");
  if (legend) legend.textContent = t(lay ? "form.whatYouLay" : "form.whatYouBacked");
  const stakeLabel = form.querySelector("#stakeFieldLabel");
  const stakeHint = form.querySelector("#stakeFieldHint");
  if (stakeLabel) stakeLabel.textContent = t(lay ? "form.backersStake" : "form.stake");
  if (stakeHint) stakeHint.hidden = !lay;
  updateLiabilityPreview(form);
}

function updateLiabilityPreview(form = $("#betForm")) {
  if (!form) return;
  const preview = form.querySelector("#liabilityPreview");
  if (!preview) return;
  if (!isLaySide(form)) {
    preview.hidden = true;
    return;
  }
  const stake = parseFloat(form.stake?.value);
  const oddsDec = parseOddsToDecimal(form);
  const liability = computeLayLiability(stake, oddsDec);
  const valueEl = preview.querySelector('[data-role="liability"]');
  if (liability == null || !valueEl) {
    preview.hidden = true;
    return;
  }
  const currency = (form.currency?.value || "GBP").trim().toUpperCase() || "GBP";
  valueEl.textContent = `${liability.toFixed(2)} ${currency}`;
  preview.hidden = false;
}

function edgePctFromImplied(oddsDec, impliedDec) {
  if (!(oddsDec > 1) || !(impliedDec > 1)) return null;
  const p = 1 / impliedDec;
  return (p * (oddsDec - 1) - (1 - p)) * 100;
}

function kellyFromImplied(oddsDec, impliedDec, bankroll, multiplier) {
  if (!(oddsDec > 1) || !(impliedDec > 1) || !(bankroll > 0)) return null;
  const b = oddsDec - 1, p = 1 / impliedDec, q = 1 - p;
  const f = Math.max(0, (b * p - q) / b) * (multiplier || 1);
  return { fraction: f, stake: f * bankroll };
}

function updateCalcBlock(form, kind, implied, oddsDec, bankroll, mult, currency) {
  const block = form.querySelector(`[data-calc="${kind}"]`);
  if (!block) return;
  const hasImplied = Number.isFinite(implied) && implied > 1;
  block.hidden = !hasImplied;
  if (!hasImplied) return;

  const edgeVal = block.querySelector('[data-role="edge"]');
  const kellyWrap = block.querySelector('[data-role="kelly-wrap"]');
  const kellyVal = block.querySelector('[data-role="kelly"]');
  const edge = edgePctFromImplied(oddsDec, implied);
  if (edgeVal) {
    edgeVal.textContent = edge != null
      ? t("form.edgeValue", { pct: edge.toFixed(2) })
      : t("form.edgeNeedsOdds");
  }
  const kelly = kellyFromImplied(oddsDec, implied, bankroll, mult);
  if (kellyWrap) {
    const showKelly = bankroll > 0 && oddsDec > 1;
    kellyWrap.hidden = !showKelly;
    if (showKelly && kellyVal) {
      kellyVal.textContent = kelly && kelly.fraction > 0
        ? t("form.kellySuggest", {
            stake: money(kelly.stake),
            currency,
            pct: (kelly.fraction * 100).toFixed(1),
          })
        : t("form.kellyNoEdge");
    }
  }
}

function updateModellingCalcs(form = $("#betForm")) {
  if (!form) return;
  const bankroll = Number(state.user?.bankroll) || 0;
  const mult = state.user?.kelly_multiplier || 1;
  const currency = ccy();
  const oddsDec = parseOddsToDecimal(form);
  const personal = parseFloat(form.elements.namedItem("personal_implied_odds")?.value);
  const model = parseFloat(form.elements.namedItem("model_implied_odds")?.value);
  updateCalcBlock(form, "personal", personal, oddsDec, bankroll, mult, currency);
  updateCalcBlock(form, "model", model, oddsDec, bankroll, mult, currency);
}

function localDatetimeInputValue(d = new Date()) {
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function isSettledOutcome(outcome) {
  return Boolean(outcome && outcome !== "pending");
}

function autoFillSettledDate(form) {
  if (!form?.settled_at || !isSettledOutcome(form.outcome?.value || "pending")) return;
  if (!String(form.settled_at.value || "").trim()) {
    form.settled_at.value = localDatetimeInputValue();
  }
}

function computeSettlementProfit(form) {
  const stake = parseFloat(form.stake?.value);
  const cashOutRaw = String(form.cash_out_amount?.value || "").trim();
  const cashOut = cashOutRaw ? parseFloat(cashOutRaw) : null;
  const outcome = form.outcome?.value || "pending";
  const eachWay = form.each_way?.checked;
  const placeFraction = parseFloat(form.place_fraction?.value) || 0.25;
  const commission = parseFloat(form.exchange_commission_pct?.value) || 0;
  const oddsDec = parseOddsToDecimal(form);

  if (!Number.isFinite(stake) || stake <= 0) return null;

  if (cashOut != null && Number.isFinite(cashOut)) {
    return Math.round((cashOut - stake) * 100) / 100;
  }

  if (outcome === "pending") return 0;
  if (outcome === "void") return 0;
  if (!Number.isFinite(oddsDec) || oddsDec <= 1) return 0;

  const lay = isLaySide(form);
  let gross = 0;
  if (lay) {
    if (outcome === "win") gross = stake;
    else if (outcome === "loss") gross = -(computeLayLiability(stake, oddsDec) || 0);
  } else if (!eachWay) {
    if (outcome === "win") gross = stake * (oddsDec - 1);
    else if (outcome === "half_win") gross = 0.5 * stake * (oddsDec - 1);
    else if (outcome === "half_loss") gross = -0.5 * stake;
    else if (outcome === "loss") gross = -stake;
  } else {
    const unit = stake / 2;
    const placeOdds = 1 + (oddsDec - 1) * placeFraction;
    if (outcome === "win") {
      gross = unit * (oddsDec - 1) + unit * (placeOdds - 1);
    } else if (outcome === "placed") {
      gross = -unit + unit * (placeOdds - 1);
    } else {
      gross = -stake;
    }
  }

  if (gross > 0 && commission) gross -= gross * (commission / 100);
  return Math.round(gross * 100) / 100;
}

function maxCashOutReturn(form) {
  const stake = parseFloat(form.stake?.value);
  const oddsDec = parseOddsToDecimal(form);
  if (!Number.isFinite(stake) || stake <= 0 || !Number.isFinite(oddsDec) || oddsDec <= 1) return null;
  return Math.round(stake * oddsDec * 100) / 100;
}

function updateSettlementPreview(form = $("#betForm")) {
  if (!form) return;
  const preview = form.querySelector("#settlementPreview");
  const warning = form.querySelector("#cashOutWarning");
  if (!preview) return;

  const outcome = form.outcome?.value || "pending";
  const cashOutRaw = String(form.cash_out_amount?.value || "").trim();
  const hasCashOut = cashOutRaw !== "";
  const settled = outcome !== "pending" || hasCashOut;
  const profit = computeSettlementProfit(form);

  if (!settled || profit == null) {
    preview.hidden = true;
    if (warning) warning.hidden = true;
    return;
  }

  const valueEl = preview.querySelector('[data-role="profit"]');
  if (valueEl) {
    valueEl.textContent = money(profit, true);
    valueEl.className = "settlement-preview__value " + plClass(profit);
  }
  preview.hidden = false;

  if (warning) {
    const cashOut = parseFloat(cashOutRaw);
    const maxReturn = maxCashOutReturn(form);
    warning.hidden = !(hasCashOut && Number.isFinite(cashOut) && maxReturn != null && cashOut > maxReturn + 0.001);
  }
}

function readDatetimeField(form, name) {
  const v = String(form[name]?.value || "").trim();
  return v ? new Date(v).toISOString() : new Date().toISOString();
}

function readOptionalDatetimeField(form, name) {
  const v = String(form[name]?.value || "").trim();
  return v ? new Date(v).toISOString() : null;
}

const NUM_FIELDS = ["odds", "odds_denominator", "stake", "place_fraction", "cash_out_amount",
  "model_implied_odds", "personal_implied_odds", "closing_odds", "closing_odds_exchange", "exchange_commission_pct"];

function readForm(form) {
  const data = Object.fromEntries(new FormData(form));
  const out = {};
  for (const [k, v] of Object.entries(data)) {
    if (v === "" || v == null) continue;
    out[k] = NUM_FIELDS.includes(k) ? Number(v) : v;
  }
  out.each_way = form.each_way.checked;
  const eachWay = out.each_way;
  out.placed = eachWay && (out.outcome === "win" || out.outcome === "placed");
  if (out.currency) out.currency = out.currency.trim().toUpperCase();
  if (out.bet_type) out.bet_type = out.bet_type.trim();
  out.placed_at = readDatetimeField(form, "placed_at");
  out.event_at = readOptionalDatetimeField(form, "event_at");
  out.settled_at = readDatetimeField(form, "settled_at");
  if (out.odds_format !== "fractional") delete out.odds_denominator;
  return out;
}

function fillForm(form, b) {
  const set = (n, v) => { if (form[n] != null && v != null) form[n].value = v; };
  set("sport", b.sport);
  if (form.side) form.side.value = b.side || "back";
  set("bet_type", BET_TYPE_LABELS[b.bet_type] || BET_TYPE_LABELS[b.bet_type?.toLowerCase()] || b.bet_type);
  set("tournament", b.tournament);
  set("event", b.event);
  set("selection", b.selection);
  set("event_at", b.event_at ? new Date(b.event_at).toISOString().slice(0, 16) : "");
  set("placed_at", b.placed_at ? new Date(b.placed_at).toISOString().slice(0, 16) : "");
  set("settled_at", b.outcome !== "pending" && b.settled_at
    ? new Date(b.settled_at).toISOString().slice(0, 16) : "");
  const fmt = b.odds_format || "decimal";
  form.odds_format.value = fmt;
  form.odds_format.dataset.prev = fmt;
  const formatted = formatOddsFromDecimal(Number(b.odds_decimal), fmt);
  set("odds", formatted.odds);
  if (fmt === "fractional") set("odds_denominator", formatted.denominator);
  else form.odds_denominator.value = "";
  set("stake", b.stake);
  set("currency", b.currency);
  form.each_way.checked = b.each_way;
  set("place_fraction", b.place_fraction);
  syncEachWay();
  syncOutcomeOptions(form);
  set("outcome", displayOutcome(b)); set("cash_out_amount", b.cash_out_amount);
  set("bet_model", b.bet_model); set("closing_odds", b.closing_odds);
  set("closing_odds_exchange", b.closing_odds_exchange);
  set("model_implied_odds", b.model_implied_odds);
  set("personal_implied_odds", b.personal_implied_odds);
  set("exchange_commission_pct", b.exchange_commission_pct);
  set("bookmaker", b.bookmaker);
  set("tipster", b.tipster); set("bet_broker", b.bet_broker); set("notes", b.notes);
}

/* ============================ Reports ============================ */
async function renderReports() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-reports"));

  [state.sports, state.betTypes, state.tipsters, state.currencies] = await Promise.all([
    api("/bets/sports").catch(() => []),
    api("/bets/bet-types").catch(() => []),
    api("/bets/tipsters").catch(() => []),
    api("/bets/currencies").catch(() => []),
  ]);
  buildReportFilters();
  $("#breakdownDim").addEventListener("change", loadBreakdown);
  $("#exportCsv").addEventListener("click", () => downloadExport("csv"));
  $("#exportXlsx").addEventListener("click", () => downloadExport("xlsx"));
  $("#exportJson").addEventListener("click", () => downloadExport("json"));
  await loadReports();
}

function buildReportFilters() {
  const root = $("#reportFilters");
  const currencyOpts = [
    `<option value="">${t("reports.allCurrencies")}</option>`,
    ...state.currencies.map(c => `<option value="${esc(c)}">${esc(c)}</option>`),
  ].join("");
  root.innerHTML = `
    <label>${t("bets.sport")}<select name="sport"><option value="">${t("bets.all")}</option>${state.sports.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
    <label>${t("bets.type")}<select name="bet_type">${betTypeFilterOptions()}</select></label>
    <label>${t("form.tipster")}<select name="tipster"><option value="">${t("bets.all")}</option>${state.tipsters.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
    <label>${t("form.currency")}<select name="currency">${currencyOpts}</select></label>
    <label>${t("bets.from")}<input type="date" name="date_from" /></label>
    <label>${t("bets.to")}<input type="date" name="date_to" /></label>`;
  const currencySelect = root.querySelector('[name="currency"]');
  if (state.currencies.length) currencySelect.value = state.currencies[0];
  $$("select, input", root).forEach(el => el.addEventListener("change", loadReports));
}

async function loadReports() {
  await Promise.all([loadSummary(), loadEquity(), loadBreakdown(), loadMonthly()]);
}

async function loadSummary() {
  const f = currentFilters("reportFilters");
  const s = await api("/reports/summary" + qs(f));
  const currencyNote = s.currency ? t("reports.currencyOnly", { currency: s.currency }) : t("reports.allCurrenciesNote");
  const cards = [
    [t("reports.profitLoss"), `<span class="${plClass(s.profit)}">${money(s.profit, true)}</span>`, t("reports.settled", { count: s.settled_bets, note: currencyNote })],
    [t("reports.roi"), pct(s.roi_pct), s.roi_vs_bankroll_pct != null ? t("reports.ofBankroll", { pct: pct(s.roi_vs_bankroll_pct) }) : t("reports.perUnitStaked")],
    [t("reports.yield"), pct(s.yield_pct), t("reports.turnover", { amount: money(s.turnover) })],
    [t("reports.strikeRate"), pct(s.strike_rate_pct), t("reports.wlv", { wins: s.wins, losses: s.losses, voids: s.voids })],
    [t("reports.totalBets"), String(s.total_bets), currencyNote],
  ];
  $("#metricCards").innerHTML = cards.map(([l, v, sub]) =>
    `<div class="card"><div class="card__label">${l}</div><div class="card__value">${v}</div><div class="card__sub">${sub}</div></div>`).join("");
}

function destroyChart(name) { if (state.charts[name]) { state.charts[name].destroy(); delete state.charts[name]; } }

function ensureChartJs() {
  if (typeof Chart !== "undefined") return Promise.resolve();
  if (window._chartJsLoading) return window._chartJsLoading;
  window._chartJsLoading = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load Chart.js"));
    document.head.appendChild(s);
  });
  return window._chartJsLoading;
}

async function loadEquity() {
  const f = currentFilters("reportFilters");
  const pts = await api("/reports/equity-curve" + qs(f));
  destroyChart("equity");
  const ctx = $("#equityChart");
  if (!ctx) return;
  try {
    await ensureChartJs();
  } catch {
    return;
  }
  if (typeof Chart === "undefined") return;
  state.charts.equity = new Chart(ctx, {
    type: "line",
    data: {
      labels: pts.map(p => i18n.formatLocaleDate(new Date(p.date), { day: "2-digit", month: "short" })),
      datasets: [{
        data: pts.map(p => p.cumulative),
        borderColor: "#a9791f", backgroundColor: "rgba(169,121,31,.10)",
        fill: true, tension: .25, pointRadius: 0, borderWidth: 2,
      }],
    },
    options: chartOpts(),
  });
}

async function loadMonthly() {
  const f = currentFilters("reportFilters");
  const pts = await api("/reports/equity-curve" + qs(f));
  const byMonth = {};
  pts.forEach(p => {
    const d = new Date(p.date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    byMonth[key] = (byMonth[key] || 0) + p.profit;
  });
  const keys = Object.keys(byMonth).sort();
  destroyChart("monthly");
  const ctx = $("#monthlyChart");
  if (!ctx) return;
  try {
    await ensureChartJs();
  } catch {
    return;
  }
  if (typeof Chart === "undefined") return;
  state.charts.monthly = new Chart(ctx, {
    type: "bar",
    data: {
      labels: keys,
      datasets: [{
        data: keys.map(k => Number(byMonth[k].toFixed(2))),
        backgroundColor: keys.map(k => byMonth[k] >= 0 ? "#157a52" : "#bd3a2b"),
        borderRadius: 3,
      }],
    },
    options: chartOpts(),
  });
}

function chartOpts() {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 } } },
      y: { grid: { color: "#eef0f3" }, ticks: { font: { family: "JetBrains Mono", size: 10 } } },
    },
  };
}

async function loadBreakdown() {
  const dim = $("#breakdownDim").value;
  const dimLabels = { sport: t("reports.dimSport"), tipster: t("reports.dimTipster"), bet_type: t("reports.dimBetType"), bookmaker: t("reports.dimBookmaker") };
  $("#dimHead").textContent = dimLabels[dim] || dim;
  const f = currentFilters("reportFilters");
  f.dimension = dim;
  const rows = await api("/reports/breakdown" + qs(f));
  const label = k => dim === "bet_type" ? betTypeLabel(k) : k;
  $("#breakdownBody").innerHTML = rows.map(r => `
    <tr><td>${esc(label(r.key))}</td>
    <td class="r num">${r.settled_bets}</td>
    <td class="r num">${pct(r.strike_rate_pct)}</td>
    <td class="r num">${pct(r.yield_pct)}</td>
    <td class="r num ${plClass(r.profit)}">${money(r.profit, true)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="empty">${t("reports.noSettled")}</td></tr>`;
}

async function downloadExport(kind) {
  const f = currentFilters("reportFilters");
  const res = await api(`/reports/export.${kind}` + qs(f), { raw: true });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `mybetrecord.${kind}`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

/* ============================ Settings ============================ */
async function renderSettings() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-settings"));

  const form = $("#settingsForm");
  const u = state.user;
  await i18n.loadCatalog();
  $("#localeSelect").innerHTML = i18n.languageOptions(u.preferred_locale || "en");
  fillTimezoneSelect($("#timezoneSelect"), u.timezone || "UTC");
  form.default_odds_format.value = u.default_odds_format;
  fillCurrencySelect(form.base_currency, 20, u.base_currency);
  form.bankroll.value = u.bankroll || "";
  form.kelly_multiplier.value = u.kelly_multiplier ?? 1;
  form.display_name.value = u.display_name || "";

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const payload = {
      preferred_locale: data.preferred_locale,
      timezone: data.timezone,
      default_odds_format: data.default_odds_format,
      base_currency: data.base_currency.toUpperCase(),
      bankroll: Number(data.bankroll || 0),
      kelly_multiplier: Number(data.kelly_multiplier || 1),
      display_name: data.display_name || null,
    };
    try {
      state.user = await api("/auth/settings", { method: "PATCH", body: payload });
      await i18n.setLocale(state.user.preferred_locale || "en", { persistCookie: true });
      toast(t("settings.saved"));
      await refreshTicker();
      await route();
    } catch (err) { toast(err.message, true); }
  });

  await handleBillingReturn();
  await renderPlan();

  $("#newKeyBtn").addEventListener("click", createKey);
  await loadKeys();
}

/* ----------------------------- Plan & billing ----------------------------- */
function formatPrice(amount, currency) {
  try {
    return i18n.formatLocaleNumber(amount, { style: "currency", currency });
  } catch {
    return `${amount} ${currency}`;
  }
}

function planDateLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const tzOpt = state.user?.timezone ? { timeZone: state.user.timezone } : {};
  return i18n.formatLocaleDate(d, { day: "2-digit", month: "short", year: "numeric", ...tzOpt });
}

async function handleBillingReturn() {
  const params = new URLSearchParams(location.search);
  const billing = params.get("billing");
  if (!billing) return;
  // Strip the query param but keep the SPA hash route.
  const clean = location.pathname + location.hash;
  history.replaceState(null, "", clean);
  if (billing === "success") {
    // The webhook confirms Pro server-side; refresh the cached user.
    try { state.user = await api("/auth/me"); } catch {}
    await refreshTicker();
    toast(t(state.user?.plan === "pro" ? "plan.upgradeSuccess" : "plan.processing"));
  } else if (billing === "cancel") {
    toast(t("plan.upgradeCanceled"), true);
  }
}

async function renderPlan() {
  const body = $("#planBody");
  const badge = $("#planBadge");
  if (!body) return;
  body.innerHTML = `<p class="muted">${esc(t("plan.loading"))}</p>`;

  let plan, pricing;
  try {
    [plan, pricing] = await Promise.all([
      api("/payments/plan"),
      api("/payments/pricing"),
    ]);
  } catch {
    body.innerHTML = `<p class="muted">${esc(t("plan.unavailable"))}</p>`;
    if (badge) badge.hidden = true;
    return;
  }

  const isPro = plan.plan === "pro";
  if (badge) {
    badge.hidden = false;
    badge.textContent = t(isPro ? "plan.pro" : "plan.free");
    badge.className = "plan-badge " + (isPro ? "plan-badge--pro" : "plan-badge--free");
  }

  if (isPro) {
    renderProPlan(body, plan);
  } else {
    renderFreePlan(body, plan, pricing);
  }
}

function renderProPlan(body, plan) {
  const periodEnd = plan.subscription_current_period_end;
  const cancelling = plan.subscription_cancel_at_period_end;
  const lines = [`<p class="plan-desc">${esc(t("plan.proDesc"))}</p>`];
  if (cancelling && periodEnd) {
    lines.push(`<p class="plan-note plan-note--warn">${esc(t("plan.cancelsOn", { date: planDateLabel(periodEnd) }))}</p>`);
  } else if (periodEnd) {
    lines.push(`<p class="plan-note">${esc(t("plan.renewsOn", { date: planDateLabel(periodEnd) }))}</p>`);
  }

  if (!plan.stripe_configured) {
    body.innerHTML = lines.join("");
    return;
  }

  if (cancelling) {
    lines.push(`<div class="plan-actions"><button type="button" class="btn btn--brass btn--sm" id="resumeBtn">${esc(t("plan.resume"))}</button></div>`);
  } else {
    lines.push(`<div class="plan-actions"><button type="button" class="btn btn--ghost btn--sm" id="cancelBtn">${esc(t("plan.cancel"))}</button></div>`);
  }
  body.innerHTML = lines.join("");

  const cancelBtn = $("#cancelBtn");
  if (cancelBtn) cancelBtn.addEventListener("click", async () => {
    if (!confirm(t("plan.cancelConfirm"))) return;
    cancelBtn.disabled = true;
    try {
      await api("/payments/cancel", { method: "POST" });
      toast(t("plan.cancelRequested"));
      await renderPlan();
    } catch (err) {
      toast(err.message, true);
      cancelBtn.disabled = false;
    }
  });

  const resumeBtn = $("#resumeBtn");
  if (resumeBtn) resumeBtn.addEventListener("click", async () => {
    resumeBtn.disabled = true;
    try {
      await api("/payments/resume", { method: "POST" });
      toast(t("plan.resumed"));
      await renderPlan();
    } catch (err) {
      toast(err.message, true);
      resumeBtn.disabled = false;
    }
  });
}

function renderFreePlan(body, plan, pricing) {
  const limit = plan.free_daily_bet_limit;
  const blocks = [`<p class="plan-desc">${esc(t("plan.freeDesc", { limit }))}</p>`];

  if (!plan.stripe_configured) {
    blocks.push(`<p class="plan-note">${esc(t("plan.billingUnavailable"))}</p>`);
    body.innerHTML = blocks.join("");
    return;
  }

  const prices = pricing.prices || [];
  const codes = prices.map(p => p.currency);
  const preferred = (state.user?.base_currency || pricing.default_currency || "USD").toUpperCase();
  const selected = codes.includes(preferred) ? preferred : (pricing.default_currency || "USD");
  const options = prices.map(p =>
    `<option value="${esc(p.currency)}"${p.currency === selected ? " selected" : ""}>${esc(p.currency)}</option>`
  ).join("");

  blocks.push(`
    <div class="upgrade-card">
      <h3 class="upgrade-card__title">${esc(t("plan.upgradeTitle"))}</h3>
      <p class="upgrade-card__blurb">${esc(t("plan.upgradeBlurb"))}</p>
      <div class="upgrade-card__row">
        <label class="upgrade-card__ccy"><span>${esc(t("plan.payCurrency"))}</span>
          <select id="planCurrency" class="mini-select">${options}</select>
        </label>
        <div class="upgrade-card__price" id="planPrice"></div>
      </div>
      <button type="button" class="btn btn--brass" id="upgradeBtn">${esc(t("plan.upgrade"))}</button>
    </div>`);
  body.innerHTML = blocks.join("");

  const priceFor = code => {
    const p = prices.find(x => x.currency === code);
    return p ? formatPrice(p.amount, p.currency) : "";
  };
  const updatePrice = () => {
    const code = $("#planCurrency").value;
    $("#planPrice").textContent = t("plan.perMonth", { price: priceFor(code) });
  };
  $("#planCurrency").addEventListener("change", updatePrice);
  updatePrice();

  $("#upgradeBtn").addEventListener("click", async () => {
    const btn = $("#upgradeBtn");
    btn.disabled = true;
    const currency = $("#planCurrency").value;
    const base = `${location.origin}/app/`;
    try {
      const session = await api("/payments/checkout-session", {
        method: "POST",
        body: {
          currency,
          success_url: `${base}?billing=success#/settings`,
          cancel_url: `${base}?billing=cancel#/settings`,
        },
      });
      if (session.url) {
        window.location.assign(session.url);
      } else {
        toast(t("plan.checkoutFailed"), true);
        btn.disabled = false;
      }
    } catch (err) {
      toast(err.message || t("plan.checkoutFailed"), true);
      btn.disabled = false;
    }
  });
}

async function loadKeys() {
  const keys = await api("/auth/api-keys");
  $("#keysBody").innerHTML = keys.map(k => `
    <tr><td>${esc(k.name)}</td>
    <td class="num">${esc(k.prefix)}…</td>
    <td class="num">${k.last_used_at ? formatDt(k.last_used_at) : t("settings.never")}</td>
    <td class="r"><button class="btn btn--danger" data-revoke="${k.id}">${t("settings.revoke")}</button></td></tr>`).join("")
    || `<tr><td colspan="4" class="empty">${t("settings.noKeys")}</td></tr>`;
  $$("[data-revoke]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm(t("settings.revokeConfirm"))) return;
    await api(`/auth/api-keys/${b.dataset.revoke}`, { method: "DELETE" });
    toast(t("settings.keyRevoked")); loadKeys();
  }));
}

async function createKey() {
  const name = prompt(t("settings.keyPrompt"), "default");
  if (name == null) return;
  const k = await api(`/auth/api-keys?name=${encodeURIComponent(name || "default")}`, { method: "POST" });
  const reveal = $("#newKeyReveal");
  reveal.hidden = false;
  reveal.textContent = t("settings.keyReveal", { key: k.api_key });
  await loadKeys();
}

/* ============================ Admin ============================ */
async function renderAdmin() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-admin"));

  let userSearchTimer;
  $("#adminUserSearch").addEventListener("input", () => {
    clearTimeout(userSearchTimer);
    userSearchTimer = setTimeout(loadAdminUsers, 300);
  });
  $("#adminEventFilter").addEventListener("change", loadAdminEvents);
  $("#adminAddForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("#adminAddEmail").value.trim();
    if (!email) return;
    try {
      await api("/auth/admin/admins", { method: "POST", body: { email } });
      $("#adminAddEmail").value = "";
      toast(t("admin.adminAdded"));
      await Promise.all([loadAdminAdmins(), loadAdminUsers(), loadAdminStats()]);
    } catch (err) {
      toast(err.message, true);
    }
  });

  await Promise.all([loadAdminStats(), loadAdminAdmins(), loadAdminUsers(), loadAdminEvents()]);
}

async function loadAdminStats() {
  const s = await api("/auth/admin/stats");
  const cards = [
    [t("admin.statUsers"), String(s.total_users), t("admin.statUsersSub", { active: s.active_users, admins: s.admin_users })],
    [t("admin.statBets"), String(s.total_bets), t("admin.statBetsSub")],
    [t("admin.statSignups"), String(s.signups_today), t("admin.statSignupsSub")],
    [t("admin.statLogins"), String(s.logins_today), t("admin.statLoginsSub")],
    [t("admin.statEvents"), String(s.events_today), t("admin.statEventsSub")],
  ];
  $("#adminStats").innerHTML = cards.map(([l, v, sub]) =>
    `<div class="card"><div class="card__label">${l}</div><div class="card__value">${v}</div><div class="card__sub">${sub}</div></div>`
  ).join("");
}

function adminStatusBadge(active) {
  return active
    ? `<span class="outcome-select outcome-select--win">${t("admin.active")}</span>`
    : `<span class="outcome-select outcome-select--loss">${t("admin.disabled")}</span>`;
}

async function loadAdminAdmins() {
  const admins = await api("/auth/admin/admins");
  $("#adminAdminsBody").innerHTML = admins.map(u => `
    <tr data-admin="${u.id}">
      <td>${esc(u.email)}</td>
      <td>${esc(u.display_name || "—")}</td>
      <td class="num">${formatDt(u.created_at)}</td>
      <td class="r">
        <button class="btn btn--ghost btn--sm" data-remove-admin="${u.id}" ${u.id === state.user?.id ? "disabled" : ""}>
          ${t("admin.removeAdmin")}
        </button>
      </td>
    </tr>`).join("")
    || `<tr><td colspan="4" class="empty">${t("admin.noAdmins")}</td></tr>`;

  $$("[data-remove-admin]").forEach(btn => btn.addEventListener("click", () =>
    adminRemoveAdmin(btn.dataset.removeAdmin)
  ));
}

async function adminRemoveAdmin(userId) {
  if (!confirm(t("admin.revokeAdminConfirm"))) return;
  try {
    await api(`/auth/admin/admins/${userId}`, { method: "DELETE" });
    toast(t("admin.adminRemoved"));
    await Promise.all([loadAdminAdmins(), loadAdminUsers(), loadAdminEvents(), loadAdminStats()]);
  } catch (err) {
    toast(err.message, true);
  }
}

async function loadAdminUsers() {
  const search = $("#adminUserSearch").value.trim();
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  const users = await api(`/auth/admin/users${qs}`);
  $("#adminUsersBody").innerHTML = users.map(u => `
    <tr data-user="${u.id}">
      <td>${esc(u.email)}</td>
      <td>${esc(u.display_name || "—")}</td>
      <td>${adminStatusBadge(u.is_active)}</td>
      <td class="num">${formatDt(u.last_login_at)}</td>
      <td class="num">${formatDt(u.created_at)}</td>
      <td class="r num">${u.bet_count}</td>
      <td class="r num">${u.api_key_count}</td>
      <td class="r">
        <button class="btn btn--ghost btn--sm" data-toggle-active="${u.id}" data-active="${u.is_active}">
          ${u.is_active ? t("admin.disable") : t("admin.enable")}
        </button>
      </td>
    </tr>`).join("")
    || `<tr><td colspan="8" class="empty">${t("admin.noUsers")}</td></tr>`;

  $$("[data-toggle-active]").forEach(btn => btn.addEventListener("click", () =>
    adminToggleUser(btn.dataset.toggleActive, { is_active: btn.dataset.active !== "true" })
  ));
}

async function adminToggleUser(userId, payload) {
  const label = payload.is_active ? t("admin.enableConfirm") : t("admin.disableConfirm");
  if (!confirm(label)) return;
  try {
    await api(`/auth/admin/users/${userId}`, { method: "PATCH", body: payload });
    toast(t("admin.userUpdated"));
    await Promise.all([loadAdminUsers(), loadAdminEvents(), loadAdminStats()]);
  } catch (err) {
    toast(err.message, true);
  }
}

async function loadAdminEvents() {
  const eventType = $("#adminEventFilter").value;
  const qs = eventType ? `?event_type=${encodeURIComponent(eventType)}` : "";
  const events = await api(`/auth/admin/events${qs}`);
  $("#adminEventsBody").innerHTML = events.map(e => `
    <tr>
      <td class="num">${formatDt(e.created_at)}</td>
      <td>${esc(e.event_type)}</td>
      <td>${esc(e.user_email || e.user_id || "—")}</td>
      <td>${esc(e.detail || "—")}</td>
      <td class="num">${esc(e.ip_address || "—")}</td>
    </tr>`).join("")
    || `<tr><td colspan="5" class="empty">${t("admin.noEvents")}</td></tr>`;
}

/* -------------------------------- start -------------------------------- */
async function start() {
  try {
    const shareToken = getShareToken();
    if (shareToken) {
      await i18n.initI18n(i18n.getLoginLocale?.() || "en");
      document.title = t("share.title");
      await renderPublicShare(shareToken);
      return;
    }
    if (token()) {
      showAuthLoading();
      await i18n.initI18n("en");
      await boot({ loading: false });
    } else {
      showAuthLoading();
      await i18n.initI18n(i18n.getLoginLocale());
      document.title = t("meta.title");
      i18n.applyI18n(document);
      if (!location.hash || location.hash === "#/bets") location.hash = "#/login";
      showAuth();
    }
  } catch (err) {
    console.error("Startup failed:", err);
    showAuth();
  }
}

function onReady() {
  try { bindEvents(); } catch (err) { console.error("bindEvents failed:", err); }
  if (getShareToken() || token()) {
    start().catch(() => (getShareToken() ? renderPublicShare(getShareToken()) : showAuth()));
  }
}

window.mbrAttach = function () {
  if (window.__mbrAttached) return;
  window.__mbrAttached = true;
  onReady();
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.mbrAttach());
} else if (document.querySelector('script[src="/app/app.js"]')) {
  // Loaded via static tag (e.g. tests)
  window.mbrAttach();
}
window.addEventListener("pageshow", e => { if (e.persisted) onReady(); });
})();
