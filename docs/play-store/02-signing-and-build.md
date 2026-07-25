# Signing & release build

## 1. Generate an upload key (once)
Create a keystore **outside** the repo:

```bash
keytool -genkeypair -v \
  -keystore ~/keys/mybetrecord-upload.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias upload
```

- Validity must end after **22 Oct 2033** (10000 days satisfies this).
- Back up the keystore + passwords in a password manager / secure vault.
- **Never** commit the keystore, `keystore.properties`, or passwords to Git.

## 2. Wire signing into Gradle (local/CI only)
Create `android/keystore.properties` (gitignored):

```properties
storeFile=/Users/you/keys/mybetrecord-upload.jks
storePassword=...
keyAlias=upload
keyPassword=...
```

Reference it from `app/build.gradle.kts` `signingConfigs.release`, or use Android Studio's **Generate Signed Bundle** wizard for the first upload.

## 3. Build the AAB

```bash
cd android
# macOS/Linux:
./gradlew testDebugUnitTest      # must pass
./gradlew bundleRelease          # -> app/build/outputs/bundle/release/app-release.aab

# Windows PowerShell:
.\gradlew.bat testDebugUnitTest
.\gradlew.bat bundleRelease
```

## 4. Play App Signing
- Upload the AAB; Play App Signing manages the distribution key.
- Keep the R8/ProGuard `mapping.txt` for each release (deobfuscated crash reports).

## CI signing (later)
- Store the base64 keystore + passwords in the CI secret manager (never in the repo).
- Decode at build time; upload via the Play Developer Publishing API or `gradle-play-publisher`.

## Versioning
- Bump `versionCode` (integer) on every upload; keep `versionName` human-readable (e.g. `1.0.1`).
