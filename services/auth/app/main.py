"""Auth service — accounts, login, settings, and API keys."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db, init_db
from betrecord_shared.events import log_event
from betrecord_shared.models import ApiKey, AppEvent, Bet, User
from betrecord_shared.schemas import (
    AdminStatsOut,
    AdminUserOut,
    AdminUserUpdate,
    ApiKeyCreated,
    ApiKeyOut,
    AppEventOut,
    SettingsUpdate,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from betrecord_shared.security import (
    create_access_token,
    generate_api_key,
    get_current_admin,
    get_current_user,
    hash_password,
    verify_password,
)

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


@app.on_event("startup")
def _startup() -> None:
    if settings.environment != "production":
        init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth"}


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(
    payload: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    log_event(
        db,
        "register",
        user_id=user.id,
        detail=user.email,
        ip_address=_client_ip(request),
    )
    db.commit()
    db.refresh(user)
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    ip = _client_ip(request)
    if not user or not verify_password(payload.password, user.password_hash):
        log_event(
            db,
            "login_failed",
            user_id=user.id if user else None,
            detail=payload.email.lower(),
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        log_event(db, "login_blocked", user_id=user.id, detail="account disabled", ip_address=ip)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    log_event(db, "login", user_id=user.id, detail=user.email, ip_address=ip)
    db.commit()
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


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
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        bet_count=bet_counts.get(user.id, 0),
        api_key_count=key_counts.get(user.id, 0),
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
        stmt = stmt.where(
            or_(func.lower(User.email).like(term), func.lower(User.display_name).like(term))
        )
    users = db.scalars(stmt.offset(offset).limit(limit)).all()
    user_ids = [u.id for u in users]
    bet_counts, key_counts = _user_counts(db, user_ids)
    return [_admin_user_out(u, bet_counts, key_counts) for u in users]


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
