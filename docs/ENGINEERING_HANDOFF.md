# UNO 1.0 — ЕДИНАЯ ИНЖЕНЕРНАЯ КАРТА / HANDOFF ДЛЯ GROK И ЛЮБОГО НОВОГО АГЕНТА


## UPDATE 2026-11-11 — PERMANENT SINGLE APK CHANNEL ON FULL FOUNDATION

**CHECKPOINT:** Branch `feat/uno-permanent-full-foundation-20261111` @ `59a89c3d` (base `e62a989e5f7f94167dcc798cf5973d6ba93c1875`).

**WHAT IS FIXED:**
- Full existing product code preserved (encrypted exact memory, manual facts, experimental offline chat, unified diagnostics, STOP, foundation reference cycle, R5.3 math package).
- Permanent channel added: `android/app/build.gradle.kts` accepts `org.unovyra.uno` as stable applicationId (no mandatory CI suffix).
- `android/scripts/owner_permanent_channel.py` + tests: local-only creation of one permanent PKCS12 key + signed builds with strictly increasing versionCode for the same package.
- Decision recorded in `docs/decisions/2026-11-11_OWNER_SINGLE_APK_CHANNEL_R1.md`.

**STATUS:**
- `ANDROID_BUILT` for permanent channel: FALSE (requires owner's local keystore + SDK).
- `DEVICE_VERIFIED`: FALSE.
- First install of `org.unovyra.uno` is a clean install; prior `.ci*` packages remain side-by-side until owner removes them.
- `main` untouched. No new test packages created. No weights training. No Actions run for signing.

**NEXT:** Owner creates the permanent key locally and builds the first `org.unovyra.uno` APK from this branch. Subsequent builds update it. Product work continues on this base.

---


## UPDATE 2026-11-10 — ONE INSTALLED UNO UPDATE CHANNEL / R4

**REAL LIMIT:** Every prior `.ci<RUN_ID>` APK has a distinct applicationId, and historic debug signing certificates are not accompanied by matching private keys in the UNO repo. **No safe data-preserving update APK can be claimed from an arbitrary CI artifact.** Do not offer the owner additional CI side-by-side icons, auto-uninstall or reset app data.

**IMPLEMENTED:** `android/scripts/owner_update_build.py` and explicit local-only Gradle `unoOwnerUpdateApplicationId/unoOwnerUpdateVersionCode` mode. Requires exact prior baseline APK, same locally held signing keystore, strictly greater versionCode and aapt/apksigner verification before producing a **non-overwriting** versioned APK+JSON. Keystore and passwords never enter repository, Actions or command-line values; GitHub Actions refuses owner signing. The code **does not install** anything. [Full source, old WP04 public signer SHA, constraints](implementation/2026-11-10_OWNER_UPDATE_CHANNEL_R1.md).

**CORRECTED CI VERIFIED:** [run #42808900944](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42808900944), built source `e3a1f80e1e93d385066703adf05356a888237fc3` SUCCESS: **14/14** owner-update host mock regressions, **313** Kotlin host assertions, static/negative suites, Android SDK35 build, lint and APK gates PASS. CI-only APK `org.unovyra.uno.scaffold.ci42808900944` SHA-256 `a2000e575b21ad4fda888d93de809fdafd1be9fa7eb592227da43762ec1c3a31`, **NOT an owner-installable update**. Earlier [#42808670634](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42808670634) **FAIL** from an incorrect public-alias test assertion; fixed, not erased. `OWNER_SIGNED_UPDATE_BUILT=FALSE`, `DEVICE_VERIFIED=FALSE`. This CI build does not exercise an actual owner's private signing key.

**NEXT GATE:** independently confirm which package/APK is **currently installed** on A52, then locate **the same signing private key**, or explicitly decide on first-time migration with preservation/export and no implicit removal. Until then, no compatible APK can be delivered. One unified Self-Test and one report remain the owner UX; original UNO 1.0 intelligence, memory, Android actions and native readback remain separate unclosed product gates.

---
