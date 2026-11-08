# UNO Android UI — diagnostic report copy + unambiguous test APK identity (2026-11-08, R1)

## Trigger and diagnosis

The owner installed the side-by-side UNO debug APK and showed a screen where the themes were followed immediately by RAM/CPU measurement buttons; **SQLite, credential NOOP and report-copy controls were absent**. The live `UnoActivity.kt` from `feat/uno-foundation-hardening-20261107` already placed SQLite and owner credential controls between theme selection and RAM/CPU. The previous and newer side-by-side apps both displayed the same **UNOVYRA UNO · Scaffold** label. Therefore the **best explanation** is that the older app was opened instead of the new app. That is an inference based on source and screenshot, **not** measured Android package identity; no app PID/package logs from the owner's A52 were received.

Separately, the app did not provide any manual **copy full diagnostic JSON** control, and the on-screen preview was capped at 14,000 characters; that missing UX is confirmed by code.

## Changes in feature branch

- `UnoActivity.kt`: shows `УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName` above tests; adds a clearly marked `📋 СКОПИРОВАТЬ ВЕСЬ ПОСЛЕДНИЙ ОТЧЁТ` manual button near diagnostic tests. Successful test results keep an untruncated JSON string with package and app-private output path for `ClipboardManager` / `ClipData.newPlainText`, independent of the 14k UI preview. Explicit failure and missing-result messages; invalidate previous clipboard candidate when a new test starts. Clipboard export is *user-initiated*, not automatic; the UI warns that other applications may see clipboard contents. It does not grant Android native action authority, use network or export files to SAF.
- `android/app/build.gradle.kts`: ordinary package IDs unchanged. When passed the preexisting isolated CI suffix, debug builds receive an additional **visible launcher label** `UNO TEST · ci<GITHUB_RUN_ID>` via a versioned resource. This avoids ambiguous identical launcher titles, while a fresh per-run app package avoids debug signing key collisions.
- `AndroidManifest.xml`: app label now points to `@string/uno_app_label` supplied by Gradle `resValue`, not inline literal or unresolved placeholder.
- `android/scripts/static_contract_check.py` and `test_static_contract_check.py`: positive presence guards for SQLite/credential buttons, clipboard code and visible package ID, plus negative regressions and updated clean synthetic fixture. This static check **is not UI instrumentation**.
- CI `.github/workflows/uno-feature-android-verify.yml` now runs the static test explicitly and verifies **both** unique package ID and resolved launcher label from `aapt dump badging`. No signing secrets or public release introduced.

Original `AGENTS.md` rules still apply, notably the owner-approved necessity condition for GitHub Actions, no `main` merge, no weight training, no automatic system effects, no legacy Jarvis OwnerGate/weights. `DenyAllAndroidPort` / `NoWeightsNeuralPort` remain intact.

## Test history, including failures

1. [Run 42504065211](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42504065211): **FAIL** because the clean fixture for the newly extended static guard lacked the new UI markers. Fixture and three negative regressions fixed without weakening guard.
2. [Run 42504217888](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42504217888): host + Gradle + SDK35 compile + lint **PASS**, but final `aapt` launcher-label check **FAIL** because the inline label appeared as empty in `APK_BADGING`. Changing label to a string resource was necessary. This intermediate APK was **not distributed**.
3. [Run 42504842750](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42504842750): **SUCCESS**, every CI step including source contract tests, full Kotlin preflight, Gradle core JVM, `:app:assembleDebug`, lint and APK label/package audit. Exact **built SHA `a1410895ef3fe2f748ba3f6e70cf8e45f70a022e`**.

### Verified build output

- Package **`org.unovyra.uno.scaffold.ci42504842750`** (verified from `aapt dump badging`).
- Launcher label **`UNO TEST · ci42504842750`** (verified `application-label:` in `aapt`).
- `app-debug.apk`, **924526 bytes**, **SHA-256 `cfb8f3de6df47a25e709563117f33d829f0445054a9919846d937e0d10a51f6a`** independently rehashed after private artifact download. Both artifact ZIP and inner APK ZIP integrity checks **PASS**.
- GitHub private artifact ID `13627416075`; ZIP size **937876 bytes**, SHA-256 `99fd6d28a7bace096dd541041bb7e36e7905c0e83a04553f6d7cbf23ae753b6e`.
- Verified owner-private Google Drive APK: https://drive.google.com/file/d/1YsPRCW5wL-_EYx2flCAdJN393kW6NEpf/view?usp=drivesdk ; metadata readback size 924526, MIME `application/vnd.android.package-archive`, `shared=false`.
- No file/user history deleted. Both legacy and new versions have different package IDs and own sandboxes. More fresh CI builds produce additional isolated apps; stable signing for upgrade channel remains a future requirement.

**Status:** `IMPLEMENTED`, `HOST_TESTED`, `ANDROID_BUILT`, **`DEVICE_VERIFIED=FALSE` for this new APK**, `RELEASE_READY=FALSE`, `FOUNDATION_INCOMPLETE`. An APK's proper manifest label and successful Android build do not prove the owner has launched and tested it. The Android clipboard and SQLite/credential UI need real A52 verification. The historical Astra/R5.3, Grok, Jarvis, UNO-N0/FR/TR and model artifacts are untouched.

## Next on-device acceptance

Install the **new exact** APK (do not uninstall old apps). Launch app titled `UNO TEST · ci42504842750`; confirm the top header says `org.unovyra.uno.scaffold.ci42504842750`. From that app tap `Проверить SQLite (без создания базы)`; expected fresh side-by-side sandbox without main DB: `NOT_INITIALIZED`, not proof of prior app history. Press `📋 СКОПИРОВАТЬ ВЕСЬ ПОСЛЕДНИЙ ОТЧЁТ` and paste into ChatGPT. Then explicitly initialize fresh SQLite and test credential NOOP/STOP, keeping independent native effects disabled. Do not claim `DEVICE_VERIFIED` until actual results are supplied.
