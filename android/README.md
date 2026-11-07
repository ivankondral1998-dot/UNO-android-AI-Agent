> **АКТУАЛЬНЫЙ КОНТЕКСТ ДЛЯ GROK / НОВОГО РАЗРАБОТЧИКА:** [инженерная карта UNO 1.0](../docs/ENGINEERING_HANDOFF.md) + [правила](../AGENTS.md). Этот README описывает исторические WP-01 этапы; после hardening новый APK ещё не собран и не испытан на A52. Не путать старый CI APK с текущим кодом.

# UNO 1.0 Android Foundation — WP-01, debug APK Android-built (2026-11-07)

Derived from preserved November 3 `UNO B2 Scaffold 0.1.0` as research implementation, not a release-ready brain. Original 67 files matched `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip` by exact bytes before copying; this directory is a new work tree. Root `AGENTS.md` is the only operative rules file.

Components:
- `:core`: previous Kotlin contracts, bounded scheduler, in-memory research memory/controller, and **new `ProbeMath` + host tests**. Previous trust/controller is NOT a production-safe Android dispatch implementation. The app uses deny-all ports only.
- `:app`: minimal Android shell; explicit STOP; read-only battery, memory/PSS, thermal, OS and CPU workload measurements, saved app-private `files/diagnostics/probe_latest.json`. No network request or model inference. Empty real action catalog. No advertised intelligence.
- Isolated neural service is still a placeholder with no Binder. Fully offline trained neural runtime is NOT integrated.

CI-verified build requirements on 2026-11-07: JDK17, Android SDK platform35/build-tools35, Gradle8.7+ with Google AGP8.6.1 and Kotlin1.9.24 available in the environment. Run `gradle :app:assembleDebug`. Owner explicitly authorized this single GitHub Actions build; subsequent Actions executions need specific authorization. APK is real, signed with temporary CI debug key.

Host checks (requires `kotlinc` + Java): `bash scripts/host_verify.sh` (100 checks in current suite). These do not compile the Android portion or prove actual hardware behavior.

After install on Samsung A52 Android14: open app, inspect device record, run CPU sample, use `adb shell run-as org.unovyra.uno.scaffold cat files/diagnostics/probe_latest.json` for debug app JSON; capture device/build identity, logs, and battery/thermal traces separately. Only then `DEVICE_VERIFIED` may be claimed.

Limitations: naive matmul is diagnostic only, not a calibrated NN-performance benchmark; PSS reflects this process, not whole future organism. No energy Joule measurement. Strict offline use requires checking OS integrations/SAF when later enabled. Site `https://uno-research.pages.dev/` was supplied by owner and is merely displayed as text; live availability was not independently confirmed in this environment.

## Offline Diagnostic Laboratory v2 — 2026-11-07 (WP-01 continuing)

The foundational Android app now includes a manually activated read-only sandbox laboratory. No model weights, native action dispatch, root, Accessibility, network, SAF, audio, camera or permissions are enabled. The service remains an isolated placeholder. **Do not mistake diagnostic PASS for finished UNO intelligence.**

- `LabSystemMetrics.kt`: battery current/charge/temperature/voltage (when the OEM reports them), thermal status/headroom, PSS/RSS, native/Java heap, GC, uptime, CPU usage, readable CPU clocks.
- `DeviceLab.kt`: bounded, cancellable QUICK/STRESS scenarios and JSON reports saved in app-private storage. App-owned storage integrity fixture only; no deletion of user files.
- `SensorLab.kt`: foreground-only, bounded event timestamps for ordinary motion/environment sensors, explicit missing/unsupported. No physical accuracy claims.
- `core/LabProtocol.kt` and `Measurement.kt`: executable host workloads, percentiles, STOP/queue stress, corruption detection, semantic evidence verdicts. Unavailable metrics are null or UNSUPPORTED, never silently zero.
- `scripts/run_all_preflight.sh`: JVM, static manifest and Python test suite; no SDK required.
- `scripts/adb_collect.py`: offline evidence capture from **this debug package only**, outputs checksummed raw ADB files. `--restart-uno` is an opt-in force-stop/restart of **UNO only**.
- `scripts/validate_lab.py`, `scripts/compare_lab.py`: validate report semantics and compare two profiles without declaring statistical significance.
- [Full Russian protocol](LAB_PROTOCOL_RU.md): what is measured, interpretations, STOP/thermal limits, A52 procedure, unsupported/future tests.

The Android debug APK was **built** successfully by [GitHub Actions run 42391092683](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42391092683); SHA-256 `fb49afa67cbb4cc3591d72728da5ae8b649e5560e6d3c754b65ad58c610a728f`. It has **not** been installed or tested on A52. Host tests do not validate Android APIs. There is no physical-energy Joule instrument; `BatteryManager` counters may be unavailable and are not a calibrated Watt-meter. There is no auto-upload or remote dependency.

## UI-01: themes and later model-driven personalization

UI uses orange by default; manual local choices: orange, yellow, rose (rose/cyan preset incomplete), light orange. Only UI theme token and opt-in flag are persisted in app-private `SharedPreferences`. STOP stays red. `UnoThemeGate` in `:core` accepts a future neural proposal **only on explicit user request** and applies it **only after owner confirmation**; interaction-style input requires separate opt-in, default OFF. The current APP has **no model**, so its "Ask UNO for a theme" button reports unavailable instead of faking intelligence. See `docs/implementation/2026-11-07_UI_THEME_PERSONALIZATION_FOUNDATION.md`. Host coverage is `UNO_WP01_HOST_PASS=100`; Android build/device remains unverified.

## WP-01 hardening follow-up — compute admission, 2026-11-07

The Grok/Work B2 Python reference contains a reproduced multi-resource-budget gap: a TEXT tick completed with a positive MAC allowance but zero bytes/tokens/time allowance. **This is not fixed in the preserved historical Python reference.**

A new Kotlin-only `ComputeBudgetGate` is available in `:core` as a **fail-closed pre-admission primitive** (MAC, tokens, peak concurrent scratch bytes, monotonic deadline and STOP). Its 17 host negative tests passed, including 10 repeated runs and an 8-thread contention check. It is registered in the standard host runner but the **full runner has not been executed on this updated branch**, and no Android APK was built for the update. The gate is **not wired to a trained neural model or Android effects**. For exact source attribution, limitations and pending gates see `docs/implementation/2026-11-07_COMPUTE_BUDGET_CONTRACT_R1.md` and `docs/audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md`. Do not treat arithmetic/host PASS as mobile resource or inference proof.
