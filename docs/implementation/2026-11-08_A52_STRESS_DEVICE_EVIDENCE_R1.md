# UNO WP-02 — Samsung A52 STRESS physical-device evidence R1

**Date:** 2026-11-08. **Status:** `DEVICE_VERIFIED` **only for the eight sandbox diagnostic scenarios recorded below**, based on the owner-provided on-device report; not independently replicated by a second operator, not whole UNO/owner/SQLite verification. `RELEASE_READY=FALSE`, `FOUNDATION_INCOMPLETE`.

## Provenance and scope

- **Source:** report text pasted by the owner from `UNO TEST · ci42504842750`, package `org.unovyra.uno.scaffold.ci42504842750`; **user-provided raw telemetry**, not fetched from Android or read from an independently signed measurement store. No raw file hash supplied, so integrity and completeness of original on-device JSON remain `REQUIRES_DATA`.
- On-device path asserted in user log: `/data/user/0/org.unovyra.uno.scaffold.ci42504842750/files/diagnostics/uno_lab_report_1794159950910.json`. This is app-private: **not accessible** outside that Android sandbox by ordinary file managers.
- Recorded start `1794159920614` epoch milliseconds, equivalent to **2026-11-08 17:45:20.614 UTC**; run type `OWNER_INITIATED_SANDBOX_ONLY`, `profile=STRESS`; `profile_limit_ms=60000` is a ceiling, **not an expected 60s duration**.
- Hardware identity as observed: Samsung `SM-A525F`, Android 14 / SDK34; reported RAM `3,574,796,288` bytes OS-visible; ABI `arm64-v8a`. Do not generalize these samples to another Android device or a trained neural workload.
- **Measured elapsed** `30256 ms`; `abort_reason_or_null=null`; exactly **8 scenario entries with status PASS**, defined in `android/app/src/main/kotlin/org/unovyra/uno/DeviceLab.kt` (Git blob `326f0fcc7f3a9859fb5a00049337d9cfe178b0fc`) and `android/core/src/main/kotlin/org/unovyra/uno/core/LabProtocol.kt` (Git blob `cdb877a77c096e94504115e55f971dd5252787e9`). These labels mean each *synthetic scenario's own completion checks* passed, **not** that agent intelligence, native authority, model runtime, or power budget passed.

## Per-scenario observations (owner's raw report)

| Scenario | Observed status and metric | Correct proof boundary |
|---|---|---|
| CPU_FP32 | PASS; width 128; 48 rounds; each `2,097,152` scalar MAC; duration `186,818,906 ns`; p50 `3,865,729 ns`, p95 `3,906,719 ns` | Naive fixed FP32 matrix multiply; about **539 million counted scalar MAC/s** *only for this kernel*, no optimized NN/MAC, no model weights |
| CPU_SUSTAINED | PASS; `2,919` batches; 25.008 s; p50 batch `7,899,948 ns`, p95 `8,142,187 ns`, p99 `9,604,583 ns` | `LabProtocol.sustainedCpu` calls `cpu(2,128)` per batch, equivalent to about **490 million counted scalar MAC/s** over sampled 25 s; not a controlled CPU-throttling or joules result |
| CPU_PARALLEL | PASS, 2 of 2 own worker threads completed; 24.28 ms | Neither CPU affinity nor demonstrated parallel speedup |
| QUEUE_STOP | PASS, 16,000 attempts; 64 accepted, 15,936 rejected; capacity 64; queue STOP preempted subsequent scheduling | **Synthetic** `BoundedScheduler`; not owner STOP pressed during real Android-effect dispatch or in-flight cancellation |
| HEAP_PRESSURE | PASS; 64 MiB own-process bounded allocation; duration 153 ms | Not OOM margin, true production weights memory, or memory leak absence |
| INTEGRITY | PASS; 2 MiB buffer; deliberate changed byte detected | Only volatile in-memory SHA-256 check; no filesystem or database crash consistency |
| STORAGE_FSYNC_SHA256 | PASS; 2 MiB local app fixture; fsync-inclusive write `33,254,479 ns`, subsequent read `9,270,260 ns`, hash match | Real app-private storage read/write tested; **not** physical power-cut durability, SQLite WAL recovery, or independent native readback |
| SENSOR_STREAM | PASS; 7 selected, 4.076 s; six streams yielded samples, proximity type 8 yielded 0 | Sensors delivered timestamped observations, no absolute sensor accuracy; zero proximity events may reflect no triggering stimulus, not established sensor fault |

## Resources, thermals, UX — measured with caveats

- Initial process **PSS = 111426 KiB (108.8 MiB)**; final **106310 KiB (103.8 MiB)**. `HEAP_PRESSURE.after` shows **165157 KiB (161.3 MiB)**; this is a sampled high point **not a proven global process peak**. Data insufficient to bound memory of a full NN model.
- System available RAM initial `1,087,164,416` bytes, final `1,105,915,904` bytes; `system_low_memory=false` at samples. Do not treat this as future model allocation budget.
- `process_elapsed_cpu_ms` 13727→41254 = **27,527 ms** over 30,256 ms wall; process CPU time can include concurrent threads, so the ratio ≈0.91 is **not direct single-core utilization**.
- ART `art.gc.gc-count`: 8→111 (**103 GC events**) and reported cumulative `art.gc.gc-time`: 142→1367 (**+1225 ms**). `art.gc.blocking-gc-count=0` at endpoints. High allocation/GC activity is a **real workload observation**, but gc-time is not necessarily a sum of UI pauses.
- Report `ui_heartbeat_delays_gt_350ms=0`, `ui_max_heartbeat_delay_ms=174`. This only measures 250 ms in-app heartbeat scheduling; **does not prove 60/90 Hz frame pacing, gesture responsiveness, or no jank**.
- Battery 28%→27%; temperature 28.2→28.4 °C; `thermal_status_code_or_null=0` at sampled endpoints; no power-saving flag; `thermal_headroom` intermittently `null`. Percent increments/short time window and current-sensor OEM uncertainty preclude robust watts/joules, thermal steady state, and throttling estimates.
- Sensor catalogue `count=34`, of which multiple entries are fused/virtual/vendor sensors; **not** 34 independent calibrated hardware sensors. Selected sensor type 8 `Ear Hover Proximity Sensor` had 0 observed events; all seven were enumerated and the source logic declares SENSOR_STREAM PASS if at least one delivered event total.
- Report flags `network_used_by_lab=false`, `app_android_effects_enabled=false`, `trained_neural_model_loaded=false`, `neural_quality_tested=false`, `native_action_gate_tested=false`, `physical_joules_measured=false`, `no_external_effects=true`. These are generated lab-state assertions, **not network packet capture or independent OS-action attestation**.

## Cross-checks and remaining gates

Source code confirms `CPU_SUSTAINED` is a loop of two `CPU_FP32` rounds per batch; `QUEUE_STOP` exercises own in-memory bounded queue; `STORAGE_FSYNC_SHA256` writes and re-reads only app-private fixture. The source also confirms that **STRESS has a 60-second safety ceiling** and runs a 25-second CPU sustained segment plus other bounded checks; elapsed 30.256 seconds is consistent, not premature STOP.

**Newly achieved:** Android APK installation, foreground launch, stress dispatch, CPU/heap/storage/sensors, and in-app full-JSON clipboard export are **observed working together on Samsung A52** for this one run. Clipboard action succeeded sufficiently for the owner to paste report; exact original raw byte-level equality is not provable without the saved JSON file.

**Not yet tested:** `AndroidOutcomeInspection` missing DB / initialization / fresh restart; `KeyguardManager` device-credential NOOP and one-use consumption; owner pressing STOP **while** a test is running; Android lifecycle background/restart; native OS actions, independently verified readback, production neural runtime or weights, model quality, in-situ learning or commercial release. Do not shift the project away from current release-first AGO rules.

**Next practical device acceptance:** with this same installed `UNO TEST` build, press `Проверить SQLite (без создания базы)` → `📋 СКОПИРОВАТЬ ВЕСЬ ПОСЛЕДНИЙ ОТЧЁТ`; expect `status=NOT_INITIALIZED` only if DB not previously created. Then independently test `Создать пустую SQLite-базу и проверить`, app restart and read-only reinspection; finally credential NOOP/STOP. No further stress loops requested until a particular defect or changed model workload justifies repetition.
