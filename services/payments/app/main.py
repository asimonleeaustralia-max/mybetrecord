"""Payments service — Stripe scaffold for the eventual subscription.

Deliberately minimal and isolated: it holds the Stripe secret so no other
service does. Wire real price IDs/keys via environment variables when you turn
billing on. Endpoints no-op gracefully when Stripe isn't configured, so the
rest of the app runs fine without it.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from betrecord_shared.config import get_settings
from betrecord_shared.models import User
from betrecord_shared.security import get_current_user

settings = get_settings()
app = FastAPI(title="mybetrecord · payments", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    import stripe  # type: ignore
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
except Exception:  # pragma: no cover
    stripe = None


def _require_stripe():
    if stripe is None or not settings.stripe_secret_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing is not configured. Set STRIPE_SECRET_KEY to enable it.",
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "payments", "stripe_configured": bool(settings.stripe_secret_key)}


@app.post("/payments/checkout-session")
def create_checkout_session(
    success_url: str,
    cancel_url: str,
    user: User = Depends(get_current_user),
):
    _require_stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        customer_email=user.email,
        client_reference_id=user.id,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"id": session.id, "url": session.url}


@app.post("/payments/webhook")
async def webhook(request: Request):
    _require_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:  # signature / parse failure
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid webhook: {exc}")

    # Handle the events you care about. Subscription state would be persisted
    # to the user record here once a billing model is added.
    if event["type"] in ("checkout.session.completed", "customer.subscription.updated"):
        pass

    return {"received": True}
