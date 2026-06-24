"""Outbound email helpers."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Outbound email could not be sent."""


def send_email(to: str, subject: str, body_text: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        if settings.environment == "development":
            print(f"[email] To: {to}\nSubject: {subject}\n\n{body_text}", flush=True)
            return
        logger.error("SMTP not configured; email to %s was not sent", to)
        raise EmailDeliveryError(f"SMTP not configured; email to {to} was not sent")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(body_text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except smtplib.SMTPException as exc:
        logger.exception("SMTP delivery failed for %s", to)
        raise EmailDeliveryError(f"SMTP delivery failed for {to}") from exc


def send_verification_email(to: str, verify_url: str, expires_minutes: int) -> None:
    subject = "Verify your mybetrecord email address"
    body = (
        "Thanks for signing up for mybetrecord.\n\n"
        f"Open this link to verify your email and activate your account "
        f"(valid for {expires_minutes} minutes):\n"
        f"{verify_url}\n\n"
        "If you did not create an account, you can ignore this email.\n"
    )
    send_email(to, subject, body)


def send_password_reset_email(to: str, reset_url: str, expires_minutes: int) -> None:
    subject = "Reset your mybetrecord password"
    body = (
        "You requested a password reset for your mybetrecord account.\n\n"
        f"Open this link to choose a new password (valid for {expires_minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    send_email(to, subject, body)
