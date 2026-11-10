# UNO — Jarvis V20 source cross-check / one-tap diagnostic R3 (2026-11-10)

## Exact sources (read-only Jarvis, active UNO feature branch)

- UNO: `feat/uno-foundation-hardening-20261107`, start-of-review HEAD `64b6a563276e0a7aa1d6474720647d13b2e02532`; authority `/AGENTS.md` V3 (RELEASE FIRST).
- Jarvis source: private `kolakbro5995-cpu/JarvisLab`, recovered snapshot `recovery/v20-original-baseline-3ab8dd9-20261031`, snapshot commit `b3c19fcae9000defd67efc7dd77d7876e4a3de22`, Git tree `e7c6d41e176395c1428b855b6624419bcbe581cc`. Access must use the **Jarvis owner account**, not the separate UNO GitHub connection.
- Jarvis V20 supplied APK: `JarvisLab-V20-Sol-Experiment-20261029.apk`, SHA-256 `984fc3f975e5cb38210e49c57bce6ea562f54f5f139e45e2569bd9fd27aeea07`. APK/source identity was not proven byte-for-byte; the recovered snapshot is a source reference, not an APK rebuild.
- **Important manifest identity mismatch (direct local binary-XML manifest read):** supplied Sol-Experiment APK has `package=io.jarvis.mobile.lab.experiment`, `versionCode=20`, `versionName=0.7.6-lab-experiment`; the recovered source `app/build.gradle.kts` declares `applicationId=io.jarvis.mobile.lab`, `versionCode=20`, `versionName=0.7.6-lab`. The submitted experimental APK cannot be treated as the canonical Lab in-place update or a proven byte-for-byte build of this source. `RuntimeDiagnostics.runUnifiedDetailed()` in recovered source has an exact `io.jarvis.mobile.lab` branch guard, so cognitive Self-Test in the `.experiment` APK is **not proven reachable** from this source alone. The canonical `verify_lab_update.sh` correctly restricts updates to `io.jarvis.mobile.lab`.

## Verified Jarvis implementation patterns

1. `app/src/main/java/io/jarvis/mobile/diagnostics/RuntimeDiagnostics.kt`, `runUnifiedDetailed()`: one report combines passive runtime state, bounded trace tails, live feature flags, read-only media/volume observations, deterministic STOP phrase probes, fixed-input INT8 model *diagnostics*, isolated cognitive scenarios and prior heavy-run summaries. Heavy stress and memory benchmarks **do not run** within Self-Test. Report is archived app-private and its contents can be copied.
2. `app/src/lab/java/io/jarvis/mobile/agent/runtime/cognitive/LabCognitiveDiagnostics.kt`, `runAll()`: bounded synthetic cognitive harness, hard no-Android-dispatch invariant. PASS here is not a real native-effect confirmation.
3. `app/src/main/java/io/jarvis/mobile/agent/AndroidOperationAuthority.kt` and `ConfirmationTicketGate.kt`: separate owner/permissions/STOP/context-bound, one-use operation gates. `TaskEvidenceLedger.kt` keeps distinct task outcomes; reported evidence is not automatically native readback.
4. `scripts/verify_lab_update.sh`: install-over-existing gate requires identical `io.jarvis.mobile.lab` package and signing certificate and increasing `versionCode`. This is directly relevant to UNO APK proliferation.

**UNO adaptation:** single existing owner-triggered QUICK diagnostic and JSON report; historical advanced tools remain collapsed. No Jarvis Local Brain weights, Android action dispatch, old cloud path or app tree transplanted. UNO still uses deny-all native authority and has no accepted neural agent model.

## Concrete R2 error reproduced and patched

`UnoActivity.runUnifiedSelfTest()` declares `NEURAL_DIALOGUE_QUALITY=NOT_TESTED` (correct: no model acceptance). But `UnoDiagnosticEvaluator.recognized` did not contain `NOT_TESTED`, so an ordinary report was forced to `FAIL` with `unrecognized=1`, even without actual failures.

Reproduced with a standalone Kotlin source-isolated harness: `ALL_NORMAL_DIAGNOSTIC_STATUS=FAIL, unrecognized=1`. Added `NOT_TESTED` to accepted **incomplete** statuses, while unknown tokens and actual FAIL still fail-closed, STOP still overrides. Added a dedicated Kotlin regression in `UnoDiagnosticSummaryTest.kt`. Local small-scope harness confirmed eight cases (7 existing semantics + new `NOT_TESTED` case). This is **not** a complete project-host or Android test claim.

## One installed UNO identity, no new icon per check

`UnoActivity.runUnifiedSelfTest()` now includes `INSTALLED_APK_IDENTITY`: it reads its own `application_id`, `version_code` and SHA-256 of the currently installed APK signing certificate(s) from Android PackageManager, API 26–35, without new permissions or new app. Exceptions are captured as FAIL, not substituted with fabricated identities. The report explicitly says `device_attested=false`: clipboard JSON is **not** remote cryptographic attestation.

This supplies an owner-accessible baseline for identifying the installed UNO app. It does **not** itself create a compatible replacement: the current workflow deliberately uses `org.unovyra.uno.scaffold.ci<run_id>`, versionCode=1 and an ordinary debug signer, so each CI artifact is **not** an in-place update. Never tell the owner to install the CI-suffixed artifact. Before any candidate installation use the existing `android/scripts/apk_update_gate.py` on the confirmed installed-baseline APK and candidate APK; signer identity and versionCode must match the update rules. Without a confirmed baseline and trusted stable signer, **UPDATE_READY=FALSE**.

## Verification boundaries / next gate

- **IMPLEMENTED (source):** Kotlin diagnostic status correction, regression, installed package fingerprint added to existing one-tap report; no new Activity, permission, service, model, or standalone APK installed.
- **HOST_TESTED_LOCAL:** targeted Kotlin evaluator harness (8 PASS); no full preflight yet for this change.
- **ANDROID_BUILT:** not yet, until exact-new-source SDK35 build succeeds.
- **DEVICE_VERIFIED:** FALSE, including PackageManager JSON on A52, STOP/report race, and local KeyStore.
- **PRODUCT:** one trained/accepted offline intelligence, real owner-bound Android action and independent native readback remain open. No release, merge to main, Jarvis copy, weight training, or destructive action was authorized by this work.


## R3 EXACT-SOURCE CI VERIFICATION (completed 2026-11-10, supersedes initial pending build)

- **CI exact source commit:** `cb87b7edd3e5d4f116a4e913a8b18a750be15f1a`; private GitHub Actions [run #42805696859](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42805696859), job `129794125073`: **SUCCESS**, every job step passed.
- **HOST_TESTED:** standalone Kotlin preflight and Gradle `:core:unoHostTests` PASS, final `UNO_WP01_HOST_PASS=313`. Log explicitly contains `PASS declared neural NOT_TESTED is incomplete, never an unknown failure`. Python safety/negative scripts passed (observed 40, 50 and 8-test suite summaries in logs). These are host checks, not device behavioral proof.
- **ANDROID_BUILT:** Gradle SDK35 `:app:assembleDebug` PASS; `:app:lintDebug` PASS; aapt package/manifest/permission and native `libuno_llama.so` gates PASS.
- **Exact APK SHA-256 (CI log):** `1f6df2427f217cd0285cab3da652573db986faefd48ec99012271aed9f24ed6c`. CI package `org.unovyra.uno.scaffold.ci42805696859`; **side-by-side test artifact, not owner-installable update**. Private artifact `uno-ci-only-not-owner-update-24`, ID `13757639247`; its archive digest is a different object from APK SHA.
- **DEVICE_VERIFIED=FALSE:** no installation, real Samsung A52, clipboard, installed signer readback, reboot, owner authority, native effect, independent OS readback or neural quality test was run. **RELEASE_READY=FALSE**. Do not distribute CI-suffixed APK as an update.
- After this verified code commit, a later **documentation-only** clarification identified the separately packaged Jarvis `.experiment` manifest; this documentation edit was not part of the exact build SHA and does not change app/runtime sources.
