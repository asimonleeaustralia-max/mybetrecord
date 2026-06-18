"""Application event logging for admin monitoring."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AppEvent


def log_event(
    db: Session,
    event_type: str,
    *,
    user_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AppEvent(
            event_type=event_type,
            user_id=user_id,
            detail=detail,
            ip_address=ip_address,
        )
    )
