# UNO WP-02 — Android SDK 35 GitHub Actions build evidence, R1

**Дата:** 2026-11-08. **Полномочия:** explicit owner approval 08.11.2026 for GitHub Actions when genuinely necessary, recorded in root `/AGENTS.md`. Это разовый адресный workflow для feature branch, а не право на release/main/обучение/секреты. **Статус:** `ANDROID_BUILT` for the *exact checked-out commit below*, `HOST_TESTED` for the listed test suites, `DEVICE_VERIFIED=FALSE`, `RELEASE_READY=FALSE`, `FOUNDATION_INCOMPLETE`.

## 1. Exact evidence, no extrapolation

- Repo: `ivankondral1998-dot/UNO-android-AI-Agent`, branch `feat/uno-foundation-hardening-20261107`.
- **Built Git SHA:** `de7d3e9c3e9634daa6ec20e7741d24546d088569`. This contains owner-approval root `AGENTS.md` plus `.github/workflows/uno-feature-android-verify.yml`. Future documentation-only commits do not change this build SHA.
- **GitHub Actions run:** [#42488780925](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42488780925), `workflow_dispatch` available but **one path-filtered push** initiated this run; conclusion **SUCCESS**, attempt 1, all build/lint/test steps SUCCESS.
- **Private owner artifact ID:** `13620288108` ([download in private GitHub Actions](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42488780925/artifacts/13620288108)); 7 files: debug APK, APK badge/permissions/SHA/provenance, host preflight log, lint HTML. Expires on **2026-11-11** in GitHub Actions retention (3 days); the provided conversation attachment can persist independently.
- Artifact ZIP SHA-256: `5d0cb1cd1d5d35ef1fba89fb197a84a531d662f3a2e70eeedc7c741b06251424`. ZIP integrity checked by `unzip -t`.
- **Actual debug APK:** `android/app/build/outputs/apk/debug/app-debug.apk` inside artifact. Size **922,662 bytes**, SHA-256 **`2c5285ea277acc11a8925900a66013a0ad4585946e84c13ef8cb09e72365ed37`**, independently rehashed from downloaded artifact. ZIP integrity of APK checked. Package **`org.unovyra.uno.scaffold`**, versionName **`0.1.0-skeleton`**, versionCode 1; minSdk26, targetSdk35, compileSdk35.
- `aapt dump permissions` from the built APK lists **no manifest permission requests**. In particular INTERNET, RECORD_AUDIO, CAMERA absent. This does **not** prove every future offline dependency/SAF provider is local or all runtime behavior verified.
- Runner: Ubuntu 24.04, JDK17, Gradle 8.7 (repo has no wrapper), Android SDK platform35 and build tools 35.0.0, AGP8.6.1 and Kotlin Gradle plugin1.9.24 from source files.

## 2. Actual verification results

GitHub Actions shows **SUCCESS** on:
- `python3 scripts/static_contract_check.py` — PASS (restricted offline manifest, DenyAllAndroidPort and missing model remain fail closed).
- `python3 scripts/test_sqlite_outcome_schema.py` — **14/14 PASS**, host SQLite transactional schema, *not* Android SQLiteOpenHelper device test.
- `python3 scripts/test_lab_tools.py` — PASS, limited diagnostics semantics.
- `bash scripts/run_all_preflight.sh` — **`UNO_LAB_PREFLIGHT_SUCCESS`**, standalone `kotlinc` was present and did **not** fall back to skip. Host-log exact markers: `UNO_WP01_HOST_PASS=193` (full Kotlin core aggregate), `STATIC_PREFLIGHT_PASS`, `UNO_SQLITE_SCHEMA_HOST_PASS=14`, `UNO_OUTCOME_INSPECTOR_HOST_PASS=11`, `UNO_OWNER_CONSENT_HOST_PASS=31`, `UNO_DEVICE_CREDENTIAL_PLATFORM_HOST_PASS=11`.
- Gradle `:core:unoHostTests` — SUCCESS independently of the standalone host test.
- Gradle `:app:assembleDebug` — SUCCESS, current real Android SDK compile/build.
- Gradle `:app:lintDebug` — SUCCESS **with 7 WARNINGS**, **not 0**: 4 `SetTextI18n`/hardcoded TextView internationalization, 1 `OldTargetApi`, 1 `DataExtractionRules`, 1 `MissingApplicationIcon`. No lint build-blocking error. Warnings remain open UX/manifest quality tasks; no false blanket PASS.
- `aapt dump badging/permissions`, package assertion and SHA-256 metadata — SUCCESS.

The workflow uses `permissions: contents: read`, `persist-credentials: false`, has **no secret inputs** and does not publish a release or push code; the private artifact is a debug installation candidate, not a commercial release.

## 3. Scope of the built APK and outstanding gates

The actual `UnoActivity` still wires `TrustController(DenyAllAndroidPort(), DenyAllLedger())` and `NoWeightsNeuralPort()`. New Android `SQLiteOpenHelper` outcome storage is inspect-only from owner-tapped diagnostic UI; the local credential prompt is **NOOP (verb2) only**. **No legitimate external Android action**, neural model, trained weights or readback of actual OS effects has been integrated. Controller write/readback semantics from Astra/R5.3 are still conditional on `A_cap/A_tx/A_fs`; this CI run did not establish those assumptions.

**Still untested (do not claim `DEVICE_VERIFIED`):** installation, launch, system device-credential prompt and callback lifecycle, background lock/STOP, SQLite WAL crash/restart/power-cut on Samsung Galaxy A52 Android 14, same-key APK upgrade signatures across other builds, measured RAM/PSS/thermal/battery and actual offline behavior. Host tests and successful APK compilation cannot replace device trials.

**Preserved evidence and source guidance:** `docs/implementation/2026-11-08_WP02_OWNER_CONSENT_SECURITY_ERRATUM_R2.md` (three independently reproduced and fixed reference credential bugs), original Astra R5.3 in `docs/precode/r5.3/`, Grok B2 audit in `docs/audits/2026-11-07/` with MATH-C01 FAIL/MATH-C05 BLOCKER, and read-only Jarvis V21 AndroidOperationAuthority/ConfirmationTicketGate as architecture test-oracle, **not** a new model or direct dependency. No changes to Jarvis, Neural Language, UNO model weights or `main`.

**Next physical gate:** install this **exact** APK on Samsung Galaxy A52/Android14, explicitly test the existing diagnostic owner-flow, owner STOP, SQLite inspection (empty/local) and record raw app+OS logs without privacy leaks. Only after that validate independent app-private effect `CREATE_LOCAL_NOTE` and readback under owner consent and recovery. The catalog is not restricted to one action in product architecture; one action is an integration acceptance fixture.
