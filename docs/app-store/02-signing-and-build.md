# App Store — signing, archive & upload

## 1. Version numbers
- [ ] Bump `MARKETING_VERSION` (user-facing, e.g. `1.0.0`) in `ios/project.yml`.
- [ ] Bump `CURRENT_PROJECT_VERSION` (build number, e.g. `1`) for each upload.
- [ ] Run `xcodegen generate` after editing `project.yml`.

## 2. Release build settings
- [ ] Scheme: **MyBetRecord** → **Release**.
- [ ] `API_BASE_URL` = `https://www.mybetrecord.com` (default in `project.yml`).
- [ ] No debug-only ATS exceptions in Release.

## 3. Archive
1. Connect a Mac with full Xcode installed.
2. **Product → Archive** (select **Any iOS Device** as destination).
3. When the Organizer opens, select the archive → **Distribute App**.
4. Choose **App Store Connect** → **Upload**.
5. Follow prompts (include symbols, manage signing automatically).

## 4. Command-line alternative

```bash
cd ios
xcodegen generate
xcodebuild -scheme MyBetRecord \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath build/MyBetRecord.xcarchive \
  archive
```

Upload via Xcode Organizer or `xcrun altool` / Transporter app.

## 5. Verify upload
- [ ] App Store Connect → **My Apps** → **mybetrecord** → **TestFlight** shows the new build (processing may take 10–30 minutes).

## Secrets
- Never commit distribution certificates, `.p12` files, or provisioning profiles with private keys to Git.
- Store App Store Connect API keys in a password manager or CI secret store only.
