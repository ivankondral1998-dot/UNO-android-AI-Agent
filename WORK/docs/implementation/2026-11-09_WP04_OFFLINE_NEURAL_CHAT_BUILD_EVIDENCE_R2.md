# UNO WP-04 — pinned offline neural chat: BUILD EVIDENCE R2 · 2026-11-09

## Exact source, scope
- Repository: `ivankondral1998-dot/UNO-android-AI-Agent`, feature `feat/uno-foundation-hardening-20261107`.
- Git code SHA built: `7990bc8af5cc58a6c195d42c957be6dc0e75f412`, parent `587e57ef24a87925a81f3d581be79f19a934b24e`.
- Pin: upstream llama.cpp `a4d4f2fd4ec85ec6a0a9ece4870416c1b6cc24f5`, MIT, submodule `android/third_party/llama.cpp`. No weights bundled, no forced model selection.
- Chat source: `UnoChatActivity.kt`, `UnoNativeEngine.kt`, `UnoChatHistoryStore.kt`, `app/src/main/cpp/uno_llama.cpp`, `core/UnoPromptWindow.kt`.
- Local SAF sources are restricted to allowlisted Android provider authorities; no INET permission, but real network independence and Huawei picker behavior have NOT been exercised.
- Inference is CPU-only, not in isolated process. This is NOT a trusted Android production inference boundary; Android NativePort/dispatch remains deny-all.

## Reproducible build
- [Actions run #42670625565](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42670625565) `SUCCESS` for exact `7990bc8...`.
- Host `run_all_preflight.sh`: success, core harness `UNO_WP01_HOST_PASS=203` including `UNO_CHAT_WINDOW_HOST_PASS=10`. `gradle :core:unoHostTests`: successful. `:app:assembleDebug` and `:app:lintDebug`: successful. Security fixture 4 new negative tests passed.
- Aapt: `org.unovyra.uno.scaffold.ci42670625565`, launcher `UNO TEST · ci42670625565`, minSdk26 targetSdk35. No INTERNET / RECORD_AUDIO / CAMERA.
- Artifact GitHub `13698867287`, `uno-side-by-side-debug-10`. Private Actions archive, retention 3 days.
- APK size `7910771` B; SHA-256 `af331736d568a14a1b8b9e05e1ce5ccfee626cd847a67780da5eba7801fcf6b5`.
- Independent download and ZIP test yielded complete archive and APK ZIP. `readelf` on extracted arm64-v8a native lib lists all 5 required JNI entrypoints and correct shared dependencies.

## FAIL, preserved
- [Actions run #42670096975](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42670096975) failed at `STATIC_PREFLIGHT_FAIL / unexpected_activity_catalog`, before building. Cause: new internal Activity not yet in fail-closed manifest allowlist. Code-only guard correction + 4 negative tests in next source commit `7990bc8`. Original failed run preserved.

## Important unproven claims
- **Not yet device verified**: no model imported into UNO on either Huawei or Samsung; no offline answer, token timing, RAM, heat, lifecycle or interruption data for this code.
- Qwen3 GGUF and `llama_chat_apply_template` compatibility not confirmed by real inference; failure is reported, not replaced with fabricated answer.
- No semantic memory, encryption, isolated neural worker, training, real Android actions/permissions/readback. Owner identity and earlier sandbox WP03 do not grant those capabilities.
- Commercial product, release signing and distribution remain unapproved.
- Documentation-only follow-up commit may advance branch HEAD; always attribute APK evidence to the **exact built SHA**, not a later docs HEAD.

## Device acceptance after owner installs test APK
1. Use Huawei nova 10 SE (API31 / 8GB) first; load known local Qwen3-0.6B Q4_K_M GGUF through `Выбрать GGUF` from system Downloads/Documents local provider. The file already in PocketPal's private sandbox cannot automatically be reused.
2. Open `UNO TEST · ci42670625565` → `ОТКРЫТЬ ЭКСПЕРИМЕНТАЛЬНЫЙ ОФЛАЙН-ЧАТ UNO`. Confirm app reports GGUF loaded, send one short Russian question, record answer and reported TTFT/token throughput, check STOP response. The first test should not require additional STRESS runs.
3. Turn off Wi-Fi/mobile; repeat a single short prompt to verify no network requirement. If file picker rejects a vendor provider, preserve error/status; do not broaden provider allowlist silently.
4. Repeat on Samsung A52 only after Huawei data warrants it, keeping separate APK package/data. No prior installed test packages deleted.

**State:** `IMPLEMENTED + HOST_TESTED + ANDROID_BUILT`, `DEVICE_VERIFIED_WP04=FALSE`, `RELEASE_READY=FALSE`.

Original R1 contract remains [unchanged](2026-11-09_WP04_OFFLINE_NEURAL_CHAT_EXPERIMENT_R1.md). Source and CI evidence supersede its prebuild status, not its stated limitations.
