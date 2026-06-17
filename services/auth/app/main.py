"""Auth service — accounts, login, settings, and API keys."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db, init_db
from betrecord_shared.models import ApiKey, User
from betrecord_shared.schemas import (
    ApiKeyCreated,
    ApiKeyOut,
    SettingsUpdate,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from betrecord_shared.security import (
    create_access_token,
    generate_api_key,
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


@app.on_event("startup")
def _startup() -> None:
    if settings.environment != "production":
        init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth"}


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    token, expires = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires)


@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.patch("/auth/settings", response_model=UserOut)
def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "base_currency" and value:
            value = value.upper()
        setattr(user, field, value)
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
    name: str = "default",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    full, prefix, key_hash = generate_api_key()
    api_key = ApiKey(user_id=user.id, name=name, prefix=prefix, key_hash=key_hash)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    # The ORM row has no `api_key` column (we never store the full key), so build
    # the response from the persisted fields and attach the full key once here.
    out = ApiKeyCreated(**ApiKeyOut.model_validate(api_key).model_dump(), api_key=full)
    return out


@app.delete("/auth/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    api_key = db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
