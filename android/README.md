# mybetrecord Android

Native Kotlin / Jetpack Compose client for [mybetrecord](https://www.mybetrecord.com).

- **Package / applicationId:** `com.mybetrecord.android`
- **minSdk 26 · targetSdk 36 · compileSdk 36**
- **Stack:** Compose Material 3, Hilt, Retrofit, OkHttp, Kotlin Serialization, Navigation, Room, EncryptedSharedPreferences

This app is a private betting ledger. It does **not** accept wagers, sell subscriptions, or include Stripe/checkout/upgrade CTAs.

## Localization

The app bundles the same locale catalogs the web frontend serves, so both clients translate in lockstep (~100 languages). `app/src/main/assets/locales/*.json` are copies of `frontend/public/app/locales/*.json` with the web-only namespaces (`home`, `blog`, `admin`, `plan`, …) stripped to keep the APK small. When web translations change, re-copy and re-strip them:

```bash
cp frontend/public/app/locales/*.json android/app/src/main/assets/locales/
python - <<'EOF'
import json, glob, os
KEEP = {"meta","common","i18n","auth","nav","ticker","bets","share","promoStats","publicProfile","outcomes","form","reports","settings","errors"}
for path in glob.glob('android/app/src/main/assets/locales/*.json'):
    if os.path.basename(path) == 'languages.json':
        continue
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({k: v for k, v in d.items() if k in KEEP}, f, ensure_ascii=False, separators=(',', ':'))
EOF
```

Strings resolve at runtime via `com.mybetrecord.android.i18n.I18n` (dotted keys, English fallback). The language is chosen from the account's `preferred_locale`, falling back to the device language, and can be changed in Settings. A handful of Android-only strings live in `I18n.androidExtras` (English only).

## First-time setup: Gradle wrapper JAR

The Gradle wrapper (`gradlew` / `gradlew.bat` and `gradle/wrapper/gradle-wrapper.jar`) is committed. From `android/`, use `./gradlew` on macOS/Linux or `.\gradlew.bat` in Windows PowerShell.

If the wrapper JAR is missing locally, regenerate it once:

```bash
cd android
gradle wrapper --gradle-version 8.11.1   # requires a local Gradle install
```

Or simply **open the `android/` folder in Android Studio**, which syncs the project automatically.

## Open in Android Studio

1. Install [Android Studio](https://developer.android.com/studio) (Ladybug or newer recommended) with the Android SDK (API 36).
2. **File → Open** and select this `android/` directory (not the monorepo root).
3. Let Gradle sync finish. If prompted, use the bundled JDK 17+.
4. Pick a device/emulator and run the **app** configuration (`debug` build type).

Debug builds talk to `http://10.0.2.2:8080` (Android emulator → host machine). Release builds use `https://www.mybetrecord.com`.

## Build from the command line

**macOS / Linux (bash/zsh):**

```bash
cd android

# Unit tests (includes token refresh repository tests)
./gradlew testDebugUnitTest

# Debug APK
./gradlew assembleDebug

# Release App Bundle (AAB) for Play Console upload
./gradlew bundleRelease
```

**Windows (PowerShell):** use the `.bat` wrapper from the `android` folder. `./gradlew` is a Unix script and will fail in PowerShell.

Gradle needs **JDK 17+**. If you see `JAVA_HOME is not set`, point it at Android Studio’s bundled JBR for the current session:

```powershell
# Find the JBR (pick the path that exists on your machine)
Get-ChildItem "C:\Program Files\Android\Android Studio\jbr" -ErrorAction SilentlyContinue
Get-ChildItem "$env:LOCALAPPDATA\Programs\Android Studio\jbr" -ErrorAction SilentlyContinue

$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"   # adjust if needed
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
java -version   # should show 17+

cd android
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
.\gradlew.bat bundleRelease
```

To set it permanently: Windows Settings → System → About → Advanced system settings → Environment Variables → New User variable `JAVA_HOME` = the `jbr` folder path (not the `bin` subfolder).

If PowerShell blocks the script, run: `Set-ExecutionPolicy -Scope Process Bypass` then retry, or call `cmd /c gradlew.bat assembleDebug`.

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
