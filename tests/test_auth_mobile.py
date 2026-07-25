"""Auth refresh, logout, and account deletion flows."""

from __future__ import annotations

from helpers import register_and_verify


def test_login_returns_refresh_token(clients):
    email = "refresh-user@example.com"
    register_and_verify(clients, email)
    r = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123", "client": "android"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_expires_in"] > 0
    # Android clients get shorter access tokens than the web default.
    assert body["expires_in"] <= 30 * 60


def test_refresh_rotates_token(clients):
    email = "rotate@example.com"
    register_and_verify(clients, email)
    login = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123", "client": "android"},
    ).json()
    old_refresh = login["refresh_token"]

    r = clients["auth"].post("/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new_refresh = r.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Old refresh must be rejected (revoked after rotation).
    reused = clients["auth"].post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


def test_logout_revokes_refresh(clients):
    email = "logout@example.com"
    token = register_and_verify(clients, email)
    login = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123", "client": "android"},
    ).json()
    refresh = login["refresh_token"]

    r = clients["auth"].post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        json={"refresh_token": refresh},
    )
    assert r.status_code == 204

    bad = clients["auth"].post("/auth/refresh", json={"refresh_token": refresh})
    assert bad.status_code == 401


def test_delete_account_requires_password(clients):
    email = "delete-me@example.com"
    token = register_and_verify(clients, email)
    headers = {"Authorization": f"Bearer {token}"}

    bad = clients["auth"].request(
        "DELETE",
        "/auth/account",
        headers=headers,
        json={"password": "wrong", "confirm": "DELETE"},
    )
    assert bad.status_code == 400

    ok = clients["auth"].request(
        "DELETE",
        "/auth/account",
        headers=headers,
        json={"password": "password123", "confirm": "DELETE"},
    )
    assert ok.status_code == 204

    me = clients["auth"].get("/auth/me", headers=headers)
    assert me.status_code == 401

    login = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 401


def test_web_deletion_request_and_confirm(clients):
    email = "web-delete@example.com"
    register_and_verify(clients, email)

    r = clients["auth"].post("/auth/account/deletion-request", json={"email": email})
    assert r.status_code == 200, r.text
    deletion_token = r.json().get("deletion_token")
    assert deletion_token

    confirm = clients["auth"].post(
        "/auth/account/deletion-confirm",
        json={"token": deletion_token},
    )
    assert confirm.status_code == 200, confirm.text

    login = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 401


def test_password_change_revokes_refresh(clients):
    email = "pwchange@example.com"
    token = register_and_verify(clients, email)
    login = clients["auth"].post(
        "/auth/login",
        json={"email": email, "password": "password123", "client": "android"},
    ).json()
    refresh = login["refresh_token"]

    r = clients["auth"].post(
        "/auth/password/change",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "password123", "password": "password456!"},
    )
    assert r.status_code == 200, r.text

    bad = clients["auth"].post("/auth/refresh", json={"refresh_token": refresh})
    assert bad.status_code == 401
