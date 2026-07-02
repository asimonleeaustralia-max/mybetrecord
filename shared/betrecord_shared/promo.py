"""Promo code validation, human-readable terms, and Stripe sync."""

from __future__ import annotations

import secrets

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import pricing

if TYPE_CHECKING:
    from .models import PromoCode, PromoRedemption, User


PROMO_TYPE_FREE_MONTHS = "free_months"
PROMO_TYPE_PERCENT_DISCOUNT = "percent_discount"
PROMO_TYPES = {PROMO_TYPE_FREE_MONTHS, PROMO_TYPE_PERCENT_DISCOUNT}


def normalise_code(code: str) -> str:
    return code.strip().upper()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d %b %Y")


def discount_months(promo: PromoCode) -> int | None:
    """Months of repeating percent discount derived from the promo date window."""
    if promo.promo_type != PROMO_TYPE_PERCENT_DISCOUNT:
        return None
    if promo.valid_from and promo.valid_until:
        days = (promo.valid_until - promo.valid_from).days
        return max(1, (days + 29) // 30)
    return None


def build_summary(promo: PromoCode) -> str:
    if promo.promo_type == PROMO_TYPE_FREE_MONTHS:
        months = promo.free_months or 0
        return f"{months} month{'s' if months != 1 else ''} free"
    percent = promo.percent_off or 0
    months = discount_months(promo)
    if months:
        return f"{percent:.0f}% off for {months} month{'s' if months != 1 else ''}"
    return f"{percent:.0f}% off monthly Pro"


def build_terms(promo: PromoCode) -> str:
    """Full terms shown to the user at checkout."""
    parts: list[str] = []
    if promo.promo_type == PROMO_TYPE_FREE_MONTHS:
        months = promo.free_months or 0
        parts.append(
            f"You get {months} calendar month{'s' if months != 1 else ''} of mybetrecord Pro "
            "at no charge. After that, your subscription continues at the standard monthly price "
            "unless you cancel before the free period ends."
        )
    else:
        percent = promo.percent_off or 0
        months = discount_months(promo)
        if months:
            parts.append(
                f"{percent:.0f}% off your monthly Pro subscription for {months} "
                f"month{'s' if months != 1 else ''}. Standard pricing applies afterwards."
            )
        else:
            parts.append(f"{percent:.0f}% off your monthly Pro subscription.")

    if promo.valid_from and promo.valid_until:
        parts.append(
            f"Code must be redeemed between {_format_dt(promo.valid_from)} "
            f"and {_format_dt(promo.valid_until)} (UTC)."
        )
    elif promo.valid_until:
        parts.append(f"Code must be redeemed by {_format_dt(promo.valid_until)} (UTC).")
    elif promo.valid_from:
        parts.append(f"Code available from {_format_dt(promo.valid_from)} (UTC).")

    parts.append("One use per account. Cannot be combined with other offers.")
    if promo.description:
        parts.append(promo.description.strip())
    return " ".join(parts)


def estimated_discount_value(promo: PromoCode, currency: str | None) -> float:
    """Estimated total discount for one redemption in the given checkout currency."""
    monthly = pricing.price_amount(pricing.normalise_currency(currency))
    if promo.promo_type == PROMO_TYPE_FREE_MONTHS:
        return (promo.free_months or 0) * monthly
    percent = promo.percent_off or 0
    months = discount_months(promo)
    if months:
        return (percent / 100.0) * monthly * months
    return (percent / 100.0) * monthly


def new_stats_token(db: Session) -> str:
    from .models import PromoCode

    for _ in range(10):
        token = secrets.token_urlsafe(16)
        existing = db.scalar(select(PromoCode.id).where(PromoCode.stats_token == token))
        if not existing:
            return token
    raise RuntimeError("Could not create promo stats link")


def redemption_count(db: Session, promo_id: str) -> int:
    from .models import PromoRedemption

    return int(
        db.scalar(
            select(func.count())
            .select_from(PromoRedemption)
            .where(PromoRedemption.promo_code_id == promo_id)
        )
        or 0
    )


def user_has_redeemed(db: Session, promo_id: str, user_id: str) -> bool:
    from .models import PromoRedemption

    return (
        db.scalar(
            select(PromoRedemption.id).where(
                PromoRedemption.promo_code_id == promo_id,
                PromoRedemption.user_id == user_id,
            )
        )
        is not None
    )


def get_promo_by_code(db: Session, code: str) -> PromoCode | None:
    from .models import PromoCode

    return db.scalar(select(PromoCode).where(PromoCode.code == normalise_code(code)))


def validate_promo_for_user(
    db: Session,
    code: str,
    user: User | None = None,
    *,
    require_stripe: bool = True,
) -> tuple[PromoCode | None, str | None]:
    """Return (promo, error_message). error_message is set when invalid."""
    promo = get_promo_by_code(db, code)
    if not promo:
        return None, "Invalid or expired promotion code."
    if not promo.active:
        return None, "This promotion code is no longer active."

    now = _now()
    if promo.valid_from and now < promo.valid_from:
        return None, f"This code is not active until {_format_dt(promo.valid_from)} (UTC)."
    if promo.valid_until and now > promo.valid_until:
        return None, "This promotion code has expired."

    if promo.max_redemptions is not None:
        if redemption_count(db, promo.id) >= promo.max_redemptions:
            return None, "This promotion code has reached its redemption limit."

    if user and user_has_redeemed(db, promo.id, user.id):
        return None, "You have already used this promotion code on your account."

    if promo.promo_type == PROMO_TYPE_FREE_MONTHS and not promo.free_months:
        return None, "This promotion code is misconfigured."
    if promo.promo_type == PROMO_TYPE_PERCENT_DISCOUNT and not promo.percent_off:
        return None, "This promotion code is misconfigured."

    if not promo.stripe_promotion_code_id and require_stripe:
        return None, "This promotion code is not yet available for checkout."

    return promo, None


def sync_promo_to_stripe(promo: PromoCode, stripe_module) -> None:
    """Create Stripe coupon + promotion code for a local promo record."""
    if promo.promo_type == PROMO_TYPE_FREE_MONTHS:
        coupon = stripe_module.Coupon.create(
            percent_off=100,
            duration="repeating",
            duration_in_months=promo.free_months,
            name=f"Pro free — {promo.code}",
        )
    else:
        months = discount_months(promo)
        coupon_kwargs: dict = {
            "percent_off": promo.percent_off,
            "name": f"Pro discount — {promo.code}",
        }
        if months:
            coupon_kwargs["duration"] = "repeating"
            coupon_kwargs["duration_in_months"] = months
        else:
            coupon_kwargs["duration"] = "forever"
        coupon = stripe_module.Coupon.create(**coupon_kwargs)

    promo_kwargs: dict = {
        "coupon": coupon.id,
        "code": promo.code,
        "active": promo.active,
    }
    if promo.max_redemptions is not None:
        promo_kwargs["max_redemptions"] = promo.max_redemptions
    if promo.valid_until:
        promo_kwargs["expires_at"] = int(promo.valid_until.timestamp())

    stripe_promo = stripe_module.PromotionCode.create(**promo_kwargs)
    promo.stripe_coupon_id = coupon.id
    promo.stripe_promotion_code_id = stripe_promo.id


def set_stripe_promo_active(promo: PromoCode, active: bool, stripe_module) -> None:
    if not promo.stripe_promotion_code_id:
        return
    stripe_module.PromotionCode.modify(promo.stripe_promotion_code_id, active=active)
