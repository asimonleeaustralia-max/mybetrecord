# mybetrecord Android

Native Kotlin / Jetpack Compose client for [mybetrecord](https://www.mybetrecord.com).

- **Package / applicationId:** `com.mybetrecord.android`
- **minSdk 26 · targetSdk 36 · compileSdk 36**
- **Stack:** Compose Material 3, Hilt, Retrofit, OkHttp, Kotlin Serialization, Navigation, Room, EncryptedSharedPreferences

This app is a private betting ledger. It does **not** accept wagers, sell subscriptions, or include Stripe/checkout/upgrade CTAs.

## First-time setup: Gradle wrapper JAR

This repo does not commit the binary `gradle/wrapper/gradle-wrapper.jar`. Generate it once before using `./gradlew`:

```bash
cd android
gradle wrapper --gradle-version 8.9   # requires a local Gradle install (brew install gradle)
```

Or simply **open the `android/` folder in Android Studio**, which provisions the wrapper automatically on first sync. After that, `./gradlew` works normally.

## Open in Android Studio

1. Install [Android Studio](https://developer.android.com/studio) (Ladybug or newer recommended) with the Android SDK (API 36).
2. **File → Open** and select this `android/` directory (not the monorepo root).
3. Let Gradle sync finish. If prompted, use the bundled JDK 17+.
4. Pick a device/emulator and run the **app** configuration (`debug` build type).

Debug builds talk to `http://10.0.2.2:8080` (Android emulator → host machine). Release builds use `https://www.mybetrecord.com`.

## Build from the command line

```bash
cd android

# Unit tests (includes token refresh repository tests)
./gradlew testDebugUnitTest

# Debug APK
./gradlew assembleDebug

# Release App Bundle (AAB) for Play Console upload
./gradlew bundleRelease
```

Outputs:

- Debug APK: `app/build/outputs/apk/debug/`
- Release AAB: `app/build/outputs/bundle/release/app-release.aab`

### Signing a release AAB

Create a keystore outside the repo, then either:

**Option A — `keystore.properties` (local, gitignored pattern):**

```properties
storeFile=/absolute/path/to/mybetrecord-upload.jks
storePassword=...
keyAlias=upload
keyPassword=...
```

Wire it into `app/build.gradle.kts` `signingConfigs` before shipping, or sign via Android Studio (**Build → Generate Signed Bundle / APK**).

**Option B — Android Studio wizard** (recommended for first upload): Build → Generate Signed Bundle → select/create upload key → build AAB.

Enable Play App Signing in Play Console and upload the AAB to internal/closed testing first.

## Feature map

| Area | Notes |
|------|--------|
| Age gate | 18+ attestation on first launch |
| Auth | Login / register (`client: "android"`), refresh on 401, logout |
| Dashboard / Reports | `GET /reports/summary` |
| Bets | Full CRUD via `/bets`, Room cache for list |
| Settings | Profile from `/auth/me`, `PATCH /auth/settings`, plan status (read-only) |
| Account deletion | `DELETE /auth/account` with password + `DELETE` confirmation |
| Legal links | Privacy, terms, responsible gambling, web delete-account |

## Cleartext / network security

- Release: `usesCleartextTraffic=false`, HTTPS-only network security config
- Debug: cleartext allowed only for `10.0.2.2` / localhost via debug `network_security_config.xml`

## Play Data safety

See [docs/DATA_SAFETY.md](docs/DATA_SAFETY.md) for the declaration inventory.

## Local API

Point the emulator at a local stack (for example docker compose on port 8080). Production traffic always uses HTTPS to `www.mybetrecord.com`.
