"""Auth service — accounts, login, settings, and API keys."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db, init_db
from betrecord_shared.email import EmailDeliveryError, send_password_reset_email, send_verification_email
from betrecord_shared.events import log_event
from betrecord_shared.models import ApiKey, AppEvent, Bet, LandingHit, PasswordResetToken, PendingRegistration, User
from betrecord_shared.schemas import (
    AdminAddIn,
    AdminCompProIn,
    AdminStatsOut,
    AdminUserOut,
    AdminUserUpdate,
    ApiKeyCreated,
    ApiKeyOut,
    AppEventOut,
    LandingHitOut,
    LandingTrackIn,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterResponse,
    SettingsUpdate,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
    VerifyEmailConfirm,
)
from betrecord_shared.seed import promote_bootstrap_admin
from betrecord_shared.security import (
    create_access_token,
    generate_api_key,
    generate_password_reset_token,
    get_current_admin,
    get_current_user,
    hash_password,
    hash_password_reset_token,
    verify_password,
)
from betrecord_shared.visitor import client_country, is_bot, parse_browser

settings = get_settings()
app = FastAPI(title="mybetrecord · auth", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@app.on_event("startup")
def _startup() -> None:
    # Bootstrap shared tables on first boot (pg advisory lock; safe on restarts).
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth"}


@app.post("/auth/track/landing", status_code=204)
def track_landing(payload: LandingTrackIn, request: Request, db: Session = Depends(get_db)) -> Response:
    """Record an anonymous home-page visit (called from marketing.js beacon)."""
    ua = request.headers.get("user-agent")
    path = (payload.path or "/").strip()[:255] or "/"
    referrer = (payload.referrer or "").strip()[:512] or None
    promo_code = (payload.promo_code or "").strip()[:64] or None
    if promo_code:
        promo_code = promo_code.upper()
    db.add(
        LandingHit(
            path=path,
            ip_address=_client_ip(request),
            user_agent=ua[:512] if ua else None,
            browser=parse_browser(ua),
            country=client_country(dict(request.headers)),
            is_bot=is_bot(ua),
            referrer=referrer,
            promo_code=promo_code,
        )
    )
    db.commit()
    return Response(status_code=204)


@app.post("/auth/register", response_model=RegisterResponse)
def register(
    payload: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    for row in db.scalars(select(PendingRegistration).where(PendingRegistration.email == email)):
        db.delete(row)
    db.flush()

    raw_token, token_hash = generate_password_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.email_verification_minutes)
    db.add(
        PendingRegistration(
            email=email,
            password_hash=hash_password(payload.password),
            timezone=payload.timezone or "UTC",
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    try:
        send_verification_email(
            email,
            _verification_url(raw_token),
            settings.email_verification_minutes,
        )
    except EmailDeliveryError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to send verification email. Please try again later.",
        ) from exc
    log_event(
        db,
        "register_pending",
        detail=email,
        ip_address=_client_ip(request),
    )
    db.commit()

    response = RegisterResponse(
        message="Check your email for a verification link to activate your account."
    )
    if settings.environment != "production":
        response.verification_token = raw_token
    return response


def _verification_url(raw_token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/app/#/verify-email/{raw_token}"


@app.post("/auth/register/verify", response_model=TokenResponse)
def verify_registration(
    payload: VerifyEmailConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    token_hash = hash_password_reset_token(payload.token)
    now = datetime.now(timezone.utc)
    pending = db.scalar(
        select(PendingRegistration).where(PendingRegistration.token_hash == token_hash)
    )
    ip = _client_ip(request)

    if not pending or _as_utc(pending.expires_at) <= now:
        log_event(db, "register_verify_failed", detail="invalid or expired token", ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link")

    if db.scalar(select(User).where(User.email == pending.email)):
        db.delete(pending)
        log_event(db, "register_verify_failed", detail="email already registered", ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=pending.email,
        password_hash=pending.password_hash,
        timezone=pending.timezone,
    )
    db.add(user)
    db.delete(pending)
    promote_bootstrap_admin(user, db)
    log_event(
        db,
        "register",
        user_id=user.id,
        detail=user.email,
        ip_address=ip,
    )
    db.commit()
    db.refresh(user)
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    ip = _client_ip(request)
    if not user or not verify_password(payload.password, user.password_hash):
        pending = db.scalar(select(PendingRegistration).where(PendingRegistration.email == email))
        if pending and verify_password(payload.password, pending.password_hash):
            log_event(
                db,
                "login_blocked",
                detail="email not verified",
                ip_address=ip,
            )
            db.commit()
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Please verify your email before signing in. Check your inbox for the verification link.",
            )
        log_event(
            db,
            "login_failed",
            user_id=user.id if user else None,
            detail=email,
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        log_event(db, "login_blocked", user_id=user.id, detail="account disabled", ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    promote_bootstrap_admin(user, db)
    log_event(db, "login", user_id=user.id, detail=user.email, ip_address=ip)
    db.commit()
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


_PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


def _reset_url(raw_token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/app/#/reset-password/{raw_token}"


def _invalidate_reset_tokens(db: Session, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    for row in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
    ):
        row.used_at = now


@app.post("/auth/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    ip = _client_ip(request)
    raw_token: str | None = None

    if user and user.is_active:
        _invalidate_reset_tokens(db, user.id)
        raw_token, token_hash = generate_password_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_minutes)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        try:
            send_password_reset_email(
                user.email,
                _reset_url(raw_token),
                settings.password_reset_minutes,
            )
        except EmailDeliveryError as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Unable to send password reset email. Please try again later.",
            ) from exc
        log_event(
            db,
            "password_reset_requested",
            user_id=user.id,
            detail=user.email,
            ip_address=ip,
        )
        db.commit()
    elif user and not user.is_active:
        log_event(
            db,
            "password_reset_blocked",
            user_id=user.id,
            detail="account disabled",
            ip_address=ip,
        )
        db.commit()

    response = PasswordResetResponse(message=_PASSWORD_RESET_MESSAGE)
    if raw_token and settings.environment != "production":
        response.reset_token = raw_token
    return response


@app.post("/auth/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    token_hash = hash_password_reset_token(payload.token)
    now = datetime.now(timezone.utc)
    reset_row = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    ip = _client_ip(request)

    if (
        not reset_row
        or reset_row.used_at is not None
        or _as_utc(reset_row.expires_at) <= now
    ):
        log_event(db, "password_reset_failed", detail="invalid or expired token", ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link")

    user = db.get(User, reset_row.user_id)
    if not user or not user.is_active:
        log_event(
            db,
            "password_reset_failed",
            user_id=reset_row.user_id,
            detail="account missing or disabled",
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link")

    user.password_hash = hash_password(payload.password)
    reset_row.used_at = now
    _invalidate_reset_tokens(db, user.id)
    log_event(
        db,
        "password_reset_completed",
        user_id=user.id,
        detail=user.email,
        ip_address=ip,
    )
    db.commit()
    return PasswordResetResponse(message="Password updated. You can sign in with your new password.")


@app.post("/auth/password/change", response_model=PasswordResetResponse)
def change_password(
    payload: PasswordChange,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.password)
    _invalidate_reset_tokens(db, user.id)
    log_event(
        db,
        "password_changed",
        user_id=user.id,
        detail=user.email,
        ip_address=_client_ip(request),
    )
    db.commit()
    return PasswordResetResponse(message="Password updated.")


@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.patch("/auth/settings", response_model=UserOut)
def update_settings(
    payload: SettingsUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "base_currency" and value:
            value = value.upper()
        setattr(user, field, value)
    log_event(db, "settings_updated", user_id=user.id, ip_address=_client_ip(request))
    db.commit()
    db.refresh(user)
    return user


# ------------------------------ API keys ---------------------------------- #

@app.get("/auth/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    ).all()


@app.post("/auth/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    request: Request,
    name: str = "default",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    full, prefix, key_hash = generate_api_key()
    api_key = ApiKey(user_id=user.id, name=name, prefix=prefix, key_hash=key_hash)
    db.add(api_key)
    log_event(
        db,
        "api_key_created",
        user_id=user.id,
        detail=name,
        ip_address=_client_ip(request),
    )
    db.commit()
    db.refresh(api_key)
    # The ORM row has no `api_key` column (we never store the full key), so build
    # the response from the persisted fields and attach the full key once here.
    out = ApiKeyCreated(**ApiKeyOut.model_validate(api_key).model_dump(), api_key=full)
    return out


@app.delete("/auth/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def revoke_api_key(
    key_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked = True
    log_event(
        db,
        "api_key_revoked",
        user_id=user.id,
        detail=api_key.name,
        ip_address=_client_ip(request),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------- Admin ------------------------------------ #

def _user_counts(db: Session, user_ids: list[str]) -> tuple[dict[str, int], dict[str, int]]:
    if not user_ids:
        return {}, {}
    bet_rows = db.execute(
        select(Bet.user_id, func.count())
        .where(Bet.user_id.in_(user_ids))
        .group_by(Bet.user_id)
    ).all()
    key_rows = db.execute(
        select(ApiKey.user_id, func.count())
        .where(ApiKey.user_id.in_(user_ids), ApiKey.revoked.is_(False))
        .group_by(ApiKey.user_id)
    ).all()
    return dict(bet_rows), dict(key_rows)


def _admin_user_out(
    user: User,
    bet_counts: dict[str, int],
    key_counts: dict[str, int],
) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        base_currency=user.base_currency,
        preferred_locale=user.preferred_locale,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        bet_count=bet_counts.get(user.id, 0),
        api_key_count=key_counts.get(user.id, 0),
        plan=user.plan or "free",
        comp_pro_until=user.comp_pro_until,
        is_pro=user.is_pro,
    )


@app.get("/auth/admin/stats", response_model=AdminStatsOut)
def admin_stats(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)) -> AdminStatsOut:
    today = _start_of_today()
    return AdminStatsOut(
        total_users=db.scalar(select(func.count()).select_from(User)) or 0,
        active_users=db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
        admin_users=db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True))) or 0,
        total_bets=db.scalar(select(func.count()).select_from(Bet)) or 0,
        signups_today=db.scalar(
            select(func.count()).select_from(User).where(User.created_at >= today)
        )
        or 0,
        logins_today=db.scalar(
            select(func.count()).select_from(AppEvent).where(
                AppEvent.event_type == "login", AppEvent.created_at >= today
            )
        )
        or 0,
        events_today=db.scalar(
            select(func.count()).select_from(AppEvent).where(AppEvent.created_at >= today)
        )
        or 0,
        landing_hits_today=db.scalar(
            select(func.count()).select_from(LandingHit).where(LandingHit.created_at >= today)
        )
        or 0,
        landing_unique_ips_today=db.scalar(
            select(func.count(func.distinct(LandingHit.ip_address))).select_from(LandingHit).where(
                LandingHit.created_at >= today, LandingHit.ip_address.isnot(None)
            )
        )
        or 0,
    )


@app.get("/auth/admin/users", response_model=list[AdminUserOut])
def admin_list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = None,
) -> list[AdminUserOut]:
    stmt = select(User).order_by(User.created_at.desc())
    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(User.email).like(term))
    users = db.scalars(stmt.offset(offset).limit(limit)).all()
    user_ids = [u.id for u in users]
    bet_counts, key_counts = _user_counts(db, user_ids)
    return [_admin_user_out(u, bet_counts, key_counts) for u in users]


@app.get("/auth/admin/admins", response_model=list[AdminUserOut])
def admin_list_admins(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserOut]:
    users = db.scalars(
        select(User).where(User.is_admin.is_(True)).order_by(User.email)
    ).all()
    user_ids = [u.id for u in users]
    bet_counts, key_counts = _user_counts(db, user_ids)
    return [_admin_user_out(u, bet_counts, key_counts) for u in users]


@app.post("/auth/admin/admins", response_model=AdminUserOut, status_code=201)
def admin_add_admin(
    payload: AdminAddIn,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.is_admin:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already an admin")
    user.is_admin = True
    log_event(
        db,
        "admin.user_update",
        user_id=admin.id,
        detail=f"target={user.email}; is_admin=True",
        ip_address=_client_ip(request),
    )
    db.commit()
    db.refresh(user)
    bet_counts, key_counts = _user_counts(db, [user.id])
    return _admin_user_out(user, bet_counts, key_counts)


@app.delete("/auth/admin/admins/{user_id}", response_model=AdminUserOut)
def admin_remove_admin(
    user_id: str,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove your own admin access")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not user.is_admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not an admin")
    user.is_admin = False
    log_event(
        db,
        "admin.user_update",
        user_id=admin.id,
        detail=f"target={user.email}; is_admin=False",
        ip_address=_client_ip(request),
    )
    db.commit()
    db.refresh(user)
    bet_counts, key_counts = _user_counts(db, [user.id])
    return _admin_user_out(user, bet_counts, key_counts)


@app.patch("/auth/admin/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    data = payload.model_dump(exclude_unset=True)
    if user_id == admin.id:
        if data.get("is_admin") is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove your own admin access")
        if data.get("is_active") is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot disable your own account")

    changes: list[str] = []
    for field, value in data.items():
        if getattr(user, field) != value:
            changes.append(f"{field}={value}")
            setattr(user, field, value)

    if changes:
        log_event(
            db,
            "admin.user_update",
            user_id=admin.id,
            detail=f"target={user.email}; " + ", ".join(changes),
            ip_address=_client_ip(request),
        )
    db.commit()
    db.refresh(user)
    bet_counts, key_counts = _user_counts(db, [user.id])
    return _admin_user_out(user, bet_counts, key_counts)


@app.patch("/auth/admin/users/{user_id}/comp-pro", response_model=AdminUserOut)
def admin_comp_pro(
    user_id: str,
    payload: AdminCompProIn,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    until = payload.comp_pro_until
    if until is not None and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    user.comp_pro_until = until
    if until:
        detail = f"target={user.email}; comp_pro_until={until.isoformat()}"
    else:
        detail = f"target={user.email}; comp_pro_until=cleared"
    log_event(
        db,
        "admin.comp_pro",
        user_id=admin.id,
        detail=detail,
        ip_address=_client_ip(request),
    )
    db.commit()
    db.refresh(user)
    bet_counts, key_counts = _user_counts(db, [user.id])
    return _admin_user_out(user, bet_counts, key_counts)


@app.get("/auth/admin/events", response_model=list[AppEventOut])
def admin_list_events(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    user_id: str | None = None,
) -> list[AppEventOut]:
    stmt = (
        select(AppEvent, User.email)
        .outerjoin(User, AppEvent.user_id == User.id)
        .order_by(AppEvent.created_at.desc())
    )
    if event_type:
        stmt = stmt.where(AppEvent.event_type == event_type)
    if user_id:
        stmt = stmt.where(AppEvent.user_id == user_id)

    rows = db.execute(stmt.offset(offset).limit(limit)).all()
    return [
        AppEventOut(
            id=event.id,
            user_id=event.user_id,
            user_email=email,
            event_type=event.event_type,
            detail=event.detail,
            ip_address=event.ip_address,
            created_at=event.created_at,
        )
        for event, email in rows
    ]


@app.get("/auth/admin/landing-hits", response_model=list[LandingHitOut])
def admin_list_landing_hits(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[LandingHitOut]:
    hits = db.scalars(
        select(LandingHit).order_by(LandingHit.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [LandingHitOut.model_validate(h) for h in hits]
