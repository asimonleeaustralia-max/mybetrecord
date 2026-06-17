/* mybetrecord — single-page client.
   Talks to the services through the same origin; nginx proxies
   /auth, /bets, /reports, /payments to the right container. */

const TOKEN_KEY = "mbr_token";
const state = { user: null, sports: [], charts: {} };

/* ----------------------------- API client ----------------------------- */
function token() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); }

async function api(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401) { setToken(null); showAuth(); throw new Error("Session expired"); }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : "Request failed");
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
  const s = n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (withSign && n > 0 ? "+" : "") + s;
}
function plClass(v) { return v > 0 ? "pl-pos" : v < 0 ? "pl-neg" : "pl-zero"; }
function pct(v) { return v == null ? "—" : `${Number(v).toFixed(2)}%`; }
function esc(s) { return (s ?? "").toString().replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function toast(msg, isErr = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast" + (isErr ? " toast--err" : "");
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.hidden = true), 2600);
}

function clone(id) { return document.importNode($(`#${id}`).content, true); }

/* -------------------------------- auth -------------------------------- */
function showAuth() {
  $("#app").hidden = true;
  $("#auth").hidden = false;
}
function showApp() {
  $("#auth").hidden = true;
  $("#app").hidden = false;
}

$$("[data-auth-tab]").forEach(btn => btn.addEventListener("click", () => {
  $$("[data-auth-tab]").forEach(b => b.classList.toggle("is-active", b === btn));
  const tab = btn.dataset.authTab;
  $("#loginForm").hidden = tab !== "login";
  $("#registerForm").hidden = tab !== "register";
  $("#authError").hidden = true;
}));

$("#loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  const f = Object.fromEntries(new FormData(e.target));
  try {
    const { access_token } = await api("/auth/login", { method: "POST", body: f });
    setToken(access_token);
    await boot();
  } catch (err) { authError(err.message); }
});

$("#registerForm").addEventListener("submit", async e => {
  e.preventDefault();
  const f = Object.fromEntries(new FormData(e.target));
  if (!f.display_name) delete f.display_name;
  try {
    const { access_token } = await api("/auth/register", { method: "POST", body: f });
    setToken(access_token);
    await boot();
  } catch (err) { authError(err.message); }
});

function authError(msg) { const el = $("#authError"); el.textContent = msg; el.hidden = false; }

$("#logoutBtn").addEventListener("click", () => { setToken(null); showAuth(); location.hash = "#/bets"; });

/* ------------------------------- ticker ------------------------------- */
async function refreshTicker() {
  try {
    const s = await api("/reports/summary");
    $("#tkBankroll").textContent = state.user.bankroll ? money(state.user.bankroll) : "—";
    const pl = $("#tkPL");
    pl.textContent = money(s.profit, true);
    pl.className = "num " + plClass(s.profit);
    $("#tkYield").textContent = pct(s.yield_pct);
  } catch {}
}

/* ------------------------------- router ------------------------------- */
const routes = {
  "/bets": renderBets,
  "/new": () => renderForm(null),
  "/reports": renderReports,
  "/settings": renderSettings,
};

async function route() {
  if (!state.user) return;
  const hash = location.hash || "#/bets";
  const [path, id] = hash.slice(1).split("/").filter(Boolean).reduce((a, p, i) => (i === 0 ? ["/" + p] : [a[0], p]), ["", ""]);
  $$(".tab").forEach(t => t.classList.toggle("is-active", t.getAttribute("href") === `#${path}`));

  if (path === "/edit" && id) return renderForm(id);
  const handler = routes[path] || renderBets;
  await handler();
}
window.addEventListener("hashchange", route);

/* -------------------------------- boot -------------------------------- */
async function boot() {
  try {
    state.user = await api("/auth/me");
  } catch { showAuth(); return; }
  showApp();
  await refreshTicker();
  if (!location.hash) location.hash = "#/bets";
  await route();
}

/* ============================ Bets list ============================ */
async function renderBets() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-bets"));

  state.sports = await api("/bets/sports").catch(() => []);
  buildBetFilters();
  await loadBets();
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
    <label>Sport<select name="sport"><option value="">All</option>${state.sports.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
    <label>Result<select name="outcome"><option value="">All</option><option value="win">Win</option><option value="loss">Loss</option><option value="void">Void</option><option value="pending">Pending</option></select></label>
    <label>Type<select name="bet_type"><option value="">All</option><option value="win">Win</option><option value="each_way">Each way</option><option value="over_under">Over/Under</option><option value="multi">Multi</option><option value="handicap">Handicap</option></select></label>
    <label>From<input type="date" name="date_from" /></label>
    <label>To<input type="date" name="date_to" /></label>`;
  $$("select, input", root).forEach(el => el.addEventListener("change", loadBets));
}

async function loadBets() {
  const bets = await api("/bets" + qs(currentFilters("betsFilters")));
  const body = $("#betsBody");
  $("#betsEmpty").hidden = bets.length > 0;
  body.innerHTML = bets.map(betRow).join("");
  $$("[data-del]", body).forEach(b => b.addEventListener("click", () => deleteBet(b.dataset.del)));
}

function outcomePill(o) {
  const map = { win: "win", loss: "loss", void: "void", pending: "pending", half_win: "win", half_loss: "loss", cashed_out: "void" };
  return `<span class="pill pill--${map[o] || "pending"}">${esc(o.replace("_", " "))}</span>`;
}

function betRow(b) {
  const d = new Date(b.placed_at);
  const date = d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "2-digit" });
  return `<tr>
    <td class="num">${date}</td>
    <td>${esc(b.sport)}</td>
    <td>${esc(b.event)}<div class="sel">${esc(b.selection)}</div></td>
    <td>${esc(b.bet_type.replace("_", " "))}</td>
    <td class="r">${Number(b.odds_decimal).toFixed(2)}</td>
    <td class="r">${money(b.stake)}</td>
    <td>${outcomePill(b.outcome)}</td>
    <td class="r ${plClass(b.profit)}">${money(b.profit, true)}</td>
    <td class="r">${b.clv_pct == null ? "—" : pct(b.clv_pct)}</td>
    <td class="r"><a class="btn btn--ghost btn--sm" href="#/edit/${b.id}">Edit</a> <button class="btn btn--danger" data-del="${b.id}">Delete</button></td>
  </tr>`;
}

async function deleteBet(id) {
  if (!confirm("Delete this bet? This can't be undone.")) return;
  await api(`/bets/${id}`, { method: "DELETE" });
  toast("Bet deleted");
  await Promise.all([loadBets(), refreshTicker()]);
}

/* ============================ Bet form ============================ */
async function renderForm(id) {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-form"));
  state.sports = await api("/bets/sports").catch(() => []);
  $("#sportList").innerHTML = state.sports.map(s => `<option value="${esc(s)}">`).join("");

  const form = $("#betForm");
  // default odds format from user settings
  form.odds_format.value = state.user.default_odds_format || "decimal";
  form.currency.value = state.user.base_currency || "GBP";
  syncOddsFormat();
  syncEachWay();

  form.odds_format.addEventListener("change", syncOddsFormat);
  form.each_way.addEventListener("change", syncEachWay);
  ["odds", "personal_implied_odds"].forEach(n => form[n].addEventListener("input", updateKellyHint));

  let editing = null;
  if (id) {
    $("#formTitle").textContent = "Edit bet";
    $("#saveBtn").textContent = "Save changes";
    editing = await api(`/bets/${id}`);
    fillForm(form, editing);
    syncOddsFormat(); syncEachWay(); updateKellyHint();
  } else {
    // default datetime-local to now
    const now = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);
    form.placed_at.value = now.toISOString().slice(0, 16);
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const payload = readForm(form);
    try {
      if (editing) await api(`/bets/${editing.id}`, { method: "PATCH", body: payload });
      else await api("/bets", { method: "POST", body: payload });
      toast(editing ? "Bet updated" : "Bet recorded");
      await refreshTicker();
      location.hash = "#/bets";
    } catch (err) { toast(err.message, true); }
  });
}

function syncOddsFormat() {
  const form = $("#betForm");
  const frac = form.odds_format.value === "fractional";
  $("#oddsDenField").hidden = !frac;
  $("#oddsField").querySelector("input").placeholder =
    form.odds_format.value === "american" ? "+150" : frac ? "6 (numerator)" : "2.50";
}
function syncEachWay() {
  const form = $("#betForm");
  $("#ewFields").hidden = !form.each_way.checked;
}

function updateKellyHint() {
  const form = $("#betForm");
  const bankroll = state.user.bankroll;
  const personal = parseFloat(form.personal_implied_odds.value);
  const oddsDec = parseFloat(form.odds.value); // approximate (decimal entry)
  const hint = $("#kellyHint");
  if (bankroll && personal > 1 && oddsDec > 1 && form.odds_format.value === "decimal") {
    const b = oddsDec - 1, p = 1 / personal, q = 1 - p;
    const f = Math.max(0, (b * p - q) / b) * (state.user.kelly_multiplier || 1);
    const stake = (f * bankroll).toFixed(2);
    hint.hidden = false;
    hint.textContent = f > 0
      ? `Kelly suggests ${money(stake)} ${ccy()} (${(f * 100).toFixed(1)}% of bankroll).`
      : "No edge at these odds — Kelly suggests no bet.";
  } else {
    hint.hidden = true;
  }
}

const NUM_FIELDS = ["odds", "odds_denominator", "stake", "place_fraction", "cash_out_amount",
  "model_implied_odds", "personal_implied_odds", "closing_odds", "exchange_commission_pct"];

function readForm(form) {
  const data = Object.fromEntries(new FormData(form));
  const out = {};
  for (const [k, v] of Object.entries(data)) {
    if (v === "" || v == null) continue;
    out[k] = NUM_FIELDS.includes(k) ? Number(v) : v;
  }
  out.each_way = form.each_way.checked;
  out.placed = form.placed.checked;
  if (out.currency) out.currency = out.currency.toUpperCase();
  if (out.placed_at) out.placed_at = new Date(out.placed_at).toISOString();
  return out;
}

function fillForm(form, b) {
  const set = (n, v) => { if (form[n] != null && v != null) form[n].value = v; };
  set("sport", b.sport); set("bet_type", b.bet_type); set("event", b.event);
  set("selection", b.selection);
  set("placed_at", new Date(b.placed_at).toISOString().slice(0, 16));
  // stored odds are decimal; present as decimal for editing clarity
  form.odds_format.value = "decimal";
  set("odds", Number(b.odds_decimal).toFixed(2));
  set("stake", b.stake); set("currency", b.currency);
  form.each_way.checked = b.each_way; form.placed.checked = b.placed;
  set("place_fraction", b.place_fraction);
  set("outcome", b.outcome); set("cash_out_amount", b.cash_out_amount);
  set("bet_model", b.bet_model); set("closing_odds", b.closing_odds);
  set("model_implied_odds", b.model_implied_odds);
  set("personal_implied_odds", b.personal_implied_odds);
  set("exchange", b.exchange); set("exchange_commission_pct", b.exchange_commission_pct);
  set("tipster", b.tipster); set("notes", b.notes);
}

/* ============================ Reports ============================ */
async function renderReports() {
  const main = $("#main");
  main.innerHTML = "";
  main.appendChild(clone("tpl-reports"));

  state.sports = await api("/bets/sports").catch(() => []);
  buildReportFilters();
  $("#breakdownDim").addEventListener("change", loadBreakdown);
  $("#exportCsv").addEventListener("click", () => downloadExport("csv"));
  $("#exportXlsx").addEventListener("click", () => downloadExport("xlsx"));
  await loadReports();
}

function buildReportFilters() {
  const root = $("#reportFilters");
  root.innerHTML = `
    <label>Sport<select name="sport"><option value="">All</option>${state.sports.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
    <label>Type<select name="bet_type"><option value="">All</option><option value="win">Win</option><option value="each_way">Each way</option><option value="over_under">Over/Under</option><option value="multi">Multi</option></select></label>
    <label>From<input type="date" name="date_from" /></label>
    <label>To<input type="date" name="date_to" /></label>`;
  $$("select, input", root).forEach(el => el.addEventListener("change", loadReports));
}

async function loadReports() {
  await Promise.all([loadSummary(), loadEquity(), loadBreakdown(), loadMonthly()]);
}

async function loadSummary() {
  const f = currentFilters("reportFilters");
  const s = await api("/reports/summary" + qs(f));
  const cards = [
    ["Profit / Loss", `<span class="${plClass(s.profit)}">${money(s.profit, true)}</span>`, `${s.settled_bets} settled`],
    ["ROI", pct(s.roi_pct), s.roi_vs_bankroll_pct != null ? `${pct(s.roi_vs_bankroll_pct)} of bankroll` : "per unit staked"],
    ["Yield", pct(s.yield_pct), `${money(s.turnover)} turnover`],
    ["Strike rate", pct(s.strike_rate_pct), `${s.wins}W / ${s.losses}L / ${s.voids}V`],
    ["Total bets", String(s.total_bets), `${ccy()} base`],
  ];
  $("#metricCards").innerHTML = cards.map(([l, v, sub]) =>
    `<div class="card"><div class="card__label">${l}</div><div class="card__value">${v}</div><div class="card__sub">${sub}</div></div>`).join("");
}

function destroyChart(name) { if (state.charts[name]) { state.charts[name].destroy(); delete state.charts[name]; } }

async function loadEquity() {
  const f = currentFilters("reportFilters");
  const pts = await api("/reports/equity-curve" + qs(f));
  destroyChart("equity");
  const ctx = $("#equityChart");
  if (!ctx || typeof Chart === "undefined") return;
  state.charts.equity = new Chart(ctx, {
    type: "line",
    data: {
      labels: pts.map(p => new Date(p.date).toLocaleDateString(undefined, { day: "2-digit", month: "short" })),
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
  if (!ctx || typeof Chart === "undefined") return;
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
  $("#dimHead").textContent = dim.replace("_", " ").replace(/^\w/, c => c.toUpperCase());
  const f = currentFilters("reportFilters");
  f.dimension = dim;
  const rows = await api("/reports/breakdown" + qs(f));
  $("#breakdownBody").innerHTML = rows.map(r => `
    <tr><td>${esc(r.key)}</td>
    <td class="r num">${r.settled_bets}</td>
    <td class="r num">${pct(r.strike_rate_pct)}</td>
    <td class="r num">${pct(r.yield_pct)}</td>
    <td class="r num ${plClass(r.profit)}">${money(r.profit, true)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="empty">No settled bets yet.</td></tr>`;
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
  form.default_odds_format.value = u.default_odds_format;
  form.base_currency.value = u.base_currency;
  form.bankroll.value = u.bankroll;
  form.kelly_multiplier.value = u.kelly_multiplier;
  form.display_name.value = u.display_name || "";

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const payload = {
      default_odds_format: data.default_odds_format,
      base_currency: data.base_currency.toUpperCase(),
      bankroll: Number(data.bankroll || 0),
      kelly_multiplier: Number(data.kelly_multiplier || 1),
      display_name: data.display_name || null,
    };
    try {
      state.user = await api("/auth/settings", { method: "PATCH", body: payload });
      toast("Settings saved");
      await refreshTicker();
    } catch (err) { toast(err.message, true); }
  });

  $("#newKeyBtn").addEventListener("click", createKey);
  await loadKeys();
}

async function loadKeys() {
  const keys = await api("/auth/api-keys");
  $("#keysBody").innerHTML = keys.map(k => `
    <tr><td>${esc(k.name)}</td>
    <td class="num">${esc(k.prefix)}…</td>
    <td class="num">${k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "never"}</td>
    <td class="r"><button class="btn btn--danger" data-revoke="${k.id}">Revoke</button></td></tr>`).join("")
    || `<tr><td colspan="4" class="empty">No keys yet.</td></tr>`;
  $$("[data-revoke]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("Revoke this key? Anything using it will stop working.")) return;
    await api(`/auth/api-keys/${b.dataset.revoke}`, { method: "DELETE" });
    toast("Key revoked"); loadKeys();
  }));
}

async function createKey() {
  const name = prompt("Name this key (e.g. 'laptop script')", "default");
  if (name == null) return;
  const k = await api(`/auth/api-keys?name=${encodeURIComponent(name || "default")}`, { method: "POST" });
  const reveal = $("#newKeyReveal");
  reveal.hidden = false;
  reveal.textContent = `Copy this now — it won't be shown again:  ${k.api_key}`;
  await loadKeys();
}

/* -------------------------------- start -------------------------------- */
if (token()) boot(); else showAuth();
