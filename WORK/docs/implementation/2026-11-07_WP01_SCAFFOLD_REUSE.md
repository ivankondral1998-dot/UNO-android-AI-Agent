# WP-01 — reuse of earlier UNO B2 scaffold, 2026-11-07

**Current authoritative rules:** root `/AGENTS.md` in repository. This document is implementation provenance, not a new normative rule.

## Source discovery and attribution

The requested “Grok skeleton” has **two distinct historical items**:

1. Grok's `UNO_UNOVYRA_FRAMEWORK_R3_ASTRA_COMPATIBLE.md` (dated 2026-11-03) is a pre-code mathematical/framework document, owner sign-off not recorded. Its original source has been described in earlier dialogue; the exact R3 artifact was not separately byte-verified in this session.
2. The **runnable B2 scaffold 0.1.0** was located in the saved `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip` under `06_NON_NORMATIVE_OLD_SCAFFOLD/`. It has Python reference math, Kotlin core and minimal Android UI. The packaged scaffold is historical Work output; do not attribute its Android implementation solely to Grok without direct source provenance.

At this checkpoint all 67 old-scaffold source files compared byte-for-byte against the extracted local source; 0 mismatches. Original ZIP SHA-256: `4f9f59123b40a47a4bc2783f3633f0314a69fbac8c7cdb638dad3b3a1efc59b1`.

## Reuse decision and limitations

- Reused `:core` contracts/controller/memory/scheduler and `:app` isolated-service stub/manifest as a **historical scaffold**, not final production authority. No old material was edited in its historical archive.
- Added `ProbeMath.kt`, host tests, Android read-only device telemetry and bounded CPU probe, offline status/STOP UI and diagnostic app-private JSON recording in a new path `android/`.
- The old `TrustController.dispatch()` has a check-to-dispatch TOCTOU gap; the old scheduler can poll stale work after STOP. **Do not wire privileged Android effect dispatch to either until WP-02 corrections and device tests.** In WP-01 `DenyAllAndroidPort` and `DenyAllLedger` intentionally prohibit all effects. Model port is `NoWeightsNeuralPort` and worker service is an unconnected placeholder.
- Original `organism/src/main/kotlin/uno/core/ControlEvents.kt` remains unchanged. Duplicate historical event queue abstractions are *not integrated* and must be reconciled before WP-02; do not instantiate a second cognitive controller.
- This is **not a trained UNO 1.0, not Android-built, not device-verified**.

## Tests actually executed

- Unmodified archived scaffold: Kotlin JVM 10/10 PASS, Python 61/61 PASS (local replay, no weight training).
- New Android foundation core + probe statistics: Kotlin JVM 15/15 PASS, static AndroidManifest scan 0 `uses-permission`; isolated placeholder `true`.
- The new `app` code has **not** been built with Android SDK or tested on Samsung A52. `Gradle` and Android SDK are missing from execution environment.

## Site

Owner-reported public research site: https://uno-research.pages.dev/ . It is **not a UNO inference server**, not a connected product endpoint; it is only displayed as plain text inside the diagnostic UI. Direct web fetch from this environment failed (cache miss/DNS unavailable), so website live content was not independently checked. Its release/publication policy remains an owner decision.

## Next gates

1. Obtain a provisioned Android build environment, compile `:app` and record APK checksum and build logs. **No GitHub Actions.**
2. Install APK on A52/Android14 and obtain app-private probe JSON plus raw battery/CPU/memory/lifecycle logs.
3. Work on WP-02: native authority / atomic STOP / explicit action registry / readback, under tests. Do not enable actions in this WP-01 scaffold.
4. Separately implement UNO Core F and training preparation under WP-03/WP-04, with no unauthorized training.
