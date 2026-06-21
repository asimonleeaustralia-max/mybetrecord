"""Integration tests covering the request paths the in-process unit tests miss:
auth + API keys, odds-format handling, settlement, Kelly, reports, and exports.
Regression coverage for the three bugs found during the first local run."""

import pytest


# ------------------------------- auth ------------------------------------- #

def test_register_login_me(clients):
    email = "login-flow@example.com"
    r = clients["auth"].post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    r = clients["auth"].post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = clients["auth"].get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_login_rejects_bad_password(clients, auth_headers):
    _, email = auth_headers
    r = clients["auth"].post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


def test_password_reset_flow(clients):
    email = "reset-flow@example.com"
    password = "password123"
    new_password = "new-password456"
    r = clients["auth"].post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201

    r = clients["auth"].post("/auth/password-reset/request", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    reset_token = body.get("reset_token")
    assert reset_token, "development mode should return reset_token for tests"

    r = clients["auth"].post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "password": new_password},
    )
    assert r.status_code == 200

    r = clients["auth"].post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401

    r = clients["auth"].post("/auth/login", json={"email": email, "password": new_password})
    assert r.status_code == 200


def test_password_reset_request_unknown_email(clients):
    r = clients["auth"].post(
        "/auth/password-reset/request",
        json={"email": "nobody-here@example.com"},
    )
    assert r.status_code == 200
    assert "message" in r.json()


def test_password_reset_confirm_rejects_invalid_token(clients):
    r = clients["auth"].post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-valid-token", "password": "password123"},
    )
    assert r.status_code == 400


def test_settings_update(clients, auth_headers):
    headers, _ = auth_headers
    r = clients["auth"].patch("/auth/settings", headers=headers,
                              json={"bankroll": 2500, "base_currency": "aud",
                                    "default_odds_format": "fractional", "kelly_multiplier": 0.5})
    assert r.status_code == 200
    body = r.json()
    assert body["bankroll"] == 2500
    assert body["base_currency"] == "AUD"  # upper-cased
    assert body["default_odds_format"] == "fractional"


def test_register_captures_timezone(clients):
    email = "tz-user@example.com"
    r = clients["auth"].post(
        "/auth/register",
        json={"email": email, "password": "password123", "timezone": "Europe/London"},
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = clients["auth"].get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["timezone"] == "Europe/London"


def test_register_defaults_timezone_to_utc(clients):
    email = "tz-default@example.com"
    r = clients["auth"].post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = clients["auth"].get("/auth/me", headers=headers)
    assert me.json()["timezone"] == "UTC"


def test_settings_timezone(clients, auth_headers):
    headers, _ = auth_headers
    r = clients["auth"].patch("/auth/settings", headers=headers, json={"timezone": "America/New_York"})
    assert r.status_code == 200
    assert r.json()["timezone"] == "America/New_York"


def test_settings_rejects_invalid_timezone(clients, auth_headers):
    headers, _ = auth_headers
    r = clients["auth"].patch("/auth/settings", headers=headers, json={"timezone": "Not/A/Zone"})
    assert r.status_code == 422


# --------------------------- API keys (regression) ------------------------ #

def test_api_key_lifecycle(clients, auth_headers):
    headers, _ = auth_headers

    # Create — this 500'd before the fix.
    created = clients["auth"].post("/auth/api-keys?name=cli", headers=headers)
    assert created.status_code == 201, created.text
    full_key = created.json()["api_key"]
    assert full_key.startswith("mbr_")

    # List shows it (without the secret).
    listed = clients["auth"].get("/auth/api-keys", headers=headers)
    assert listed.status_code == 200
    assert any(k["name"] == "cli" for k in listed.json())
    assert "api_key" not in listed.json()[0]

    # The key authenticates on auth, bets, and reports.
    key_headers = {"Authorization": f"Bearer {full_key}"}
    assert clients["auth"].get("/auth/me", headers=key_headers).status_code == 200
    assert clients["bets"].get("/bets", headers=key_headers).status_code == 200
    assert clients["reports"].get("/reports/summary", headers=key_headers).status_code == 200

    # X-API-Key header works too.
    assert clients["bets"].get("/bets", headers={"X-API-Key": full_key}).status_code == 200

    # Revoke -> rejected.
    key_id = listed.json()[0]["id"]
    assert clients["auth"].delete(f"/auth/api-keys/{key_id}", headers=headers).status_code == 204
    assert clients["bets"].get("/bets", headers=key_headers).status_code == 401


def test_requests_without_credentials_rejected(clients):
    assert clients["bets"].get("/bets").status_code == 401
    assert clients["reports"].get("/reports/summary").status_code == 401


# --------------------------- odds formats (regression) -------------------- #

def _make_bet(clients, headers, **overrides):
    payload = {
        "event": "Test event", "selection": "Test pick", "sport": "Testball",
        "bet_type": "win", "odds": 2.0, "odds_format": "decimal",
        "stake": 100, "outcome": "pending",
    }
    payload.update(overrides)
    r = clients["bets"].post("/bets", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_odds_decimal(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=2.5, odds_format="decimal")
    assert b["odds_decimal"] == pytest.approx(2.5)


def test_odds_format_defaults_from_user_settings(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"default_odds_format": "american"})
    # API clients can omit odds_format; the user's settings preference is used.
    r = clients["bets"].post("/bets", headers=headers, json={
        "event": "Test event", "selection": "Test pick", "sport": "Testball",
        "bet_type": "win", "odds": 150, "stake": 100, "outcome": "pending",
    })
    assert r.status_code == 201, r.text
    assert r.json()["odds_decimal"] == pytest.approx(2.5)
    assert r.json()["odds_format"] == "american"


def test_odds_american(clients, auth_headers):
    h = auth_headers[0]
    assert _make_bet(clients, h, odds=150, odds_format="american")["odds_decimal"] == pytest.approx(2.5)
    assert _make_bet(clients, h, odds=-200, odds_format="american")["odds_decimal"] == pytest.approx(1.5)


def test_odds_fractional_string(clients, auth_headers):
    # Sending "11/8" as a string was rejected before the schema fix.
    b = _make_bet(clients, auth_headers[0], odds="11/8", odds_format="fractional")
    assert b["odds_decimal"] == pytest.approx(2.375)


def test_odds_fractional_numerator_denominator(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=6, odds_denominator=4, odds_format="fractional")
    assert b["odds_decimal"] == pytest.approx(2.5)


def test_odds_hong_kong(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=0.85, odds_format="hong_kong")
    assert b["odds_decimal"] == pytest.approx(1.85)
    assert b["odds_format"] == "hong_kong"


def test_odds_malaysian(clients, auth_headers):
    h = auth_headers[0]
    assert _make_bet(clients, h, odds=0.85, odds_format="malaysian")["odds_decimal"] == pytest.approx(1.85)
    assert _make_bet(clients, h, odds=-0.85, odds_format="malaysian")["odds_decimal"] == pytest.approx(1 + 1 / 0.85)


def test_odds_indonesian(clients, auth_headers):
    h = auth_headers[0]
    assert _make_bet(clients, h, odds=1.5, odds_format="indonesian")["odds_decimal"] == pytest.approx(2.5)
    assert _make_bet(clients, h, odds=-1.5, odds_format="indonesian")["odds_decimal"] == pytest.approx(1 + 1 / 1.5)


def test_odds_below_one_rejected(clients, auth_headers):
    r = clients["bets"].post("/bets", headers=auth_headers[0], json={
        "event": "x", "selection": "y", "sport": "z", "odds": 0.8,
        "odds_format": "decimal", "stake": 10})
    assert r.status_code == 422


# ------------------------------ settlement -------------------------------- #

def test_pl_win_with_commission(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=2.5, stake=100, outcome="win",
                  bookmaker="Betfair", exchange_commission_pct=5)
    assert b["profit"] == pytest.approx(142.5)  # 150 gross - 7.5 commission


def test_lay_win_with_commission(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=3.0, stake=10, outcome="win",
                  side="lay", bookmaker="Betfair Exchange", exchange_commission_pct=5)
    assert b["side"] == "lay"
    assert b["profit"] == pytest.approx(9.5)


def test_lay_each_way_rejected(clients, auth_headers):
    r = clients["bets"].post("/bets", headers=auth_headers[0], json={
        "event": "Test event", "selection": "Test pick", "sport": "Testball",
        "bet_type": "win", "odds": 3.0, "odds_format": "decimal",
        "stake": 10, "outcome": "pending", "side": "lay", "each_way": True,
    })
    assert r.status_code == 422


def test_pl_loss_and_void(clients, auth_headers):
    h = auth_headers[0]
    assert _make_bet(clients, h, odds=2.5, stake=100, outcome="loss")["profit"] == pytest.approx(-100.0)
    assert _make_bet(clients, h, odds=2.5, stake=100, outcome="void")["profit"] == pytest.approx(0.0)


def test_pl_cash_out_overrides_outcome(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=2.5, stake=100, outcome="loss", cash_out_amount=120)
    assert b["profit"] == pytest.approx(20.0)


def test_pl_cash_out_overrides_settled_win_on_patch(clients, auth_headers):
    headers, _ = auth_headers
    bet = _make_bet(clients, headers, odds=2.0, stake=100, outcome="win")
    assert bet["profit"] == pytest.approx(100.0)

    upd = clients["bets"].patch(
        f"/bets/{bet['id']}", headers=headers, json={"cash_out_amount": 85}
    )
    assert upd.status_code == 200
    body = upd.json()
    assert body["profit"] == pytest.approx(-15.0)
    assert body["outcome"] == "win"

    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["profit"] == pytest.approx(-15.0)


def test_bankroll_includes_pending_cash_out(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"bankroll": 1000, "base_currency": "GBP"})
    _make_bet(clients, headers, odds=2.0, stake=100, outcome="pending", cash_out_amount=110, currency="GBP")
    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["profit"] == pytest.approx(10.0)
    assert summary["bankroll"] == pytest.approx(1010.0)


def test_pl_each_way_winner(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=5.0, stake=100, outcome="win",
                  each_way=True, place_fraction=0.25)
    assert b["profit"] == pytest.approx(250.0)


def test_pl_each_way_placed_only(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=5.0, stake=100, outcome="placed",
                  each_way=True, place_fraction=0.25)
    assert b["outcome"] == "placed"
    assert b["placed"] is True
    assert b["profit"] == pytest.approx(0.0)


# -------------------------------- Kelly ----------------------------------- #

def test_kelly_recommendation(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"bankroll": 1000})
    b = _make_bet(clients, headers, odds=2.5, stake=100, personal_implied_odds=2.1)
    assert b["kelly_stake"] == pytest.approx(126.98, abs=0.5)


def test_kelly_none_without_bankroll(clients, auth_headers):
    b = _make_bet(clients, auth_headers[0], odds=2.5, personal_implied_odds=2.1)
    assert b["kelly_stake"] is None  # bankroll defaults to 0


def test_personal_and_model_edge_saved(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"bankroll": 1000})
    b = _make_bet(
        clients, headers, odds=2.5, stake=100,
        personal_implied_odds=2.1, model_implied_odds=2.0,
    )
    assert b["personal_edge_pct"] == pytest.approx(19.05, abs=0.1)
    assert b["model_edge_pct"] == pytest.approx(25.0, abs=0.1)
    assert b["edge_pct"] == b["personal_edge_pct"]
    assert b["kelly_stake"] == pytest.approx(126.98, abs=0.5)
    assert b["model_kelly_stake"] == pytest.approx(166.67, abs=0.5)


# --------------------------- sports dropdown ------------------------------ #

def test_sports_dropdown_distinct_sorted(clients, auth_headers):
    headers, _ = auth_headers
    for sport in ("Tennis", "Golf", "Tennis", "Cricket"):
        _make_bet(clients, headers, sport=sport)
    sports = clients["bets"].get("/bets/sports", headers=headers).json()
    assert sports == ["Cricket", "Golf", "Tennis"]  # distinct + alphabetical


# ----------------------------- edit / delete ------------------------------ #

def test_update_and_delete_bet(clients, auth_headers):
    headers, _ = auth_headers
    bet = _make_bet(clients, headers, odds=2.0, stake=100, outcome="pending")
    bet_id = bet["id"]

    upd = clients["bets"].patch(f"/bets/{bet_id}", headers=headers, json={"outcome": "win"})
    assert upd.status_code == 200
    settled = upd.json()
    assert settled["profit"] == pytest.approx(100.0)  # recomputed on settle
    assert settled["settled_at"]

    # Changing between settled outcomes keeps the existing settled_at.
    loss = clients["bets"].patch(f"/bets/{bet_id}", headers=headers, json={"outcome": "loss"})
    assert loss.json()["settled_at"] == settled["settled_at"]

    assert clients["bets"].delete(f"/bets/{bet_id}", headers=headers).status_code == 204
    assert clients["bets"].get(f"/bets/{bet_id}", headers=headers).status_code == 404


def test_bankroll_updates_on_settle(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"bankroll": 1000, "base_currency": "GBP"})

    bet = _make_bet(clients, headers, odds=2.0, stake=100, outcome="pending", currency="GBP")
    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["bankroll"] == pytest.approx(1000.0)

    clients["bets"].patch(f"/bets/{bet['id']}", headers=headers, json={"outcome": "win"})
    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["bankroll"] == pytest.approx(1100.0)  # +100 profit

    clients["bets"].patch(f"/bets/{bet['id']}", headers=headers, json={"outcome": "loss"})
    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["bankroll"] == pytest.approx(900.0)  # starting + (-100)


def test_bankroll_ignores_other_currency(clients, auth_headers):
    headers, _ = auth_headers
    clients["auth"].patch("/auth/settings", headers=headers, json={"bankroll": 1000, "base_currency": "GBP"})
    _make_bet(clients, headers, odds=2.0, stake=100, outcome="win", currency="USD")
    summary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert summary["bankroll"] == pytest.approx(1000.0)


def test_cannot_touch_another_users_bet(clients, auth_headers):
    headers_a, _ = auth_headers
    bet = _make_bet(clients, headers_a, odds=2.0)
    # second user
    r = clients["auth"].post("/auth/register", json={"email": "intruder@example.com", "password": "password123"})
    headers_b = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert clients["bets"].get(f"/bets/{bet['id']}", headers=headers_b).status_code == 404
    assert clients["bets"].delete(f"/bets/{bet['id']}", headers=headers_b).status_code == 404


# -------------------------------- reports --------------------------------- #

def test_reports_summary_and_breakdown(clients, auth_headers):
    headers, _ = auth_headers
    _make_bet(clients, headers, sport="Rugby", odds=2.5, stake=100, outcome="win")    # +150
    _make_bet(clients, headers, sport="Rugby", odds=2.0, stake=100, outcome="loss")   # -100
    _make_bet(clients, headers, sport="Darts", odds=3.0, stake=50, outcome="void")    # 0

    summary = clients["reports"].get("/reports/summary", headers=headers).json()
    assert summary["settled_bets"] == 3
    assert summary["profit"] == pytest.approx(50.0)
    assert summary["turnover"] == pytest.approx(250.0)
    assert summary["wins"] == 1 and summary["losses"] == 1 and summary["voids"] == 1

    breakdown = clients["reports"].get("/reports/breakdown?dimension=sport", headers=headers).json()
    by_sport = {row["key"]: row["profit"] for row in breakdown}
    assert by_sport["Rugby"] == pytest.approx(50.0)
    assert by_sport["Darts"] == pytest.approx(0.0)


def test_reports_currency_filter_and_primary_currency(clients, auth_headers):
    headers, _ = auth_headers
    _make_bet(clients, headers, currency="GBP", odds=2.0, stake=100, outcome="win")   # +100 GBP
    _make_bet(clients, headers, currency="GBP", odds=2.0, stake=100, outcome="win")   # +100 GBP
    _make_bet(clients, headers, currency="USD", odds=2.0, stake=100, outcome="win")    # +100 USD

    currencies = clients["bets"].get("/bets/currencies", headers=headers).json()
    assert currencies == ["GBP", "USD"]

    primary = clients["reports"].get("/reports/summary?use_primary_currency=true", headers=headers).json()
    assert primary["currency"] == "GBP"
    assert primary["profit"] == pytest.approx(200.0)
    assert primary["settled_bets"] == 2

    usd_only = clients["reports"].get("/reports/summary?currency=USD", headers=headers).json()
    assert usd_only["currency"] == "USD"
    assert usd_only["profit"] == pytest.approx(100.0)
    assert usd_only["settled_bets"] == 1

    mixed = clients["reports"].get("/reports/summary", headers=headers).json()
    assert mixed["currency"] is None
    assert mixed["profit"] == pytest.approx(300.0)


def test_equity_curve_excludes_pending(clients, auth_headers):
    headers, _ = auth_headers
    _make_bet(clients, headers, odds=2.0, stake=100, outcome="win")
    _make_bet(clients, headers, odds=2.0, stake=100, outcome="pending")
    curve = clients["reports"].get("/reports/equity-curve", headers=headers).json()
    assert len(curve) == 1  # pending bet not on the curve


def test_exports(clients, auth_headers):
    headers, _ = auth_headers
    _make_bet(clients, headers, sport="Boxing", odds=2.0, stake=100, outcome="win")

    csv = clients["reports"].get("/reports/export.csv", headers=headers)
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]
    assert b"Boxing" in csv.content

    xlsx = clients["reports"].get("/reports/export.xlsx", headers=headers)
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]
    assert len(xlsx.content) > 1000

    js = clients["reports"].get("/reports/export.json", headers=headers)
    assert js.status_code == 200
    assert "application/json" in js.headers["content-type"]
    rows = js.json()
    assert len(rows) == 1
    assert rows[0]["sport"] == "Boxing"


# ------------------------------- payments --------------------------------- #

def test_payments_health_reports_stripe_off(clients):
    r = clients["payments"].get("/health")
    assert r.status_code == 200
    assert r.json()["stripe_configured"] is False


def test_checkout_requires_stripe_config(clients, auth_headers):
    headers, _ = auth_headers
    r = clients["payments"].post(
        "/payments/checkout-session?success_url=https://x/ok&cancel_url=https://x/no",
        headers=headers,
    )
    assert r.status_code == 503  # billing not configured


# ------------------------------- admin ------------------------------------ #

def _admin_headers(clients):
    r = clients["auth"].post(
        "/auth/login", json={"email": "admin@admin.com", "password": "password"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_admin_endpoints_require_admin(clients, auth_headers):
    headers, _ = auth_headers
    assert clients["auth"].get("/auth/admin/stats", headers=headers).status_code == 403
    assert clients["auth"].get("/auth/admin/users", headers=headers).status_code == 403
    assert clients["auth"].get("/auth/admin/events", headers=headers).status_code == 403


def test_admin_stats_users_and_events(clients, auth_headers):
    user_headers, email = auth_headers
    admin_headers = _admin_headers(clients)

    # User activity generates events.
    clients["auth"].post("/auth/login", json={"email": email, "password": "password123"})
    clients["auth"].patch("/auth/settings", headers=user_headers, json={"bankroll": 500})

    stats = clients["auth"].get("/auth/admin/stats", headers=admin_headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_users"] >= 2
    assert body["logins_today"] >= 2

    users = clients["auth"].get("/auth/admin/users", headers=admin_headers)
    assert users.status_code == 200
    emails = {u["email"] for u in users.json()}
    assert "admin@admin.com" in emails
    assert email in emails
    target = next(u for u in users.json() if u["email"] == email)
    assert target["last_login_at"] is not None

    events = clients["auth"].get("/auth/admin/events", headers=admin_headers)
    assert events.status_code == 200
    types = {e["event_type"] for e in events.json()}
    assert "login" in types
    assert "settings_updated" in types


def test_admin_can_toggle_user_active(clients, auth_headers):
    admin_headers = _admin_headers(clients)
    _, email = auth_headers
    users = clients["auth"].get("/auth/admin/users?search=" + email, headers=admin_headers).json()
    user_id = users[0]["id"]

    disabled = clients["auth"].patch(
        f"/auth/admin/users/{user_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    # Disabled user cannot log in.
    assert clients["auth"].post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).status_code == 403

    enabled = clients["auth"].patch(
        f"/auth/admin/users/{user_id}",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert enabled.status_code == 200
    assert clients["auth"].post(
        "/auth/login", json={"email": email, "password": "password123"}
    ).status_code == 200


def test_admin_cannot_disable_self(clients):
    admin_headers = _admin_headers(clients)
    me = clients["auth"].get("/auth/me", headers=admin_headers).json()
    r = clients["auth"].patch(
        f"/auth/admin/users/{me['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert r.status_code == 400


# --------------------------- public bet share ----------------------------- #

def test_bet_share_lifecycle(clients, auth_headers):
    headers, _ = auth_headers
    bet = _make_bet(
        clients,
        headers,
        event="Ascot 14:30",
        selection="Galileo Gold",
        sport="Horse racing",
        bet_type="Win",
        event_at="2026-06-20T14:30:00+00:00",
        personal_implied_odds=2.2,
        notes="Good ground, drawn well",
    )
    assert bet.get("share_token") is None

    enabled = clients["bets"].post(f"/bets/{bet['id']}/share", headers=headers)
    assert enabled.status_code == 200, enabled.text
    token = enabled.json()["share_token"]
    assert token

    again = clients["bets"].post(f"/bets/{bet['id']}/share", headers=headers)
    assert again.status_code == 200
    assert again.json()["share_token"] == token

    fetched = clients["bets"].get(f"/bets/{bet['id']}", headers=headers)
    assert fetched.json()["share_token"] == token

    public = clients["bets"].get(f"/bets/public/{token}")
    assert public.status_code == 200, public.text
    body = public.json()
    assert body["sport"] == "Horse racing"
    assert body["bet_type"] == "Win"
    assert body["event"] == "Ascot 14:30"
    assert body["selection"] == "Galileo Gold"
    assert body["stake"] == pytest.approx(100)
    assert body["currency"] == "GBP"
    assert body["personal_implied_odds"] == pytest.approx(2.2)
    assert body["notes"] == "Good ground, drawn well"
    assert "profit" not in body
    assert "bookmaker" not in body
    assert "id" not in body

    revoked = clients["bets"].delete(f"/bets/{bet['id']}/share", headers=headers)
    assert revoked.status_code == 204
    assert clients["bets"].get(f"/bets/public/{token}").status_code == 404


def test_public_bet_requires_no_auth(clients, auth_headers):
    headers, _ = auth_headers
    bet = _make_bet(clients, headers)
    token = clients["bets"].post(f"/bets/{bet['id']}/share", headers=headers).json()["share_token"]
    assert clients["bets"].get(f"/bets/public/{token}").status_code == 200
    assert clients["bets"].get("/bets/public/not-a-real-token").status_code == 404


def test_share_page_html(clients, auth_headers):
    headers, _ = auth_headers
    bet = _make_bet(
        clients,
        headers,
        event="Ascot 14:30",
        selection="Galileo Gold",
        sport="Horse racing",
        bet_type="Win",
    )
    token = clients["bets"].post(f"/bets/{bet['id']}/share", headers=headers).json()["share_token"]
    r = clients["bets"].get(f"/bets/share-page/{token}")
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers.get("content-type", "")
    html = r.text
    assert "noindex" in html
    assert 'property="og:title"' in html
    assert "Galileo Gold" in html
    assert "Ascot 14:30" in html
    assert token in html
    assert clients["bets"].get("/bets/share-page/not-a-real-token").status_code == 404

