# Mobile / Android API contract

Base URL (production): `https://www.mybetrecord.com`

All authenticated routes accept `Authorization: Bearer <access_token>`.

## Auth

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/auth/register` | `{email, password, timezone?}` | Sends verification email |
| POST | `/auth/register/verify` | `{token, client?, device_name?}` | Returns token pair |
| POST | `/auth/login` | `{email, password, client?, device_name?}` | `client: "android"` → short-lived access + refresh |
| POST | `/auth/refresh` | `{refresh_token}` | Rotates refresh; reuse revokes family |
| POST | `/auth/logout` | `{refresh_token?, all_devices?}` | Bearer optional if refresh provided |
| POST | `/auth/password-reset/request` | `{email}` | |
| POST | `/auth/password-reset/confirm` | `{token, password}` | Revokes all refresh tokens |
| POST | `/auth/password/change` | `{current_password, password}` | Revokes all refresh tokens |
| GET | `/auth/me` | — | Profile + plan status |
| PATCH | `/auth/settings` | settings fields | |
| DELETE | `/auth/account` | `{password, confirm: "DELETE"}` | Permanent deletion |
| POST | `/auth/account/deletion-request` | `{email}` | Public web deletion path |
| POST | `/auth/account/deletion-confirm` | `{token}` | Confirms email deletion |

### TokenResponse

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "...",
  "refresh_expires_in": 2592000
}
```

## Bets

| Method | Path |
|--------|------|
| GET | `/bets` |
| POST | `/bets` |
| GET | `/bets/{id}` |
| PATCH | `/bets/{id}` |
| DELETE | `/bets/{id}` |

## Reports

| Method | Path |
|--------|------|
| GET | `/reports/summary` |
| GET | `/reports/equity-curve` |
| GET | `/reports/breakdown` |

## Legal URLs (Play Console)

- Privacy: https://www.mybetrecord.com/privacy
- Terms: https://www.mybetrecord.com/terms
- Responsible gambling: https://www.mybetrecord.com/responsible-gambling
- Account deletion (web): https://www.mybetrecord.com/delete-account

## Android billing policy

The Android client must **not** include Stripe checkout, upgrade CTAs, or external payment links for digital subscriptions. Existing Pro entitlements from the website may be displayed as read-only plan status.
