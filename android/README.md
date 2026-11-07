# UNO 1.0 Android Foundation — WP-01, source only

Derived from preserved November 3 `UNO B2 Scaffold 0.1.0` as research implementation, not a release-ready brain. Original 67 files matched `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip` by exact bytes before copying; this directory is a new work tree. Root `AGENTS.md` is the only operative rules file.

Components:
- `:core`: previous Kotlin contracts, bounded scheduler, in-memory research memory/controller, and **new `ProbeMath` + host tests**. Previous trust/controller is NOT a production-safe Android dispatch implementation. The app uses deny-all ports only.
- `:app`: minimal Android shell; explicit STOP; read-only battery, memory/PSS, thermal, OS and CPU workload measurements, saved app-private `files/diagnostics/probe_latest.json`. No network request or model inference. Empty real action catalog. No advertised intelligence.
- Isolated neural service is still a placeholder with no Binder. Fully offline trained neural runtime is NOT integrated.

Build requirements, not fulfilled here: JDK17, Android SDK platform35/build-tools35, Gradle8.7+ with Google AGP8.6.1 and Kotlin1.9.24 available in the environment. Run `gradle :app:assembleDebug`. Do NOT run GitHub Actions. APK only valid after an actual build succeeds.

Host checks (requires `kotlinc` + Java): `bash scripts/host_verify.sh` (15 checks total). These do not compile the Android portion or prove actual hardware behavior.

After install on Samsung A52 Android14: open app, inspect device record, run CPU sample, use `adb shell run-as org.unovyra.uno.scaffold cat files/diagnostics/probe_latest.json` for debug app JSON; capture device/build identity, logs, and battery/thermal traces separately. Only then `DEVICE_VERIFIED` may be claimed.

Limitations: naive matmul is diagnostic only, not a calibrated NN-performance benchmark; PSS reflects this process, not whole future organism. No energy Joule measurement. Strict offline use requires checking OS integrations/SAF when later enabled. Site `https://uno-research.pages.dev/` was supplied by owner and is merely displayed as text; live availability was not independently confirmed in this environment.
