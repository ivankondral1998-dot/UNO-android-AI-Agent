# UNO WP-02 — Android package conflict / side-by-side diagnostic APK, R1

Date: 2026-11-08. Active instructions: root `/AGENTS.md`. Repo: `ivankondral1998-dot/UNO-android-AI-Agent`, branch `feat/uno-foundation-hardening-20261107`.

## Observed failure and causal classification

Owner reported Android refusing installation with wording that a package conflicts with another installed package. **Fact:** install failed on the target device. **Hypothesis (not measured on device):** previous installed app with package `org.unovyra.uno.scaffold` had a signing certificate different from this GitHub Actions run's ephemeral debug keystore. Android will not update a package across incompatible certificates. We did **not** retrieve Samsung A52 `pm` or PackageInstaller error logs/certificates; exact error code remains `REQUIRES_DATA`.

Deleting the installed app would risk losing user data, and is unnecessary for the current diagnostic goal. No package, user data or legacy apps were removed.

## Implemented remediation

1. In `android/app/build.gradle.kts`, **only debug** accepts explicit `-PunoIsolatedDebugSuffix=ci<run_id>` with a restrictive regex. Without the flag the original `applicationId` remains unchanged. `release` stays `org.unovyra.uno.scaffold`; no production package migration or signing change.
2. In feature-branch `.github/workflows/uno-feature-android-verify.yml`, owner-approved GitHub Actions now passes `ci${GITHUB_RUN_ID}` to debug assemble and lint. The `aapt dump badging` gate rejects any artifact whose package ID differs from the expected **run-unique** identity. This avoids overwriting an existing application and avoids recurring temporary debug-signing conflicts across separate GitHub runs. It does **not** make debug certificates persistent or enable future in-place updates.
3. `UnoActivity.kt` ADB export hint shows the *actual installed* `packageName`, not the historical fixed ID.

## Exact verified outputs

- **Built commit:** `0afa6cb9850faee68abea0e93be98794db41b930`.
- **GitHub Actions run:** [42493602248](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42493602248); **SUCCESS** including complete Kotlin host test, Android SDK35 build, lint and APK identity/permission validation.
- **Private Actions artifact:** ID `13622283092`, name `uno-side-by-side-debug-2`.
- **New `applicationId`, validated from actual APK `aapt dump badging`:** `org.unovyra.uno.scaffold.ci42493602248`.
- **APK:** `app-debug.apk`, 922678 bytes, SHA-256 `63b46afedb03641c189e7f9c71ede28b8e16b426878ab924952d16f69bc776c1`. The downloaded APK was independently rehashed and ZIP integrity checked locally (no damaged ZIP entries); manifest present.
- **Private Actions artifact ZIP:** 935804 bytes, SHA-256 `ecbb3587ab31eed77c7b075630e78737bf21afc4b7afa9da752f722a2e3383c9`, decompression integrity PASS.
- **User-accessible private Google Drive APK:** https://drive.google.com/file/d/1M_Pzo19E9eVDSwFo8OmHYMOrXJWIbjgP/view?usp=drivesdk ; Drive readback confirms `application/vnd.android.package-archive`, 922678 bytes, owner-only at verification time.
- Original failed-install APK had package `org.unovyra.uno.scaffold`; its source and Git SHA are preserved in `docs/implementation/2026-11-08_WP02_ANDROID_SDK35_CI_BUILD_R1.md`.

## Boundaries and next on-device acceptance

**`ANDROID_BUILT` = TRUE for exact new CI SHA**; **`DEVICE_VERIFIED` = FALSE** until Samsung A52 installation and checks. Different application ID avoids an **update signature conflict**, but **does not prove installability on-device** or correct runtime behavior. It intentionally creates **a separate Android sandbox**, so the diagnostic build cannot read or migrate old app-private history. Old app/data remain untouched. Each new CI run creates a separate test package; for a long-lived upgrade channel, a stable explicitly authorized signing key and fixed applicationId will be needed later. No keys committed or shared. This does not imply commercial-release approval.

Run exact Samsung installation; confirm a distinct new icon/package and compare with the old app; run STOP, SQLite inspection, Android credential NOOP, record OS logs if failure. Still `DenyAllAndroidPort`, no model weights, no Android native action catalog/readback; no changes to `main`, Jarvis, Neural Language or historical Astra/R5.3/Grok. GitHub Actions used under explicit owner permission for necessary SDK build only.
