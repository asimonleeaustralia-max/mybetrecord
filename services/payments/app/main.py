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

import logging
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from betrecord_shared import pricing, promo as promo_lib
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db
from betrecord_shared.events import log_event
from betrecord_shared.models import LandingHit, PromoCode, PromoRedemption, User
from betrecord_shared.schemas import (
    CheckoutRequest,
    CheckoutSessionOut,
    PlanOut,
    PortalSessionOut,
    PortalSessionRequest,
    PriceOut,
    PricingOut,
    PromoCodeCreate,
    PromoCodeOut,
    PromoCodeStatsOut,
    PromoCodeUpdate,
    PromoRedemptionOut,
    PromoReferralOut,
    PromoValidationOut,
)
from betrecord_shared.security import get_current_admin, get_current_user

settings = get_settings()
logger = logging.getLogger(__name__)
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


def _coupon_summary(coupon: dict) -> str:
    """Human-readable discount description from a Stripe coupon object."""
    parts: list[str] = []
    if coupon.get("percent_off"):
        parts.append(f"{coupon['percent_off']:.0f}% off")
    elif coupon.get("amount_off"):
        amount = coupon["amount_off"] / 100
        ccy = (coupon.get("currency") or "").upper()
        parts.append(f"{amount:g} {ccy} off".strip())

    duration = coupon.get("duration")
    months = coupon.get("duration_in_months")
    if duration == "once":
        parts.append("first invoice")
    elif duration == "repeating" and months:
        parts.append(f"for {months} month{'s' if months != 1 else ''}")
    elif duration == "forever":
        parts.append("ongoing")

    return " ".join(parts) if parts else "Discount applied"


def _promo_validation_out(promo: PromoCode, *, already_used: bool = False) -> PromoValidationOut:
    months = promo_lib.discount_months(promo)
    duration = "repeating" if months or promo.promo_type == promo_lib.PROMO_TYPE_FREE_MONTHS else "forever"
    duration_months = promo.free_months if promo.promo_type == promo_lib.PROMO_TYPE_FREE_MONTHS else months
    return PromoValidationOut(
        valid=True,
        code=promo.code,
        summary=promo_lib.build_summary(promo),
        terms=promo_lib.build_terms(promo),
        promo_type=promo.promo_type,
        free_months=promo.free_months,
        percent_off=promo.percent_off,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        already_used=already_used,
        duration=duration,
        duration_in_months=duration_months,
    )


def _invalid_promo_out(code: str, *, already_used: bool = False) -> PromoValidationOut:
    return PromoValidationOut(valid=False, code=promo_lib.normalise_code(code), already_used=already_used)


def _resolve_promotion_code(
    code: str,
    user: User,
    db: Session,
) -> tuple[str, PromoCode]:
    """Return (Stripe promotion_code id, local PromoCode) after validation."""
    promo, err = promo_lib.validate_promo_for_user(db, code, user)
    if err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)
    return promo.stripe_promotion_code_id, promo


def _promo_code_out(db: Session, promo: PromoCode) -> PromoCodeOut:
    ref_count = int(
        db.scalar(
            select(func.count())
            .select_from(LandingHit)
            .where(LandingHit.promo_code == promo.code)
        )
        or 0
    )
    return PromoCodeOut(
        id=promo.id,
        code=promo.code,
        promo_type=promo.promo_type,
        free_months=promo.free_months,
        percent_off=promo.percent_off,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        max_redemptions=promo.max_redemptions,
        active=promo.active,
        description=promo.description,
        redemption_count=promo_lib.redemption_count(db, promo.id),
        referral_count=ref_count,
        created_at=promo.created_at,
        updated_at=promo.updated_at,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "payments", "stripe_configured": _stripe_ready()}


def _pricing_out() -> PricingOut:
    return PricingOut(
        default_currency=pricing.DEFAULT_CURRENCY,
        prices=[PriceOut(**p) for p in pricing.pricing_table()],
    )


@app.get("/payments/pricing", response_model=PricingOut)
def get_pricing() -> PricingOut:
    """Public Pro pricing for every supported currency."""
    return _pricing_out()


@app.get("/payments/promo", response_model=PromoValidationOut)
def validate_promo(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PromoValidationOut:
    """Check whether a promotion code is valid for this account and describe its terms."""
    if not code or not code.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Promotion code is required.")

    normalized = promo_lib.normalise_code(code)
    promo = promo_lib.get_promo_by_code(db, normalized)
    if not promo:
        return _invalid_promo_out(code)

    if promo_lib.user_has_redeemed(db, promo.id, user.id):
        return _invalid_promo_out(code, already_used=True)

    promo_obj, err = promo_lib.validate_promo_for_user(
        db, code, user, require_stripe=_stripe_ready()
    )
    if err:
        return _invalid_promo_out(code)

    return _promo_validation_out(promo_obj)


@app.get("/payments/plan", response_model=PlanOut)
def get_plan(user: User = Depends(get_current_user)) -> PlanOut:
    """Current subscription state for the signed-in user."""
    stripe_ready = _stripe_ready()
    billing_plan = user.plan or "free"
    effective = "pro" if user.is_pro else "free"
    return PlanOut(
        plan=effective,
        billing_plan=billing_plan,
        plan_currency=user.plan_currency,
        subscription_status=user.subscription_status,
        subscription_cancel_at_period_end=bool(user.subscription_cancel_at_period_end),
        subscription_current_period_end=user.subscription_current_period_end,
        comp_pro_until=user.comp_pro_until,
        free_daily_bet_limit=settings.free_daily_bet_limit,
        stripe_configured=stripe_ready,
        pricing=_pricing_out() if stripe_ready else None,
    )


def _ensure_customer(user: User, db: Session) -> str:
    """Return the user's Stripe customer id, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=user.email,
        metadata={"user_id": user.id},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


@app.post("/payments/checkout-session", response_model=CheckoutSessionOut)
def create_checkout_session(
    payload: CheckoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutSessionOut:
    _require_stripe()
    if user.is_pro:
        raise HTTPException(status.HTTP_409_CONFLICT, "You're already on the Pro plan.")

    currency = pricing.normalise_currency(
        payload.currency
        or pricing.currency_for_locale(user.preferred_locale)
        or user.base_currency
    )
    unit_amount = pricing.stripe_unit_amount(currency)
    checkout_locale = payload.locale or pricing.stripe_checkout_locale(user.preferred_locale)

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
    promo_record: PromoCode | None = None
    referrer = (request.headers.get("referer") or "")[:512] or None
    session_kwargs: dict = {
        "mode": "subscription",
        "line_items": [{"price_data": price_data, "quantity": 1}],
        "customer": customer_id,
        "client_reference_id": user.id,
        "locale": checkout_locale,
        "subscription_data": {"metadata": {"user_id": user.id, "currency": currency}},
        "metadata": {"user_id": user.id, "currency": currency},
        "success_url": payload.success_url,
        "cancel_url": payload.cancel_url,
    }
    if payload.promotion_code:
        promo_id, promo_record = _resolve_promotion_code(payload.promotion_code, user, db)
        session_kwargs["discounts"] = [{"promotion_code": promo_id}]
        session_kwargs["metadata"]["promo_code"] = promo_record.code
        if referrer:
            session_kwargs["metadata"]["referrer"] = referrer

    session = stripe.checkout.Session.create(**session_kwargs)
    detail = f"{currency} {unit_amount}"
    if payload.promotion_code:
        detail += f" promo={payload.promotion_code.strip()}"
    log_event(db, "checkout_started", user_id=user.id, detail=detail)
    db.commit()
    return CheckoutSessionOut(id=session.id, url=session.url)


@app.post("/payments/portal-session", response_model=PortalSessionOut)
def create_portal_session(
    payload: PortalSessionRequest,
    user: User = Depends(get_current_user),
) -> PortalSessionOut:
    """Stripe Customer Portal — update payment method, view invoices."""
    _require_stripe()
    if not user.stripe_customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No billing account yet.")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=payload.return_url,
    )
    return PortalSessionOut(url=session.url)


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


# ----------------------------- admin promo codes --------------------------- #

def _validate_promo_create(payload: PromoCodeCreate) -> None:
    if payload.promo_type == promo_lib.PROMO_TYPE_FREE_MONTHS and not payload.free_months:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "free_months is required for free-month promos.")
    if payload.promo_type == promo_lib.PROMO_TYPE_PERCENT_DISCOUNT:
        if not payload.percent_off:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "percent_off is required for percent-discount promos.",
            )
        if not payload.valid_until:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "valid_until is required for percent-discount promos.",
            )
    if payload.valid_from and payload.valid_until and payload.valid_from >= payload.valid_until:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_until must be after valid_from.")


@app.get("/payments/admin/promo-codes", response_model=list[PromoCodeOut])
def admin_list_promo_codes(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[PromoCodeOut]:
    promos = db.scalars(select(PromoCode).order_by(PromoCode.created_at.desc())).all()
    return [_promo_code_out(db, p) for p in promos]


@app.post("/payments/admin/promo-codes", response_model=PromoCodeOut, status_code=201)
def admin_create_promo_code(
    payload: PromoCodeCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PromoCodeOut:
    _validate_promo_create(payload)
    code = promo_lib.normalise_code(payload.code)
    if db.scalar(select(PromoCode.id).where(PromoCode.code == code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A promo code with that value already exists.")

    promo = PromoCode(
        code=code,
        promo_type=payload.promo_type,
        free_months=payload.free_months,
        percent_off=payload.percent_off,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        max_redemptions=payload.max_redemptions,
        active=payload.active,
        description=payload.description,
    )
    db.add(promo)
    db.flush()

    if _stripe_ready():
        try:
            promo_lib.sync_promo_to_stripe(promo, stripe)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Could not create Stripe promotion: {exc}",
            ) from exc

    log_event(db, "admin.promo_created", user_id=admin.id, detail=code)
    db.commit()
    db.refresh(promo)
    return _promo_code_out(db, promo)


@app.patch("/payments/admin/promo-codes/{promo_id}", response_model=PromoCodeOut)
def admin_update_promo_code(
    promo_id: str,
    payload: PromoCodeUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PromoCodeOut:
    promo = db.get(PromoCode, promo_id)
    if not promo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Promo code not found.")

    data = payload.model_dump(exclude_unset=True)
    if "valid_from" in data or "valid_until" in data:
        vf = data.get("valid_from", promo.valid_from)
        vu = data.get("valid_until", promo.valid_until)
        if vf and vu and vf >= vu:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "valid_until must be after valid_from.")

    was_active = promo.active
    for key, value in data.items():
        setattr(promo, key, value)

    if _stripe_ready() and "active" in data and data["active"] != was_active:
        try:
            promo_lib.set_stripe_promo_active(promo, promo.active, stripe)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Could not update Stripe promotion: {exc}",
            ) from exc

    log_event(db, "admin.promo_updated", user_id=admin.id, detail=promo.code)
    db.commit()
    db.refresh(promo)
    return _promo_code_out(db, promo)


@app.get("/payments/admin/promo-codes/{promo_id}/stats", response_model=PromoCodeStatsOut)
def admin_promo_code_stats(
    promo_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> PromoCodeStatsOut:
    promo = db.get(PromoCode, promo_id)
    if not promo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Promo code not found.")

    redemptions = db.scalars(
        select(PromoRedemption)
        .where(PromoRedemption.promo_code_id == promo.id)
        .order_by(PromoRedemption.redeemed_at.desc())
        .limit(limit)
    ).all()

    redemption_out: list[PromoRedemptionOut] = []
    currencies: dict[str, int] = {}
    for r in redemptions:
        email = r.user.email if r.user else None
        redemption_out.append(
            PromoRedemptionOut(
                user_id=r.user_id,
                user_email=email,
                currency=r.currency,
                referrer=r.referrer,
                redeemed_at=r.redeemed_at,
            )
        )
        if r.currency:
            currencies[r.currency] = currencies.get(r.currency, 0) + 1

    hits = db.scalars(
        select(LandingHit)
        .where(LandingHit.promo_code == promo.code)
        .order_by(LandingHit.created_at.desc())
        .limit(limit)
    ).all()
    referrals = [
        PromoReferralOut(
            created_at=h.created_at,
            path=h.path,
            ip_address=h.ip_address,
            referrer=h.referrer,
            country=h.country,
            is_bot=h.is_bot,
        )
        for h in hits
    ]

    return PromoCodeStatsOut(
        promo=_promo_code_out(db, promo),
        redemptions=redemption_out,
        referrals=referrals,
        currencies=currencies,
    )


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


def _record_promo_redemption(
    db: Session,
    user: User,
    session_obj: dict,
) -> None:
    """Persist promo redemption when checkout completed with a discount."""
    metadata = session_obj.get("metadata") or {}
    code = metadata.get("promo_code")
    if not code:
        total_details = session_obj.get("total_details") or {}
        if not total_details.get("amount_discount"):
            return
        discounts = session_obj.get("discounts") or []
        if discounts:
            promo_ref = discounts[0].get("promotion_code")
            if isinstance(promo_ref, dict):
                code = promo_ref.get("code")
            elif promo_ref and stripe:
                try:
                    promo_obj = stripe.PromotionCode.retrieve(promo_ref)
                    code = promo_obj.code
                except Exception:
                    return
    if not code:
        return

    promo = promo_lib.get_promo_by_code(db, code)
    if not promo:
        return
    if promo_lib.user_has_redeemed(db, promo.id, user.id):
        return

    currency = (metadata.get("currency") or "").upper() or None
    if not currency:
        currency = (session_obj.get("currency") or "").upper() or None

    db.add(
        PromoRedemption(
            promo_code_id=promo.id,
            user_id=user.id,
            currency=currency,
            stripe_checkout_session_id=session_obj.get("id"),
            referrer=(metadata.get("referrer") or "")[:512] or None,
        )
    )
    log_event(db, "promo_redeemed", user_id=user.id, detail=promo.code)
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
            try:
                _record_promo_redemption(db, user, obj)
            except Exception:
                logger.debug("Could not record promo redemption", exc_info=True)

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

    else:
        logger.debug("Unhandled Stripe webhook event: %s", event_type)

    return {"received": True}
