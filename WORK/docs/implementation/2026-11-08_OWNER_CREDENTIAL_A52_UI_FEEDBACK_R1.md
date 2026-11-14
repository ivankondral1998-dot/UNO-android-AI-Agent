# UNO WP-02 — Owner credential on A52: invisible result UI defect, R1

**Date:** 2026-11-08. Repo feature branch `feat/uno-foundation-hardening-20261107`. Single authoritative root rules `/AGENTS.md`; owner allows necessary GitHub Actions, not release or privileged Android actions.

## Actual evidence and classification

The owner reports on Samsung Galaxy A52 Android14 with package `org.unovyra.uno.scaffold.ci42504842750`: **Android's system fingerprint confirmation interface appeared** after tapping `Проверить владельца через экран Android`. Upon tapping the one-use consent button, **"ничего вообще не произошло" visually**. No screenshot of the post-tap top status, `onActivityResult` code, or system callback logs have been supplied. Do **not** claim that system auth returned `RESULT_OK` or that one-time `consume()` was accepted/rejected. There was no attempted privileged native action; `DenyAllAndroidPort` remains wired.

**Proven UI defect from sources:** `UnoActivity.kt` previously updated only the `status: TextView` at the top of a long `ScrollView` for both `ownerGate.consume` and Android's `onActivityResult`. The owner buttons were near the bottom (visible in owner's screenshots). Therefore a tap could change text only off-screen, making the button appear inert. This is a reproducible structural/UI fault, not proof of a credential-state bug. See Android source blob before fix `889d42b70b79bc9d310c9bf872d4f586bec2bf2e`.

## Implemented narrow correction

- `UnoActivity.kt`: owner outcome label `ownerFeedback` added **immediately below** credential / one-use NOOP buttons, registered in existing theme/contrast label list. `showOwnerFeedback(message)` updates both the old global status and this local owner label. OS callback and each one-use click (accepted/denied) now display explicit local results; initial state also visible.
- No change to `OwnerConsentState.kt` or platform `KeyguardManager` logic. Prompt result still requires matching pending request code and one-use scope. A new UI label does not grant privileges, certify caller identity, or weaken STOP/revoke/TTL.
- `static_contract_check.py` now rejects source missing local feedback for button and OS callback. `test_static_contract_check.py` includes two negative regressions and updated clean fixture. Static source checks are not actual device instrumentation.
- Existing clipboard export and SQLite diagnostics were preserved.

## Verified outputs

- **GitHub Actions run** [42509757092](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42509757092) **SUCCESS** all steps, JDK17, Gradle8.7, real Android SDK35, standalone Kotlin host preflight (`UNO_WP01_HOST_PASS=193`, `UNO_OWNER_CONSENT_HOST_PASS=31`), independent Gradle core suite, `app:assembleDebug`, `app:lintDebug`, `aapt` identity/perms and debug artifact.
- **Exact built Git SHA:** `502088cadbbfec603bd52e8dc46be150afe3e41e`.
- **APK package:** `org.unovyra.uno.scaffold.ci42509757092`, launcher `UNO TEST · ci42509757092`, verified by `aapt dump badging`.
- **APK:** size `924794` bytes, SHA-256 `a26d12d94d690afb6f5176a5ad682e8bed2c1f6205e48377274999603d4b7f6c`; downloaded ZIP and APK entries integrity PASS, independently rehashed.
- GitHub private artifact id `13628942853`, ZIP SHA-256 `1ed1c70ecd301bbe5157796cdbd92965c8fb12be2e3e121b57a9a7f4124c9a4e`, private 3-day retention.
- Private owner Google Drive APK https://drive.google.com/file/d/13z9r0_195niHfEwo1QHi9jabp-fRlx6-/view?usp=drivesdk; Drive metadata readback `shared=false`, package MIME and size 924794 confirmed. It is direct APK not ZIP. Other test packages and their data are untouched.

## Proof boundaries and next physical verification

**HOST_TESTED=TRUE, ANDROID_BUILT=TRUE** on the exact built SHA, **DEVICE_VERIFIED_FOR_THIS_NEW_APK=FALSE**; prior A52 device lab+SQLite were observed on `ci42504842750`. Fingerprint screen appeared for old build, but **one-use acceptance remains `REQUIRES_DATA`**. No model weights, native dispatch, owner credential uniqueness proof or independent effect readback were tested. Do not claim success just because the OS presented a biometric UI. Static tests don't confirm local message placement on A52.

Recommended shortest user test without installing anything: in already installed `ci42504842750`, tap the one-use button and scroll back to top to read `status`. If using the new `ci42509757092` APK, label under the two owner buttons shows the result directly; test OS biometric then one-use twice (first conditional acceptance, second must deny). Avoid asking for repeated 60 s stress cycles.

Security note: `onPause` revokes `ready` state when backgrounded, and adapter requires `hasWindowFocus()` at consumption; some OS lifecycle ordering may create false negatives. This remains a **conditional concern** pending actual A52 callback/foreground observations, not a demonstrated bug. `OwnerConsentState` unchanged. No publishing, no main merge, no Jarvis/Grok/Astra/Neural Language modifications.
