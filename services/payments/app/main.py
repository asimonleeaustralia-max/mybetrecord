"""Payments service — Stripe-backed Pro subscriptions.

This service is the only place that holds the Stripe secret. It turns the
free→Pro upgrade into a Stripe Checkout subscription, lets a Pro user cancel,
and processes Stripe webhooks to keep the cached subscription state on the user
record in sync. Endpoints that need Stripe fail with 503 when it isn't
configured, so the rest of the app keeps working (everyone is simply "free").

Pricing comes from `betrecord_shared.pricing`: a tidy local price near 5 USD
for each of the top-20 currencies. The bettor chooses which currency to pay in
at checkout; the business accepts the FX swing between them.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from betrecord_shared import pricing
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db
from betrecord_shared.events import log_event
from betrecord_shared.models import User
from betrecord_shared.schemas import (
    CheckoutRequest,
    CheckoutSessionOut,
    PlanOut,
    PriceOut,
    PricingOut,
)
from betrecord_shared.security import get_current_user

settings = get_settings()
app = FastAPI(title="mybetrecord · payments", version="0.2.0")

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


# Subscription statuses that grant Pro access.
ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def _stripe_ready() -> bool:
    return stripe is not None and bool(settings.stripe_secret_key)


def _require_stripe():
    if not _stripe_ready():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Billing is not configured. Set STRIPE_SECRET_KEY to enable it.",
        )


def _as_dt(epoch: int | None) -> datetime | None:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "payments", "stripe_configured": _stripe_ready()}


@app.get("/payments/pricing", response_model=PricingOut)
def get_pricing() -> PricingOut:
    """Public Pro pricing for every supported currency."""
    return PricingOut(
        default_currency=pricing.DEFAULT_CURRENCY,
        prices=[PriceOut(**p) for p in pricing.pricing_table()],
    )


@app.get("/payments/plan", response_model=PlanOut)
def get_plan(user: User = Depends(get_current_user)) -> PlanOut:
    """Current subscription state for the signed-in user."""
    return PlanOut(
        plan=user.plan or "free",
        plan_currency=user.plan_currency,
        subscription_status=user.subscription_status,
        subscription_cancel_at_period_end=bool(user.subscription_cancel_at_period_end),
        subscription_current_period_end=user.subscription_current_period_end,
        free_daily_bet_limit=settings.free_daily_bet_limit,
        stripe_configured=_stripe_ready(),
    )


def _ensure_customer(user: User, db: Session) -> str:
    """Return the user's Stripe customer id, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=user.display_name or None,
        metadata={"user_id": user.id},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


@app.post("/payments/checkout-session", response_model=CheckoutSessionOut)
def create_checkout_session(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutSessionOut:
    _require_stripe()
    if user.is_pro:
        raise HTTPException(status.HTTP_409_CONFLICT, "You're already on the Pro plan.")

    currency = pricing.normalise_currency(payload.currency or user.base_currency)
    unit_amount = pricing.stripe_unit_amount(currency)

    price_data = {
        "currency": currency.lower(),
        "unit_amount": unit_amount,
        "recurring": {"interval": "month"},
    }
    if settings.stripe_product_id:
        price_data["product"] = settings.stripe_product_id
    else:
        price_data["product_data"] = {"name": "mybetrecord Pro"}

    customer_id = _ensure_customer(user, db)
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price_data": price_data, "quantity": 1}],
        customer=customer_id,
        client_reference_id=user.id,
        subscription_data={"metadata": {"user_id": user.id, "currency": currency}},
        metadata={"user_id": user.id, "currency": currency},
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    log_event(db, "checkout_started", user_id=user.id, detail=f"{currency} {unit_amount}")
    db.commit()
    return CheckoutSessionOut(id=session.id, url=session.url)


@app.post("/payments/cancel", response_model=PlanOut)
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    """Cancel at period end — the user keeps Pro until the paid period runs out."""
    _require_stripe()
    if not user.stripe_subscription_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active subscription to cancel.")

    sub = stripe.Subscription.modify(
        user.stripe_subscription_id, cancel_at_period_end=True
    )
    user.subscription_cancel_at_period_end = True
    user.subscription_status = sub.get("status", user.subscription_status)
    user.subscription_current_period_end = _as_dt(sub.get("current_period_end"))
    log_event(db, "subscription_cancel_requested", user_id=user.id)
    db.commit()
    db.refresh(user)
    return get_plan(user)


@app.post("/payments/resume", response_model=PlanOut)
def resume_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    """Undo a pending cancellation before the period ends."""
    _require_stripe()
    if not user.stripe_subscription_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No subscription to resume.")
    sub = stripe.Subscription.modify(
        user.stripe_subscription_id, cancel_at_period_end=False
    )
    user.subscription_cancel_at_period_end = False
    user.subscription_status = sub.get("status", user.subscription_status)
    user.subscription_current_period_end = _as_dt(sub.get("current_period_end"))
    log_event(db, "subscription_resumed", user_id=user.id)
    db.commit()
    db.refresh(user)
    return get_plan(user)


# ------------------------------- webhook ---------------------------------- #

def _find_user(db: Session, *, user_id: str | None, customer_id: str | None) -> User | None:
    if user_id:
        user = db.get(User, user_id)
        if user:
            return user
    if customer_id:
        return db.scalar(select(User).where(User.stripe_customer_id == customer_id))
    return None


def _apply_subscription(user: User, sub: dict, db: Session) -> None:
    """Mirror a Stripe subscription object onto the cached user fields."""
    status_str = sub.get("status")
    user.subscription_status = status_str
    user.stripe_subscription_id = sub.get("id") or user.stripe_subscription_id
    if sub.get("customer"):
        user.stripe_customer_id = sub["customer"]
    user.subscription_cancel_at_period_end = bool(sub.get("cancel_at_period_end"))
    user.subscription_current_period_end = _as_dt(sub.get("current_period_end"))

    currency = (sub.get("metadata") or {}).get("currency")
    if not currency:
        items = (sub.get("items") or {}).get("data") or []
        if items:
            currency = (items[0].get("price") or {}).get("currency")
    if currency:
        user.plan_currency = currency.upper()

    user.plan = "pro" if status_str in ACTIVE_STATUSES else "free"
    db.commit()


@app.post("/payments/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    _require_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:  # signature / parse failure
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid webhook: {exc}")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user = _find_user(
            db,
            user_id=obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id"),
            customer_id=obj.get("customer"),
        )
        if user:
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            sub_id = obj.get("subscription")
            if sub_id:
                try:
                    sub = stripe.Subscription.retrieve(sub_id)
                    _apply_subscription(user, sub, db)
                except Exception:
                    user.plan = "pro"
                    user.stripe_subscription_id = sub_id
                    user.subscription_status = "active"
                    db.commit()
            else:
                user.plan = "pro"
                db.commit()

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        user = _find_user(
            db,
            user_id=(obj.get("metadata") or {}).get("user_id"),
            customer_id=obj.get("customer"),
        )
        if user:
            _apply_subscription(user, obj, db)

    elif event_type == "customer.subscription.deleted":
        user = _find_user(
            db,
            user_id=(obj.get("metadata") or {}).get("user_id"),
            customer_id=obj.get("customer"),
        )
        if user:
            user.plan = "free"
            user.subscription_status = obj.get("status") or "canceled"
            user.subscription_cancel_at_period_end = False
            user.stripe_subscription_id = None
            user.subscription_current_period_end = _as_dt(obj.get("current_period_end"))
            db.commit()

    return {"received": True}
