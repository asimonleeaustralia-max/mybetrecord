"""Shared helpers for integration tests."""


def register_and_verify(clients, email: str, password: str = "password123", **extra) -> str:
    """Register a user, verify email, and return an access token."""
    payload = {"email": email, "password": password, **extra}
    r = clients["auth"].post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    verify_token = r.json().get("verification_token")
    assert verify_token, "development mode should return verification_token for tests"
    r = clients["auth"].post("/auth/register/verify", json={"token": verify_token})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
