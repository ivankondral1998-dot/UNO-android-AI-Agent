# UNO 1.0 — ЕДИНАЯ ИНЖЕНЕРНАЯ КАРТА / HANDOFF ДЛЯ GROK И ЛЮБОГО НОВОГО АГЕНТА

## UPDATE 2026-11-10 — SINGLE-TAP DIAGNOSTIC / COMPACT OWNER UI

Introduced one bounded owner-triggered QUICK self-test on the same Android applicationId. Old manual lab controls move behind an expandable engineering panel; visible STOP and JSON copy retained. Auto-run reads existing encrypted memory/marker and SQLite only; owner authentication, native Android effect and neural quality are expressly untested. Overall PARTIAL is not device acceptance. See [implementation](implementation/2026-11-10_UNIFIED_OWNER_DIAGNOSTIC_R1.md). **Do not elevate to ANDROID_BUILT/DEVICE_VERIFIED without fresh evidence.**

---

## UPDATE 2026-11-10 — FRESH DISK READBACK / OWNER DEVICE GATE

Implemented an explicit diagnostic for reopening persisted exact device
observations from disk (not the process singleton). The reader refuses key
creation/genesis, vault mutation and AtomicFile read-side repair; full
immutable source bytes and encrypted payload digest must match. The
owner's locator is stored separately and never treated as authority.
Existing device-reboot data still fails closed with UNKNOWN; no temporal
policy silently invented. Negative static checks added.
**CI VERIFIED:** source `a095ae796b236db71fd0fc2d534f86a0d4107daf`; private [run #42729419491](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42729419491) SUCCESS. 305 core host checks (47 encrypted memory), static negative regressions, Android SDK35 build, lint, APK/badging/manifest gates PASS. APK SHA-256 `f50b26425f310b493adb4c8bd6e1a8202650bd42e5bc8f35eeb7de3cc1824f57`. **DEVICE_UNTESTED**. [Source, tests, and physical acceptance](implementation/2026-11-10_EXACT_REOPEN_DIAGNOSTIC_R1.md).

---


## UPDATE 2026-11-10 — FIRST-OPEN EXACT MEMORY GENESIS

**Verified source:** `cf36fa1b4fef2dfbf50421456b09cac00ae42877`.
[CI #42725873442](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42725873442)
SUCCESS: 305 host assertions (47 encrypted exact-memory assertions),
Android debug APK build and lint PASS; APK SHA-256
`08815ee393d839553846b2fbfa0b9972b9ba3c16c0d99abbd6fffe035b4bb4fa`.

**Negative history/provenance:** preceding run
[#42725562176](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42725562176)
FAIL: opt-in Boolean was placed after `clockElapsedNanos`, breaking existing
Kotlin trailing-lambda calls. Code fixed by restoring the clock as the
last constructor parameter, preserving older call sites; the exact
retest above passed. This FAIL is retained, not renamed as PASS.

**Not verified:** on-device AndroidKeyStore genesis, interrupted first
commit, missing-key recovery, cross-reboot exact memory, anti-rollback,
and production unified neural intelligence. **FOUNDATION_INCOMPLETE**.


New keys now receive an authenticated empty snapshot before accepting an
observation. Existing snapshots are not migrated/replaced; corrupt state or
existing key with no snapshot still fails closed. This narrows—but does not
eliminate—the crash window between key creation and a durable snapshot.
[Patch and remaining blockers](implementation/2026-11-10_EXACT_MEMORY_GENESIS_R1.md).
Host/Android CI SUCCESS for source cf36fa1; **DEVICE_UNTESTED**.

---


## UPDATE 2026-11-10 — CORRECTIVE AUDIT / CONSENT + PROVENANCE

**CI VERIFIED:** [exact-source run #42715526164](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42715526164), commit `d9a0791ffe80fb3e3d32b1cd449282d8ac1ff230`: SUCCESS. Static-negative UI/permission checks, 299 core host checks (41 encrypted-exact-memory checks), Android arm64 debug build, Android Lint, APK package and manifest checks PASS. APK SHA-256 `f205056752516d07315d91fec0d994a87cd8234463233c7db8c01d04d0fbf6bf`. **No Samsung device verification or accepted neural F/model/authority**; only the source was built.

Source-level review found unannounced durable memory writes in the passive
Android metrics button, Keystore failure blocking an unrelated read-only
diagnostic, and mismatched/overwritable diagnostic SHA evidence. These have
been corrected in the feature branch. Old experimental chat clear now
truthfully warns that v1 plaintext survives; explicit owner-confirmed
scoped revocation is available without automatically deleting files.
Negative static regressions guard consent and provenance.
**CI SUCCESS; DEVICE_UNTESTED.** This is not memory-stage
acceptance or full UNO closure. [Detailed severity, fixes and open
blockers](implementation/2026-11-10_CORRECTIVE_IMPLEMENTATION_AUDIT_R1.md).

---


## UPDATE 2026-11-10 — ANDROID FOUNDATION OBSERVATION WIRING (CI SUCCESS)

**CI SUCCESS:** [run #42708637287](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42708637287) on exact code `de7bc300e0b91e00fa84af4bb724cf067b797145`: 299 host checks (41 encrypted exact-memory checks), Android debug APK, lint, static manifest and APK validation. APK SHA-256 `2ad2e48ba841914977a3be6a5e1b35cbb4676677acfa5e922c51689edc798f9b`. **DEVICE_UNTESTED**, no download requested. The source code does not change in this documentation update.

Actual Android device metrics now enter the existing single UnoFoundationReferenceCycle
and commit selected exact fields into encrypted UnoAndroidExactMemory.
UnoAndroidMemoryOwner enforces a process singleton and OS file lock
against concurrent writers. Persistent generation is used for event keys,
allocated under a shared memory mutex; the committed key is returned
in the typed receipt. Android lifecycle/STOP denies new observations.
Android authority remains deny-all; no verified OS effect or accepted neural
intelligence or F. **DEVICE_UNTESTED**.
[Implementation and limits](implementation/2026-11-10_ANDROID_EXACT_OBSERVATION_WIRING_R1.md).

---


## UPDATE 2026-11-10 — ORIGINAL WP-05 DURABLE EXACT MEMORY CANDIDATE

**CI VERIFIED:** [Run #42704791187](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42704791187) for exact source `85be43e55775daaa2d17207577a7f4785b6e3ba0` completed SUCCESS: full preflight, 292 host checks including 34 encrypted exact-memory cases, Android debug APK, lint, manifest/permissions check; APK SHA-256 `2a5576370f3d9299a51fe644b5f95e432f8dc124ee1485eb284de020e13e114c`. New APK not distributed or device-tested.

**Working feature:** new `UnoExactMemoryPort` + `UnoEncryptedExactMemory` + `UnoAndroidExactMemory`. Versioned AES-256-GCM authenticated snapshots, AndroidKeyStore/AtomicFile, source/epoch/boot-bound exact bytes, fail-closed corrupt/key-missing input, monotonic read clock, durable revocation tombstones. Existing original end-to-end reference can now accept an injected persistent exact-memory port. Tests explicitly forbid arbitrary `VERIFIED_COMPLETION` and do not treat semantic summaries as exact facts.

**Limits:** adapter is not yet wired to the production Activity; Android device key/boot compatibility NOT tested, same-boot restart NOT device verified, no rollback protection against old valid ciphertext and no fully semantic retrieval/owner auth. Original WP-05 remains **PARTIAL**. [Source, limits, tests](implementation/2026-11-10_ORIGINAL_WP05_ENCRYPTED_EXACT_MEMORY_R1.md). No changes to F/weights/main and no new permissions.

---


## UPDATE 2026-11-09 — ROADMAP CORRECTION / ORIGINAL END-TO-END REFERENCE

**SOURCE COMMIT:** `34b4dd3131406795a7db7c2030b975139e630927`, feature branch. [CI #42698868434](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42698868434) **SUCCESS**: full preflight, 258 host checks (including 23 new original-roadmap WP-06-T01 reference tests), Android SDK/NDK debug build, lint, aapt/source binding. New APK SHA-256 `58cecea663a9c459e4fd33899feb57771a8e5f967b771dba3c271973c9fe0814`. Exact SHA **not device tested**, no download requested.

**CORRECTION:** Prior patches named WP-05 text cycle/encryption and WP-06 GGUF-without-copy are *experimental chat patch labels*, **NOT stages of the original UNO roadmap**. The actual [roadmap](roadmap/UNO_1_0_MASTER_PLAN.md) says **WP-03 = single F / shared state, WP-04 = own immutable weights (owner-gated), WP-05 = exact/semantic memory, WP-06 = unified end-to-end agent**. Never mark those original stages complete from chat UX or a Qwen APK.

**IMPLEMENTED/HOST_TESTED:** `UnoFoundationReferenceCycle` is a single NeuralPort neutral trace: Percept -> bounded scheduler -> exact in-memory observation -> untrusted model proposal -> owner interface -> TrustController decision -> reference native outcome/readback. All fake JVM readbacks remain `REFERENCE_READBACK_CLAIM`, `verifiedAndroidEffect=false`; `VERIFIED_COMPLETION` memory cannot be fabricated. Unknown outcome is not retried. Cross-screen process STOP was additionally enforced for lab admission, owner NOOP and app-private marker creation. **Android trust remains DENY_ALL**. This is scaffold parity evidence, not real neural cognition or production effect dispatch.

**OPEN:** Still need persistent shared causal state, exact/semantic memory and recovery, neural isolation, accepted offline model selection, planning, speech/sensors, owner-bound Android authority + true native readback, device safety review. Research F and production training NOT authorized by this work. **FOUNDATION_INCOMPLETE**. [Precise source and limitations](implementation/2026-11-09_ORIGINAL_WP06_REFERENCE_R1.md).

---


## HISTORICAL EXPERIMENTAL CHAT PATCHES (NOT ORIGINAL ROADMAP WP-05 / WP-06)

**HEAD:** `083e30c0f53921b87003c40f20c64fa1786dce3f` on `feat/uno-foundation-hardening-20261107`. `main` unchanged. Current Android CI [#42686428239](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42686428239) **SUCCESS**: 235 host checks, core Gradle suite, arm64 Android APK, lint and manifest/package/native-library validation. APK package `org.unovyra.uno.scaffold.ci42686428239`, SHA-256 `764d1ceade9d4bd0591bda9a54b02a0240a9e40c780da283f74cb5bd2eaa3ad6`; this private debug APK is **not** distributed for owner testing here. CI artifact `13705910752` is retained temporarily in the private workflow. Earlier [#42684195249](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42684195249) failed on missing `UnoTextCycle` UI imports; corrected in next [#42685394826](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42685394826), which was also SUCCESS. Do not erase the failed run.

**IMPLEMENTED:** app neural chat now routes a local UI text event through `UnoTextCycle` with single bounded state, cancel/STOP checks, safe persistence-on-success and receipt hash (not OS outcome); user-initiated clear goes through the same state. v2 app-private chat saves with AES-256-GCM + AndroidKeyStore key; old v1 plaintext is read for compatibility and retained (no deletion). Root and chat STOP connect through one `UnoProcessStop` **same-process only** latch, with no automatic rearm while process alive. New default model picker is **GGUF без копии**, experimental direct read-only SAF fd path; old private-copy import survives as a clearly labelled manual fallback. New source paths and tests: [WP05 text cycle](implementation/2026-11-09_WP05_TEXT_CYCLE_INTEGRATION_R1.md), [WP05 secure chat / stop](implementation/2026-11-09_WP05_LOCAL_CHAT_PROTECTION_AND_PROCESS_STOP_R1.md), [WP06 disk](implementation/2026-11-09_WP06_DIRECT_GGUF_NO_DUPLICATE_R1.md), [Foundation acceptance](implementation/2026-11-09_FOUNDATION_ACCEPTANCE_REGISTER_R1.md).

**OWNER DEVICE EVIDENCE CORRECTION:** In this chat owner subsequently installed old `ci42670625565` on Samsung Galaxy A52 and sent screenshots of real native GGUF generation at ~2.4 t/s (overall), TTFT ~24.7 s, poor multi-turn behavior with visible `<think>`, with no UI stutters reported. Therefore OLD WP04 source now has `DEVICE_OBSERVED_TEXT_GENERATION` (limited); the previous handoff's blanket `DEVICE_VERIFIED_WP04=FALSE` was true when authored but superseded for this one text path. The new WP05/06 APK has NOT been tested on Samsung or Huawei. **Do not extrapolate performance, quality, offline proof or model F from old screenshots.**

**STATUS:** `FOUNDATION_INCOMPLETE`, `WEIGHTS_TRAINING_AUTHORIZED=FALSE`, `RELEASE_READY=FALSE`. Neural worker isolation, general state/memory, planner, local voice, Android trust/real native effect/readback still open. The next agent should read [Foundation acceptance](implementation/2026-11-09_FOUNDATION_ACCEPTANCE_REGISTER_R1.md) then source, not call this finished.

---


## UPDATE 2026-11-09 — WP-04 EXPERIMENTAL ON-DEVICE NEURAL CHAT (ANDROID BUILT; NOT DEVICE VERIFIED)

**Current product goal:** owner's release-first decision (07.11) remains in force; own F/new weights research remains separate, not displaced by Qwen. New experimental text-only chat uses pinned MIT llama.cpp and owner-supplied GGUF, never authorizes Android actions.

**EXACT BUILT SOURCE:** feature branch `feat/uno-foundation-hardening-20261107`, source commit `7990bc8af5cc58a6c195d42c957be6dc0e75f412`. Earlier precode WP03 commit `912b1f7aee03ab6071ad7823802d9ac2811ee02c` preserved as ancestor. `main` untouched.

**CI EVIDENCE:** GitHub Actions [run 42670625565](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42670625565) `SUCCESS`; standalone `run_all_preflight.sh`, Gradle `:core:unoHostTests`, Android NDK arm64 + `:app:assembleDebug`, `:app:lintDebug`, aapt package and permission validation, and native-lib presence. Host harness prints `UNO_CHAT_WINDOW_HOST_PASS=10`, total `UNO_WP01_HOST_PASS=203`. The first WP-04 CI [42670096975](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42670096975) **FAIL**: old static guard disallowed second Activity; resolved with exactly-one-local-non-exported-chat-Activity guard plus 4 negative tests, not by disabling protection.

**PRIVATE SIDE-BY-SIDE APK:** GitHub artifact `13698867287` (name `uno-side-by-side-debug-10`), package `org.unovyra.uno.scaffold.ci42670625565`, label `UNO TEST · ci42670625565`, minSdk26, targetSdk35, size **7,910,771 bytes**, SHA-256 `af331736d568a14a1b8b9e05e1ce5ccfee626cd847a67780da5eba7801fcf6b5`. Artifact archive integrity and APK zip integrity independently checked in ChatGPT runtime. APK contains `libuno_llama.so`, `libllama.so`, `libggml.so`, `libggml-cpu.so`, `libggml-base.so`, all arm64-v8a; `readelf` confirms JNI exports `load/generate/cancel/resetCancel/unload`. Manifest aapt check shows no INTERNET/RECORD_AUDIO/CAMERA. No trained weights bundled; owner explicitly imports local GGUF via allowed local SAF provider.

**DEVICE STATUS:** `ANDROID_BUILT=TRUE` for built source; `DEVICE_VERIFIED_WP04=FALSE`, `RELEASE_READY=FALSE`. Huawei nova 10 SE / Android12 / 8GB RAM demonstrated Qwen3-0.6B in PocketPal, **not** this UNO APK; Samsung A52 results similarly belong to PocketPal. No claim of real UNO inference, phone battery/RAM or true offline network isolation yet. Chat history app-private exact JSON is **unencrypted**, separate from future exact/semantic long-lived memory. Neural JNI currently runs in the app process, not in isolated NeuralWorkerService. Android trust/STOP/real action/readback remain **deny-all**. See [WP04 R2 build evidence](implementation/2026-11-09_WP04_OFFLINE_NEURAL_CHAT_BUILD_EVIDENCE_R2.md).

---

## UPDATE 2026-11-08 — WP-03 APP-PRIVATE EFFECT / READBACK (LATEST)

**Owner-device milestone already closed:** A52 `UNO TEST ci42509757092` first NOOP one-use accepted and consumed; second denied; two screenshots. See [A52 one-use evidence](implementation/2026-11-08_A52_OWNER_NOOP_ONE_USE_DEVICE_EVIDENCE_R1.md). This does not authorize native effects or establish unique UNO owner identity.

**New IMPLEMENTED scope:** `AppPrivateReadbackProbe.kt` creates one **fixed, bounded, random-ID marker** inside UNO's private files, fsyncs, reopens through fresh descriptor and checks exact bytes/SHA-256. Max 16 markers, no delete/overwrite. STOP before create denies; after create returns `UNKNOWN_MAY_HAVE_WRITTEN` if uncertain. `UnoActivity.kt` adds owner-tapped create/read and separate read-only reopen (including after restart) with opaque locator in app-private preferences. `DenyAllAndroidPort`, `NoWeightsNeuralPort`, owner NOOP credential logic, old SQLite action journal, and Jarvis architecture remain unchanged. **Not** a trusted NativePort, not verb 15, not an intelligent model, not an Android external effect. See [WP03 contract, source provenance, test limits](implementation/2026-11-08_APP_PRIVATE_EFFECT_READBACK_WP03_R1.md).

**Verification:** GitHub Actions [#42512824888](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42512824888) SUCCESS, exact built SHA `2c32e0371a1674a44d1125264ab5cace052a9c16`, Kotlin host private-effect **9/9 PASS**, static guard/negative tests, Gradle core suite, SDK35 assembleDebug/lintDebug and aapt checks. APK `UNO TEST · ci42512824888`, package `org.unovyra.uno.scaffold.ci42512824888`, size **930250 B**, SHA256 `845baedb63aa068e9ade56a37dc3adc3dbce0d87111885f447146c29a003f621`; ZIP integrity/sha independently checked. Owner direct APK [private Drive](https://drive.google.com/file/d/1qcX_EQrbOf52AjisuzY5GusG0qYTi3Gs/view?usp=drivesdk) metadata `shared=false`. **HOST_TESTED=TRUE; ANDROID_BUILT=TRUE; DEVICE_VERIFIED_WP03=FALSE.** Existing A52 screenshot evidence belongs to previous build `ci42509757092`. Do not ask owner for STRESS repeats; new tiny fixture requires only manual two-button test, then reopen after app restart.

**Sources cross-checked:** active root AGENTS V3, Astra R5.3 Android trust/STOP/verb15, Grok B2 provenance audit, Jarvis AndroidOperationAuthority/ConfirmationTicketGate read-only. Future full UNO requires a real licensed offline neural model, memory, trusted Android action boundary and native readback; this local fixture does not close those gates.

---


## UPDATE 2026-11-08 — A52 CREDENTIAL NOOP ONE-USE: DEVICE OBSERVED (LATEST)

**РЕЗУЛЬТАТ С УСТРОЙСТВА, ДВА СКРИНШОТА ВЛАДЕЛЬЦА:** на точно идентифицированной сборке **`UNO TEST · ci42509757092`** после системного экрана отпечатка Android 14 первый `Проверить одноразовое согласие · без действия` показал **«NOOP: одноразовое подтверждение принято и погашено · действий ОС нет»** (часы на телефоне ~21:33), второе нажатие — **«NOOP: подтверждение отсутствует, истекло или уже использовано · действий ОС нет»** (~21:34). Отображение результата непосредственно под кнопками также **DEVICE_OBSERVED**: исправление UX от GitHub Actions #42509757092 заработало на A52.

**DEVICE_VERIFIED_LIMITED:** настоящий пользовательский диагностический путь `KeyguardManager` → NOOP → one-use consume **наблюдался положительно**; одноразовость по двум локальным ответам подтверждена. Это не криптографическая проверка callback, не proof уникального владельца UNO, не разрешение на Android эффекты, не проверка STOP/dispatch/native readback и не доказательство работоспособного нейросетевого ядра. В исходниках `DenyAllAndroidPort`, `NoWeightsNeuralPort` продолжают действовать. **Не гонять тот же тест вновь без изменений кода**.

Полный версионированный [device-evidence и SHA двух screenshot-attachments](implementation/2026-11-08_A52_OWNER_NOOP_ONE_USE_DEVICE_EVIDENCE_R1.md) (скриншоты в chat, **не в git**). Статус `OWNER_CREDENTIAL_NOOP_ONE_USE=DEVICE_OBSERVED_PASS`; `REAL_NATIVE_EFFECT_READBACK=NOT_TESTED`; `RELEASE_READY=FALSE`. Батарея на скриншотах 19%: не требовать новых STRESS прогонов. Следующий инженерный рубеж — один ограниченный безопасный app-private effect + независимый query/readback, а не урезание архитектуры UNO.

---


## UPDATE 2026-11-08 — A52 OWNER BIOMETRIC / INVISIBLE OUTCOME (LATEST)

**ФАКТ ОТ ВЛАДЕЛЬЦА:** в `UNO TEST ci42504842750` после нажатия «Проверить владельца через экран Android» открылся системный **отпечаток пальца**. После нажатия «Проверить одноразовое согласие» пользователь сообщил «ничего вообще не произошло». **НЕЛЬЗЯ** считать Android `RESULT_OK` или успешный `consume` установленным фактом: не получены тексты статуса/OS callback logs. По исходнику воспроизведён дефект UX: обе операции обновляли только `status` **вверху** длинного ScrollView, тогда как кнопки находятся ниже.

**IMPLEMENTED + ANDROID_BUILT:** добавлен `ownerFeedback` прямо под кнопками и общий `showOwnerFeedback` для OS callback/one-use результата; статический регрессионный guard + две отрицательные проверки. `OwnerConsentState`, STOP, модель и `DenyAllAndroidPort` **не менялись**. [GitHub Actions #42509757092](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42509757092) SUCCESS, built SHA `502088cadbbfec603bd52e8dc46be150afe3e41e`, package `org.unovyra.uno.scaffold.ci42509757092`, launcher `UNO TEST · ci42509757092`, APK 924794 B, SHA256 `a26d12d94d690afb6f5176a5ad682e8bed2c1f6205e48377274999603d4b7f6c`, приватный Google Drive APK https://drive.google.com/file/d/13z9r0_195niHfEwo1QHi9jabp-fRlx6-/view?usp=drivesdk. ZIP/APK и SHA проверены. Инженерный отчёт: [A52 fingerprint feedback R1](implementation/2026-11-08_OWNER_CREDENTIAL_A52_UI_FEEDBACK_R1.md).

**GATE:** новая сборка `ANDROID_BUILT`, но `DEVICE_VERIFIED_FOR_THIS_APK=FALSE`; одноразовое согласие ещё `REQUIRES_DATA`, security logic unchanged. В уже установленной старой версии можно просто прокрутить **наверх** после нажатия, где текст статуса изменится. В новой версии ответ будет непосредственно под кнопками; OS результат и факт one-time consume должны быть проверены на A52. Никаких повторов STRESS и продвижения к Android native actions до этой проверки не требовать.

---


## UPDATE 2026-11-08 — A52 SQLITE INSPECTION — OWNER REPORT (LATEST)

**Физическое испытание владельцем:** установленная сборка `org.unovyra.uno.scaffold.ci42504842750`; получен скопированный JSON `UNO_OUTCOME_INSPECTION/1`: `status=INSPECTED`, `total=0`, `prepared=0`, `may_have_executed=0`, `stored_readback_claims_UNVERIFIED=0`, `native_actions_enabled=false`, `verified_os_outcomes=false`. По коду `AndroidOutcomeInspection.inspect(false)` статус `INSPECTED` означает, что main DB **существует и доступна** в момент обращения, иначе был бы `NOT_INITIALIZED` или `UNAVAILABLE` (при обнаружении sidecars). **Когда возникла база — неизвестно; нет доказательства персистентности непустых записей, authority, native readback.** Никакой ошибочный `PASS` о действиях/модели не присваивать.

[Точный owner-evidence и границы](implementation/2026-11-08_A52_SQLITE_INSPECTION_DEVICE_EVIDENCE_R1.md). Следующая информативная проверка без новой сборки: owner `Android` credential **NOOP** и погашение one-use (дважды), затем отдельный ручной STOP на QUICK во время выполнения; пустая SQLite с повторным нулевым счётчиком только проверяет доступность после нового запуска, не запись/восстановление данных. Повторять STRESS без оснований не нужно. Кода/весов/Jarvis/Grok/main не меняли.

---


## UPDATE 2026-11-08 — A52 STRESS PHYSICAL EVIDENCE (LATEST)

**РЕАЛЬНЫЙ DEVICE-ОТЧЁТ ОТ ВЛАДЕЛЬЦА:** Samsung Galaxy A52 `SM-A525F` / Android 14 (API34), установленный `UNO TEST · ci42504842750` / package `org.unovyra.uno.scaffold.ci42504842750`, owner-copied full `UNO_OFFLINE_LAB_REPORT_1`: **`STRESS`, 30256 ms, 8/8 sandbox scenarios `PASS`, `abort_reason_or_null=null`**. Это первое реальное device-подтверждение выбранного диагностического APK, его запуска и копирования JSON, но **НЕ** подтверждение готовности интеллекта, `AndroidOutcomeStore`, owner-credential или native readback.

**Наблюдения:** `CPU_FP32` 48 раундов 128³ FP32 naive, p50 ≈3.866 ms, p95 ≈3.907 ms; 25.008 s `CPU_SUSTAINED` 2919 batches, p95 ≈8.142 ms (по исходнику каждый batch — два раунда); 2/2 parallel; synthetic queue STOP 64/16000 accepted, real Android STOP race **не проверялся**; heap 64 MiB, measured process PSS 108.8→103.8 MiB, sampled 161.3 MiB under pressure; app-private `fsync`+2 MiB SHA readback PASS, **не power-cut proof**; 34 enumerated Android sensors (fused/vendor included), 7 selected, 6 streams delivered events, proximity type8 0 samples. UI heartbeat 0 delays ≥350 ms, max174 ms; **не Android frame pacing**. Батарея 28→27%, 28.2→28.4°C, thermal status0; **не физические joules/thermal limits**. No loaded weights or native actions.

**Статус:** `DEVICE_VERIFIED` **только для этих восьми диагностических сценариев** как owner-produced telemetry; не экстраполировать на neural runtime/OTA/recovery. Один пользовательский сырой JSON без hash/independent collection. Никаких дополнительных стресс-циклов без конкретного нового вопроса. Полный [версионированный физический отчёт и трассировка к реализации](implementation/2026-11-08_A52_STRESS_DEVICE_EVIDENCE_R1.md).

**Следующая проверка именно установленного APK:** (1) ручной `Проверить SQLite (без создания базы)` → copy full JSON, (2) явная инициализация пустой SQLite и её read-only повторное чтение **после перезапуска**, (3) device-credential NOOP и одноразовое consume, затем реальный STOP в активном лабораторном тесте. **Прежняя `DenyAllAndroidPort` и `NoWeightsNeuralPort` остаются; модель/веса/Neuron Language без правок.**

---


## UPDATE 2026-11-08 — UI COPY + IDENTIFIABLE TEST APK (LATEST)

**OWNER SCREENSHOT/ISSUE:** Отображалась лаборатория со старым одинаковым заголовком «UNOVYRA UNO · Scaffold», без SQLite/owner/copy-кнопок. При сравнении с текущим `UnoActivity` (кнопки SQLite и owner **есть между темами и RAM**) наиболее вероятно, что пользователь открыл старую отдельно установленную сборку, а не новый APK. Это **гипотеза**, пока нет on-device package identity/log. Отдельный дефект UX: отсутствовала кнопка копирования полного JSON, UI показывал только первые 14k символов.

**ИСПРАВЛЕНО И СОБРАНО:** `UnoActivity` теперь показывает `УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName` сверху, предоставляет **ручную кнопку копирования полного последнего JSON** в системный clipboard без 14k truncation (при новом запуске старый payload очищается). CI-only изолированный пакет получает отдельный resource-backed launcher label, видимый `aapt`: **`UNO TEST · ci42504842750`**. В `static_contract_check.py` добавлены положительные проверки элементов, в фикстурах — отрицательные регрессии. `DenyAllAndroidPort`, `NoWeightsNeuralPort`, offline и STOP не ослаблены.

**ANDROID_BUILT:** [GitHub Actions #42504842750](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42504842750) **SUCCESS** для exact SHA `a1410895ef3fe2f748ba3f6e70cf8e45f70a022e`. `aapt dump badging` подтвердил package **`org.unovyra.uno.scaffold.ci42504842750`** и label **`UNO TEST · ci42504842750`**; APK **924526 B**, SHA-256 **`cfb8f3de6df47a25e709563117f33d829f0445054a9919846d937e0d10a51f6a`**, проверен повторным хешированием и ZIP integrity. Private Google Drive APK https://drive.google.com/file/d/1YsPRCW5wL-_EYx2flCAdJN393kW6NEpf/view?usp=drivesdk (readback size/MIME/visibility OK). GitHub artifact ID `13627416075`.

**СОХРАНЁННЫЕ FAIL:** CI #42504065211 — clean fixture после новых положительных guard; CI #42504217888 — `aapt` не видел inline label. Оба устранены, не замаскированы. См. [полный версионированный акт с SHA/исходниками](implementation/2026-11-08_UI_DIAGNOSTIC_COPY_AND_BUILD_IDENTITY_R1.md).

**GATE:** сборка, host и lint прошли, но **на A52 новый APK ещё не проверен**. Следующий пользовательский шаг: открыть именно **UNO TEST** с идентификатором `...ci42504842750`, проверить SQLite, затем кнопку копирования и прислать JSON; после — owner NOOP, STOP и recovery. Исторический Jarvis V21, Grok, Astra/R5.3, UNO-N0/FR/TR не изменялись; Neural Language отдельно. `FOUNDATION_INCOMPLETE`.

---


## UPDATE 2026-11-08 — SIDE-BY-SIDE APK, INSTALL CONFLICT

Владелец сообщил Android install отказ: конфликт с другим установленным пакетом. **Подпись как причина — гипотеза, на A52 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`/cert пока не собраны.** Старое приложение и данные **НЕ удалять**. Исправление на feature branch: только CI debug получает уникальный суффикс `-PunoIsolatedDebugSuffix=ci${GITHUB_RUN_ID}`; обычные debug/release applicationId неизменны. ADB-подсказка в UI использует фактический `packageName`. Никаких изменений Jarvis/Neural Language/Astra/Grok.

**Реальный новый APK собран:** GitHub Actions [run #42493602248](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42493602248), **SUCCESS**, exact built source SHA `0afa6cb9850faee68abea0e93be98794db41b930`; `aapt dump badging` проверил **`org.unovyra.uno.scaffold.ci42493602248`** (не прежний `org.unovyra.uno.scaffold`). Размер **922678**, SHA-256 **`63b46afedb03641c189e7f9c71ede28b8e16b426878ab924952d16f69bc776c1`**, ZIP/APK checks integrity PASS. Отдельный приватный APK на Google Drive: https://drive.google.com/file/d/1M_Pzo19E9eVDSwFo8OmHYMOrXJWIbjgP/view?usp=drivesdk ; Drive подтвердил точный size и MIME. Подробный [акт исправления установки](implementation/2026-11-08_WP02_APK_INSTALL_CONFLICT_SIDE_BY_SIDE_R1.md).

**Это тестовая side-by-side сборка, не upgrade старого пакета**. Система создаёт новый sandbox, не импортирует существующие данные. Для обновлений в будущем понадобится фиксированный production/debug signer, не очередное изменение package ID. `DEVICE_VERIFIED=FALSE` до установки и реального test на A52, `FOUNDATION_INCOMPLETE` — нет ядра, весов и native readback. GitHub Actions и Google Drive приватная доставка авторизованы на выполнение задачи; публикации релиза нет.

---


## UPDATE 2026-11-08 — ANDROID SDK35 BUILT — RUN 42488780925 (CURRENT)

**ФАКТ `ANDROID_BUILT`** (но `DEVICE_VERIFIED=FALSE`): первое успешно собранное APK с **реальным Android SDK35** для текущего feature-кода UNO, exact built SHA `de7d3e9c3e9634daa6ec20e7741d24546d088569`; private GitHub Actions [run #42488780925](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42488780925) **SUCCESS**. Debug APK `org.unovyra.uno.scaffold`, `0.1.0-skeleton`, min26/target35, **922662 bytes**, SHA256 `2c5285ea277acc11a8925900a66013a0ad4585946e84c13ef8cb09e72365ed37`. GitHub private artifact ID `13620288108` (ZIP SHA `5d0cb1cd1d5d35ef1fba89fb197a84a531d662f3a2e70eeedc7c741b06251424`; expires 11 Nov). Artifact privately downloaded, ZIP/APK checked, SHA rechecked.

**EXECUTED TESTS:** полный `bash android/scripts/run_all_preflight.sh` с реальным standalone kotlinc (НЕ skip): core aggregate `193` checks, SQLite schema `14/14`, Kotlin inspector `11/11`, owner state `31/31`, credential adapter stubs `11/11`, static/diagnostic Python PASS; независимый `gradle :core:unoHostTests` SUCCESS, `gradle :app:assembleDebug` SUCCESS, `gradle :app:lintDebug` SUCCESS **с 7 предупреждениями** (4 локализация, target SDK, data-extraction rules, иконка). `aapt dump permissions`: permission-запросов нет, включая INTERNET/RECORD_AUDIO/CAMERA. Полная [проверяемая ведомость и SHA](implementation/2026-11-08_WP02_ANDROID_SDK35_CI_BUILD_R1.md).

**НОВЫЕ ПОЛНОМОЧИЯ**: владелец 08.11.2026 разрешил **GitHub Actions при объективной необходимости, без повторных согласований**. Новое правило зафиксировано **в единственном действующем корневом `/AGENTS.md`**. Для данного случая локального SDK не было, так что запущен один адресный `uno-feature-android-verify.yml` в feature-ветке, workflow path-filtered; **ни `main`, ни releases, ни секреты, ни Jarvis/Neural Language не изменены**.

**НЕ ОБЪЯВЛЯТЬ ГОТОВНОСТЬ UNO:** APK представляет диагностический каркас, `DenyAllAndroidPort` и `NoWeightsNeuralPort` не заменены; A52-устройство не тестировалось, реальные права/owner identity/native dispatch/readback отсутствуют. `FOUNDATION_INCOMPLETE`. Следующий физический gate — установка именно этого APK на A52, проверка Android device-credential, STOP, SQLite read-only и lifecycle; затем адресная реализация app-private verified effect. Из R5.3/Astra и Grok остаются `A_cap/A_tx/A_fs` условными, Grok MATH-C01/MATH-C05 открыты, Jarvis — изученный источник контрактов, не скопированный OwnerGate.

---


## UPDATE 2026-11-08 — AUDIT R2: OWNER CONSENT BUGFIX (MOST RECENT)

**READ ROOT `/AGENTS.md`, CHECK GITHUB HEAD BEFORE CHANGES.** Самостоятельный аудит обнаружил и воспроизвёл **три ошибки текущего `OwnerConsentState`** (не Android device exploit): (SEC-01) диагностический экран принимал scope verb15 и произвольный SHA; (SEC-02) requestCode `0x4100` повторялся при пересоздании gate, из-за чего старый тестовый RESULT_OK мог быть принят новым pending challenge; (SEC-03) произвольное описание системного подтверждения принималось с семантикой NOOP. Все три исправлены: **строгий единственный `diagnosticNoopScope()` (verb2, fixed digest, empty permissions)**, единый фиксированный `DIAGNOSTIC_DESCRIPTION` из того же класса, process-wide `AtomicInteger` + random start modulo 16 112 request codes (без reuse в одном процессе до исчерпания диапазона). `UnoActivity` использует только централизованные значения. **Старые исходники/математика сохранены; правки только на feature-ветке.**

**Проверено на реально выполненных host тестах:** `31/31` owner state и `11/11` Android platform-stub (**42/42**, 5 отдельных повторных JVM запусков); дополнительно `58/58` prior core reference host, `14/14` настоящая host SQLite SQL, `11/11` inspector stub. **125 сценариев разного уровня, НЕ 125 Android device tests.** Исправлены имена прежних fake-permission тестов: NOOP не требует Android permissions, поэтому они *не* были доказательством реального permission revocation. [Полное версионированное erratum R2 и точные Git blobs](implementation/2026-11-08_WP02_OWNER_CONSENT_SECURITY_ERRATUM_R2.md). Прежний R1 не переписывался.

**Jarvis актуально сверен, только read:** `kolakbro5995-cpu/JarvisLab` `feature/v21-local-offline-runtime-20261101` @ `9c60f81d81d11a0977be1d36d928a3b5d273bbef`, `AndroidOperationAuthority`, `ConfirmationTicketGate`, негативные host-тесты. Сохраняем one-use, STOP, permissions/context/native preflight; не переносим Cloud OwnerGate, special lab bypass, старые веса. Аудит Grok `MATH-C01` и `MATH-C05` остаются открыты; Astra `A_cap/A_tx/A_fs` — CONDITIONAL, не «PASS».

**Границы:** requestCode уникален **только внутри процесса**; после смерти процесса случайная коллизия и OS callback routing ещё не исключены испытаниями на A52. Deprecation `KeyguardManager.createConfirmDeviceCredentialIntent` API29 подтверждена Android reference; возможный `BiometricPrompt` требует отдельной SDK/device проверки. Android SDK/Gradle и Galaxy A52 здесь не проверялись; полный `run_all_preflight.sh` текущей ветки не выполнялся; `DenyAllAndroidPort` и `NoWeightsNeuralPort` не заменены. **`FOUNDATION_INCOMPLETE`.**

---


## UPDATE — OWNER CREDENTIAL NOOP / WP-02 (2026-11-08)

**При первом входе сверить текущий HEAD GitHub и `/AGENTS.md`.** Android-лаборатория получила **реальное обращение к системному экрану проверки учётных данных устройства**, пока только для диагностического `NOOP` (verb=**2** по Astra, **не ABSTAIN=0**). Добавлены `OwnerConsentState.kt` (process-only one-use/TTL/session nonce/STOP/permission/foreground binding) и `AndroidDeviceCredentialPlatform.kt` (Android KeyguardManager, actual OS device-credential intent). В `UnoActivity` — два owner-tapped шага запрос→Android RESULT_OK→одноразовое подтверждение без native-effect. Операции не выполняются, `DenyAllAndroidPort` и `NoWeightsNeuralPort` сохранены. Старый OwnerGate Jarvis, его cloud auth, веса, архитектура не переносились.

**HOST_TESTED:** 24/24 Kotlin process-state + 11/11 Android-platform mock tests = **35/35 PASS**, фактические исходники совпадают с GitHub blob SHA. Тест зарегистрирован в `android/scripts/run_all_preflight.sh`. **Это не тест Android OS UI**: настоящий SDK/Gradle, A52, credential callback/lifecycle, STOP/OS linearization не проверены. Старый `KeyguardManager.createConfirmDeviceCredentialIntent` доступен, но deprecated с API29; заменить/подтвердить на целевом Android отдельным решением. [Полный отчёт, R5.3 и provenance Jarvis](implementation/2026-11-08_WP02_DEVICE_CREDENTIAL_NOOP_R1.md).

**Блокеры:** проверка учётных данных Android-профиля ≠ доказательство индивидуального владельца UNO; одноразовый NOOP ≠ trusted dispatch, не соединён с SQLite outcome/verified readback. `A_cap/A_tx/A_fs` **условны**, `FOUNDATION_INCOMPLETE`. Следующий шаг — проверка сборки/устройства, затем ровно один локальный проверяемый effect contract под owner auth + independent readback. `main`, Jarvis, Neural Language, модель и веса не менять без нового допуска.

---


## UPDATE — SQLITE INSPECTION UI / WP-02 (2026-11-08) — CURRENT

**Ветка, SHA и правила:** перед правкой заново прочитать `/AGENTS.md` и HEAD; прошлые SHA ниже — исторические снимки. В `UnoActivity` добавлены две явные диагностические кнопки: чтение существующей SQLite без её создания и создание пустой SQLite для последующей проверки. Фактический `AndroidOutcomeInspection.kt` открывает `AndroidOutcomeStore.inspectAfterRestart()` на текущем background worker, возвращает только агрегированные счётчики, не выдаёт билеты/не делает native. `NOT_INITIALIZED` отличается от `UNAVAILABLE`; осиротевший WAL без основной БД и любой corrupt/executable/unknown row → **UNAVAILABLE**, не пустая история и не успех. UI записывает только app-private JSON с явными `verified_os_outcomes=false`, `native_actions_enabled=false` или FAIL-CLOSED.

**Код/проверка:** добавлены `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeInspection.kt`, Kotlin host fixtures `android/scripts/inspection_host/*`, запускаемый `android/scripts/test_outcome_inspection_host.sh`, добавлен запуск в `run_all_preflight.sh`; подробности в [WP-02 Android inspection UI R1](implementation/2026-11-08_WP02_ANDROID_INSPECTION_UI_R1.md). **11/11 новых Kotlin inspector host**, **14/14 прежних host SQLite** и **58/58 reference controller/journal JVM** PASS отдельно (разные уровни, не Android integration). Полный preflight на текущем HEAD, Android Gradle, UI/device тесты пока НЕ запускались.

**НЕ ЗАКРЫТО:** Ни один privileged native action не разрешён — `UnoActivity` всё ещё `DenyAllAndroidPort()+DenyAllLedger()`, веса отсутствуют. Конкретный action-authority, owner identification, one-use consent, Android permission revalidation, STOP/OS linearization, independent native readback и device transactional proof остаются `SPECIFIED_UNTESTED`. Jarvis V21 `AndroidOperationAuthority` и `ConfirmationTicketGate` проверены как источники требований (не код для слепого переноса). R5.3/Astra/Grok, N0/FR/TR, Jarvis, Neural Language и старые источники сохранены. `FOUNDATION_INCOMPLETE`.

---


## UPDATE — ANDROID SQLITE BACKEND / WP-02 (2026-11-08)

**Сверяй живой HEAD перед следующей правкой.** Добавлен `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeStore.kt`: настоящий Android `SQLiteOpenHelper` / WAL / `beginTransactionNonExclusive`; одна БД фиксирует `operations.used + source-tagged readback claim + bounded memory_ref/payload` в одном SQL COMMIT. После process restart `inspectAfterRestart()` возвращает **неисполнимую** историю либо явный `Inspection.Unavailable`, но **не выдаёт** старых tickets и никогда не делает retry. Есть SHA-256 validation raw bytes на открытии; schema upgrade fail closed, никаких удалений или автоматической конверсии старых journal-файлов. Никакие модельные/OS действия новый store самостоятельно не выполняет.

**Границы проверки:** `android/scripts/test_sqlite_outcome_schema.py` содержит **14/14 PASS** на настоящей host SQLite из *непосредственно извлечённых Kotlin SQL-констант*, 3 повтора; Kotlin класс компилировался только с Android test stubs (не SDK/API35); предыдущий core reference host JAR повторно **58/58 PASS**. Новый SQL тест включён в `android/scripts/run_all_preflight.sh`, но **полный preflight с текущей веткой ещё не запускался**. Android Gradle APK, A52, crash-power-cut, ОС readback НЕ проверены. [Исходный технический акт](implementation/2026-11-08_WP02_ANDROID_SQLITE_TRANSACTIONAL_STORE_R1.md).

**Главный незакрытый переход:** backend `IMPLEMENTED_UNWIRED`: `UnoActivity` всё ещё использует `DenyAllAndroidPort/DenyAllLedger`, neural worker изолирован, реальной Android owner auth, live permissions, consent, native linearization/readback ещё нет. SQLite `REFERENCE_READBACK_CLAIM` **не** `VERIFIED_COMPLETION`. До будущей доверенной Android интеграции этот класс не производит действия и не доказывает A_cap/A_tx всей UNO, A_fs или antirollback. RAM/energy/thermal — `REQUIRES_DATA`. **FOUNDATION_INCOMPLETE**.

**Обязательно помнить Jarvis и весь прошлый UNO:** по исходникам `kolakbro5995-cpu/JarvisLab` V21 сверены `AndroidOperationAuthority`, `ConfirmationTicketGate`, STOP/revalidation; переносить только доказанные контрактные требования, не cloud OwnerGate, lab bypass, старые веса, Jarvis BrainPort. Astra R5.3, Grok/Work, LAB/FR/TR, N0 и старые reference журналы сохранены. Neural Language — отдельный проект; ядро/веса UNO не тронуты. `main` и Jarvis не менять.

---


## UPDATE 2026-11-08 — WP-02 atomic reference used+receipt / Jarvis review (current)

**HEAD проверять заново**, snapshot этой записи не фиксирует будущие изменения. Текущий `ActionIntentJournal` получил append-only **v2 phase4 `REFERENCE_USED_RECEIPT`**: reference `used=true` и положительная source-tagged readback-запись лежат в **одном** sync-record; после reopen это восстанавливается без retry. Старый v1 `RECEIPT_RECORDED` всё ещё читается, но `used=false` (не исправлять историю задним числом). `TrustController` в reference+intentJournal режиме отвергает `DurableLedger`, отличный от тестового `InMemoryLedger`, чтобы не прятать вторую независимую дисковую транзакцию.

**HOST_TESTED (точные Git blobs):** 12 прежних journal + 23 typed controller integration + 11 receipt recovery + **12 новых atomic reference regressions** = **58/58 JVM PASS**, повторено три раза. Прогон ограничен 7 исходными Kotlin файлами; full Gradle/preflight после коммитов **НЕ** проводился. Все изменённые Git blob SHA и негативные тесты описаны в [WP-02 атомарная reference запись + проверенный Jarvis источник](implementation/2026-11-08_WP02_ATOMIC_REFERENCE_RECEIPT_JARVIS_REVIEW_R1.md).

**Jarvis учтён строго по исходникам:** только чтение `kolakbro5995-cpu/JarvisLab` `feature/v21-local-offline-runtime-20261101`; просмотрены `AndroidOperationAuthority.kt`, `ConfirmationTicketGate.kt`, `ActionEngine.kt`, `AndroidOperationAuthorityHostTest.kt`. Переносить автоматически их OwnerGate, облачную авторизацию, special lab security, старые веса и многомозговую архитектуру запрещено. В будущий Android trust port учесть one-use ticket/epoch/permission/owner/context revision, STOP и native preflight+readback **после отдельного ревью лицензий и совместимости**. Jarvis НЕ модифицирован.

**Блокеры:** одна reference journal запись **не** даёт полного `A_tx/A_fs` (нет `L,D,P-version,M-ref` transaction), нет реальной trust boundary Android / независимого native OS sample / безопасного local persistent memory / A52 device validation / trained weights. `DenyAllAndroidPort` остаётся. **FOUNDATION_INCOMPLETE**. Neural-Language, UNO F и веса не затронуты.

---


## UPDATE 2026-11-08 — readback receipt R1 (latest)

**Всегда сверить свежий SHA ветки.** Reference `TrustController` теперь отклоняет stale TRUE, если `observedAtNanos` предшествует `nativeAdmittedAtNanos`. В `ActionIntentJournal` добавлена новая append-only фаза `RECEIPT_RECORDED`: после положительного reference readback записываются ID билета, digest предложения, источник, nativeGeneration и время наблюдения; после crash такие байты можно восстановить, а ticket никогда не пересылается автоматически. Сбой sync receipt переводит текущий reference ticket в `MAY_HAVE_EXECUTED`, не в успех. Формат старых двухфазных журналов остаётся читаемым.

**HOST_TESTED:** ровно проверенные Git blobs двух core-файлов и нового теста; `11/11` новых recovery/receipt тестов + `23/23` предыдущих controller integration + `12/12` journal = **46/46 PASS**, ещё 3 повторных прогона тоже PASS. Тест добавлен в общий runner, однако **полный preflight текущей ветки и Android assembly не выполнены**. [Подробности, математика, исходники и доказательные границы](implementation/2026-11-08_WP02_READBACK_RECEIPT_REPLAY_R1.md).

**НЕ считать доверенным OS-результатом:** `RECEIPT_RECORDED` — только записанное source-tagged утверждение fake-native. Нет реального Android owner/permission/readback, `A_tx/A_fs` и единых атомарных `used + receipt + memory`; journal и ledger пока разные хранилища. STOP/OS linearization, boot identity, authentication/anti-rollback и device-gate остаются открыты. `FOUNDATION_INCOMPLETE`.

**Neural Language — самостоятельный проект, его код/веса/ABI не менялись и не переносились в UNO.** Действующее руководство этого репозитория — только `/AGENTS.md`; исторические Astra/R5.3 сохраняются и применяются как математические ограничения, не как утверждённый trained model.

---


## UPDATE 2026-11-08 — typed DispatchAttempt / causal outcome (после WP02 causal bridge)

**Проверять текущий HEAD GitHub; не использовать snapshot SHA из старых разделов.** Новый тип `DispatchAttempt` в `Contracts.kt` и метод `TrustController.dispatchOutcome()` **разделили отказ до native**, однократный **вызов native** (с результатом TRUE/FALSE/UNKNOWN без readback) и **неразрешённое состояние после прошлой попытки**. Прежний `dispatch(): NativeEndpoint` сохранён только как deprecated legacy adapter и всё ещё теряет семантику: его `FALSE` не является достоверным отрицательным OS sample. Новые пути `Verify/L/M` должны использовать типизированную причинную семантику; никакого обучения по отказам до native.

**Изменения:** `Contracts.kt`, `Controller.kt`, 10 новых сценариев в `ActionJournalControllerIntegrationTest.kt`. **Проверка:** совпавшие Git blobs пяти реально компилировавшихся Kotlin-файлов; `kotlinc` + JVM **23/23 integration и 12/12 journal PASS (35/35), 5 повторов**, полный Gradle/Android не проверен. [Подробные формулы, источник Astra/R5.3, тесты и блокеры](implementation/2026-11-08_WP02_TYPED_DISPATCH_OUTCOME_R1.md).

**Важное ограничение:** это **reference-only**, `A_cap/A_tx/A_fs` и реальный Android linearization/owner/permissions/native readback не подтверждены. В приложении по-прежнему `DenyAllAndroidPort`. `FOUNDATION_INCOMPLETE`. Ядро F/веса не менялись.

---


## UPDATE 2026-11-08 — новейший WP-02 causal bridge (после Grok `bfb9acdad6b7bff30c9fae31ff9b3da043b2c665`)

**Действующий HEAD перепроверять непосредственно в GitHub.** После исправлений Grok дополнительно подключён `ActionIntentJournal` к **опциональному reference** `TrustController`, чтобы успешный журнал `PREPARED` предшествовал выдаче билета, а синхронизированный `MAY_HAVE_EXECUTED` предшествовал fake-native dispatch. Если долговечная запись не удалась, вызова native нет. Forged/невыданный `PREPARED` теперь означает pre-dispatch `FALSE`, а не видимость неопределённого OS-эффекта. Старый host-only конструктор без журнала сохранён для совместимости; **реальная Android Activity использует DenyAll Port, интеграции с Android-native по-прежнему нет**.

**Новые испытания:** 13/13 controller+outbox host integration и 12/12 standalone journal host — **25/25 PASS** с побайтово сверенными пятью файлами источников/тестов. Новые integration-тесты зарегистрированы в `AllHostTests.kt`; **полный suite после этих коммитов заново не выполнялся**, Android APK и A52 не проверены. [Математическая трассировка и границы испытаний](implementation/2026-11-08_WP02_CAUSAL_MATH_BRIDGE_R1.md).

**Критическая граница из Astra/R5.3:** `MAY_HAVE_EXECUTED` и полученное `TRUE` от fake port не доказывают независимый результат или causation. `A_cap/A_tx/A_fs`, STOP/OS linearization, атомарное `used+receipt+memory`, owner permissions, boot identity и физическое хранилище ещё не доказаны. Текущий `NativeEndpoint.FALSE` используется также для отказа до native — **до production-интеграции разделить статус допуска и независимый endpoint sample**, чтобы не обучать по отказам как по отрицательным исходам.

**Ядро F, веса и обучение не изменялись**; действующее решение владельца — разрабатывать Android-фундамент без вмешательства в параллельную работу над интеллектуальным ядром. Старые R5.3/Astra/Grok документы и исследования сохранены. `FOUNDATION_INCOMPLETE`.

---


## UPDATE 2026-11-08 — WP-02, текущая инженерная контрольная точка

**Сверяйте живой HEAD**, а не SHA вчерашнего снимка ниже. Изменения после исходной карты: новый `ActionIntentJournal.kt` + `ActionIntentJournalTest.kt`, зарегистрированный в `AllHostTests.kt`; документ `docs/implementation/2026-11-08_WP02_ACTION_INTENT_JOURNAL_HOST_R1.md`. Компонент отдельно HOST_TESTED (12/12), а ограниченный объединённый JVM набор 53/53 PASS, **не полный Gradle/preflight**. Journal фиксирует PREPARED и MAY_HAVE_EXECUTED с append + fd.sync и на восстановлении запрещает автоматический rearm. Он **НЕ подключён** к Android-порту и не предоставляет permissions, consent, native readback, trusted outcomes, Keystore, power-cut proof или работающий нейроинференс. `DenyAllAndroidPort` остаётся обязательным.

**Текущий фронт работ:** вручную собрать и запустить все host/Android checks без GitHub Actions; завершить WP-02 trust boundary и интеграцию journal через настоящий Android owner + permission + STOP + readback; отдельно WP-05 persistent memory. Интеллектуальное ядро/веса **не менять в этой ветке без отдельного решения владельца**. Не объявлять foundation завершённым по этим JVM проверкам.

[Подробный акт WP-02](implementation/2026-11-08_WP02_ACTION_INTENT_JOURNAL_HOST_R1.md).

---

**Снимок:** 2026-11-07, состояние исходников перед созданием этой карты: `f4bc0bd12f8f7b476682a4ff07da85ef419fd6fa`. **ЭТО НЕ ВЕЧНЫЙ HEAD.** Перед работой проверьте свежий SHA рабочей ветки. Этот файл — **маршрут и проверяемый снимок состояния, НЕ отдельный набор действующих правил**. Единственный нормативный источник полномочий — [корневой AGENTS.md](../AGENTS.md) (V3 или более позднее явное решение владельца).

## 0. Если вы только что вошли в проект — прочитайте это прежде, чем писать код

**Репозиторий:** `ivankondral1998-dot/UNO-android-AI-Agent` (**приватный**). **Актуальная ветка интеграции сегодняшних изменений:** `feat/uno-foundation-hardening-20261107`. Ветка-источник WP-01: `feat/uno-production-foundation-20261106` на `ebdfd3f8263592a4906a9829b3b93cadd2256a9c`. `main` при проверке указывала на `27402e7ca2162e5abb52e24c8efc90ee016080cd`; **она НЕ содержит сегодняшних hardening-коммитов**.

При подключении GitHub сначала **явно выберите** `feat/uno-foundation-hardening-20261107`; выдача `main` по умолчанию приведёт к ложному «сегодняшних изменений нет». Убедитесь, что сервис/агент имеет доступ к приватному репозиторию; одна лишь ссылка не выдаёт GitHub permissions.

Начните с `AGENTS.md` в выбранной ветке. Там действующие решения владельца, полномочия, границы и критерии. Затем прочитайте **этот** файл и фактические исходники. Старые [docs/AGENT_START_HERE.md](AGENT_START_HERE.md), [docs/CURRENT_TASK.md](CURRENT_TASK.md), [docs/STATUS.md](STATUS.md) содержат **архивный G4-срез от 02.11.2026** с историческим запретом production-кода; он **заменён** более новым явным решением владельца. Не трактовать исторические заголовки как актуальные.

Для локальной рабочей копии: `git fetch origin feat/uno-foundation-hardening-20261107`, `git switch feat/uno-foundation-hardening-20261107`, `git rev-parse HEAD`, `git status --short`. При работе через GitHub API сначала получите SHA ветки и текущие blob SHA файлов. **Не** трогайте `main`, чужие ветки, историю или оригинальные архивы.

## 1. Каким продуктом занимаемся — решение владельца 07.11.2026

**UNO 1.0:** законченный коммерческий **полностью локальный Android ИИ-агент** с **одной интеллектуальной организацией и общим состоянием**, диалогом/восприятием, локальной точной и семантической памятью, планированием, предложением действий, независимым Android authority, STOP, подтверждениями и отдельным native readback. Первое испытательное устройство — **Samsung Galaxy A52 / Android 14**; архитектура должна оставаться переносимой.

Самообучение весов, FR/TR, plasticity, NCR-EVO, «профессор/ученик», саморастущие связи **НЕ входят в runtime UNO 1.0**: исследования сохранены, но отложены. **Модель, веса, размер, формат, квантование, runtime и лицензия НЕ утверждены**. Production-код на изолированной feature-ветке разрешён. **Нет разрешения** обучать новые production-веса, запускать GitHub Actions, делать merge в `main`, удалять исходники/историю, делать force-push/reset/rebase, публиковать/подписывать APK и выпускать релиз без отдельного решения.

**Не подменять полный продукт:** простой Android UI + `NoWeightsNeuralPort` = диагностический каркас, не настоящий UNO. Не превращать систему в несколько независимых когнитивных моделей или переименованный Jarvis.

## 2. Реальный код — где находится и что означает

| Путь | Состояние на указанном source SHA | Что НЕ доказано |
| --- | --- | --- |
| [android/core/src/main/kotlin/org/unovyra/uno/core/](../android/core/src/main/kotlin/org/unovyra/uno/core/) | `Contracts.kt`, `Controller.kt`, `Memory.kt`, `Scheduler.kt`, `ComputeBudgetGate.kt`, `LabProtocol.kt`, `ProbeMath.kt`, `Measurement.kt`, `ThemePersonalization.kt`. Kotlin reference/host-проверки и отдельные исправления. | Production Android authority, persistent память, нейронный F, проверенная модель. |
| [android/app/src/main/kotlin/org/unovyra/uno/](../android/app/src/main/kotlin/org/unovyra/uno/) | `UnoActivity.kt`, `DeviceLab.kt`, `DeviceProbe.kt`, `LabSystemMetrics.kt`, `SensorLab.kt`; читающая диагностика, ограниченные ручные лабораторные сценарии и UI. | Полноценные разрешённые Android-действия, ASR/TTS, end-to-end интеллект. |
| `android/app/src/main/kotlin/org/unovyra/uno/NeuralWorkerService.kt` | Изолированный **placeholder** без Binder и inference. | Работающая нейросеть и веса. |
| `android/app/src/main/AndroidManifest.xml` | Ноль запрошенных permissions, `allowBackup=false`, `fullBackupContent=false`, `usesCleartextTraffic=false`; neural worker изолирован. | Полная офлайн-безопасность будущих SAF/провайдеров, лицензии, ОС-поведение на A52. |
| `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt` | Общий launcher Kotlin host-тестов; уже включает `FoundationHardeningTest` и `ComputeBudgetGateTest`. | **Полный совместный прогон на HEAD после всех сегодняшних изменений ещё не выполнен.** |
| [android/scripts/](../android/scripts/) | `run_all_preflight.sh`, `host_verify.sh`, `static_contract_check.py`, `test_lab_tools.py`, `adb_collect.py` и инструментальные тесты. | Android Gradle build, устройство и реальные privileged effects. |
| [organism/](../organism/) | Исторические исходники отдельной исследовательской линии; проверить модуль и интеграцию до использования. | Не считать работающим Android UNO по наличию этого каталога. |
| [docs/precode/r5.3/source-package/](precode/r5.3/source-package/) | Архивные математические источники и R5.3 candidate NORMATIVE/01–06, источники Astra/R5.2 и provenance. | Утверждение R5.3 владельцем, работающая модель или реальная device-проверка. |

**Текущая Android-подключённая политика:** `TrustController(DenyAllAndroidPort(), DenyAllLedger())` и `NoWeightsNeuralPort()`. Значит опасные действия **не разрешены**, нейроинференс отсутствует. Код интерфейса не равен реальной реализации.

## 3. Чьё происхождение и где математика

- **Грок:** бумажная архитектура и корректировки минимального организма от 03.11, см. [атрибуцию и математический аудит](audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md). Не утверждайте, что он лично писал все Kotlin/Android-файлы, если нет первичного автора/коммита.
- **ChatGPT Work:** сохранённый `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip`, внутри `06_NON_NORMATIVE_OLD_SCAFFOLD/`: runnable Python B2 reference + Kotlin/Android-основа. В [документе происхождения WP-01](implementation/2026-11-07_WP01_SCAFFOLD_REUSE.md) зафиксировано 67 побайтово сверенных файлов и SHA архива. **Не путать исторический Work package с текущим product runtime**.
- **ChatGPT, изменения 07.11:** Android диагностическая инфраструктура, host-тесты и безопасность foundation, отдельный branch `feat/uno-foundation-hardening-20261107`; см. [аудит FND-01..10](implementation/2026-11-07_FOUNDATION_HARDENING_AUDIT_V1.md) и [новый вычислительный admission-gate](implementation/2026-11-07_COMPUTE_BUDGET_CONTRACT_R1.md).
- **Существенные математические границы:** fixed-mask contraction `CONDITIONAL`, adaptive-mask global contraction `FAIL`; semantic summary `!=` exact recall. Числа параметров/MAC = арифметика, не качество обученной модели и не расход энергии. [Скрипт проверяемой геометрии](audits/2026-11-07/verify_b2_geometry_v1.py).
- **Воспроизведённый дефект старого Python B2 (`MATH-C01`):** `ResourceBudget.charge()` учитывает только MAC: при нулевых лимитах bytes/tokens/ns reference engine всё равно исполнял TEXT tick. Kotlin `ComputeBudgetGate` — **новый неинтегрированный host-tested примитив**, **не патч исторического Python**, не runtime UNO, не физический resource monitor.

**Для Grok:** сравнивайте свои исходные формулы и допущения с реальными Kotlin/Android API **адресно**. Не подменяйте одно другим на основании совпадающих терминов; фиксируйте контрпримеры. При необходимости запросите оригинальный Grok R3: его отдельный исходный blob в текущей проверке не удостоверен.

## 4. Матрица готовности — snapshot, не переносить PASS между HEAD

| Часть | Что реально есть | Доказательство / статус |
| --- | --- | --- |
| WP-01 Android shell и read-only lab | Исходники + старый debug APK со старого коммита, ранее собранный единожды в разрешённом GitHub Actions run `42391092683`; APK SHA-256 `fb49afa67cbb4cc3591d72728da5ae8b649e5560e6d3c754b65ad58c610a728f`. | Старый APK — `ANDROID_BUILT` **только для своего SHA**. APK после hardening и новой математики **не собран**. Samsung A52 **не испытан**. |
| FND-01..10: tickets/STOP/memory/static policy/ADB | Исправлены конкретные ошибки в feature-ветке; fake/native JVM checks | Отдельно **24 Kotlin PASS** (10 базовых + 14 adversarial), **8 Python static fixture PASS + 4 ADB fixture PASS**. Не равняется full repo/Android integration PASS. |
| ComputeBudgetGate | Добавлен в Kotlin core и host launcher, MAC/tokens/peak scratch/deadline/concurrency/one-way STOP | **17/17 host PASS** в независимом прогоне, 10 повторов; full suite updated HEAD **ещё не выполнялся**. Не подключён к F. |
| WP-02 Android authority / actions | Reference controller + deny-all Android Port | **НЕ ГОТОВО:** owner identification, актуальные permissions, подтверждение, atomic STOP/dispatch boundary, durable outbox `PREPARED/UNKNOWN`, независимый Android readback. Важная гонка: `@Synchronized` может ждать выполняющийся native call; STOP не отменяет уже отправленный эффект. |
| WP-03/04 нейронный интеллект | `NoWeightsNeuralPort`, placeholder isolated service; бумажные B2/compact вычисления | **NOT_IMPLEMENTED:** trained/licensed model, frozen weights, measured quality, native inference, единый F, маски с реальным skip. Выбор модели — OWNER_DECISION; training отдельно не разрешён. |
| WP-05 память | `ExactMemory` in-memory, defensive copy и `NOT_FOUND`, запись `VERIFIED_COMPLETION` запрещена generic-пути | **NOT_IMPLEMENTED:** encrypted persistence, WAL, recovery, verified native writer, забывание, миграции и timestamp/boot identity. |
| Голос, сенсоры, память/планирование/цикл | Часть read-only датчиков для лаборатории, UI темы | **NOT_IMPLEMENTED как полный агент:** speech offline, планировщик, фактические действия и реальный end-to-end цикл. |
| Коммерческий релиз | Продуктовая цель утверждена | **NOT RELEASE_READY:** нет модельного и product-gate, device-результата, лицензий, подписи и разрешения на публикацию. |

**Не перепутать:** `HOST_TESTED` отдельной функции ≠ `ANDROID_BUILT` нового HEAD ≠ `DEVICE_VERIFIED`. Полный `android/scripts/run_all_preflight.sh` на текущей ветке и Android Gradle build/lint — **не проверены**. Старый CI run не запускать повторно без разрешения. Отдельные эксперименты на A52 по N0/LAB не доказывают работоспособность нового UNO 1.0.

## 5. Следующее практическое задание для нового агента (особенно Grok)

**Цель ближайшего этапа:** довести foundation до **целостного, проверяемого каркаса**, сохранив цель полного UNO 1.0. «Законченный каркас» НЕ означает ни обученную модель, ни готовый коммерческий агент.

1. **Первым действием:** проверьте текущие SHA и реальный diff к `feat/uno-production-foundation-20261106`; просмотрите `AGENTS.md` и этот handoff, исходники и их тесты. Ничего не удалять, не переписывать старые исследования.
2. **Установите чистый baseline обновлённой ветки:** локально `cd android && bash scripts/run_all_preflight.sh`; затем при **ручной** доступной SDK35/JDK17/Gradle-среде `gradle :core:unoHostTests :app:assembleDebug :app:lintDebug`. Сохраните stdout/stderr, APK SHA, exact HEAD. При ошибке **исправить причину и перепроверить**, не переносить старые PASS. Никаких Actions.
3. **Закройте критические инварианты WP-02:** независимый Android trust boundary; реальная авторизация/permissions/подтверждения; STOP/admission dispatch; идемпотентность и `UNKNOWN/MAY_HAVE_EXECUTED` без слепого повторения; durable transaction/outbox и независимый readback. До доказательства допуска — сохранять deny-all. STOP не отменяет уже выполненное действие ОС.
4. **Согласуйте границы компонентов:** одна организация, типизированные interfaces данных/состояния/решений, точная vs семантическая память, causal/boot identity, error recovery; убрать конфликт семантики `COMPLETE(empty)` в Python B2 vs `NOT_FOUND` в Kotlin **только в новой версии**, не править историю задним числом.
5. **Не терять математику:** любые новые F/маски/selector/ресурсный адмит проверять по исходным формам и контрпримерам; маски обязаны реально **пропускать** дорогую операцию. `ComputeBudgetGate` должен стоять перед encoder/selector/F-kernels лишь при реальной интеграции, с корректной оценкой ресурсов и STOP checkpoints. Пока нет модели — никаких заявлений об энергоэффективности и качестве.
6. **WP-05:** спроектировать и испытать локальное долговечное, защищённое хранение и восстановление сбоев без выдуманной proven-completion; нейросеть не может записать себе доказательство выполнения OS-действия.
7. **A52 gate:** установить **собранный из точного SHA собственный** APK на Samsung A52 / Android 14, записать raw логи, battery/PSS/CPU/thermal, lifecycle/STOP и проверить отсутствие сети, когда появятся соответствующие зависимости. До этого `DEVICE_VERIFIED=FALSE`.

**Приёмка завершённости именно каркаса:** единая трасса `event → shared state → typed proposal → explicit trust decision → outcome/status → memory` с тестируемыми заглушками для ещё не реализованных органов, недопуск эффектов по умолчанию, безопасный STOP и recovery, воспроизводимые host/Android проверки с точными SHA, прозрачный список намеренно **НЕ реализованных** пользовательских функций. Это *архитектурная приёмка*, не доказательство интеллектуальности. Нельзя ставить `FOUNDATION_COMPLETE` до независимого ревью и фактических тестов этих требований.

**Решения владельца, которые не выбирать молча:** конкретная модель/веса/runtime/лицензия, масштаб возможных реальных Android действий и разрешения, обучение весов, релиз/публикация. Дополнительные уточнения — через варианты с последствиями, не самовольным расширением полномочий.

## 6. Дорожная карта и известная ошибка навигации

Используйте [дорожную карту](roadmap/README.md), [мастер-план](roadmap/UNO_1_0_MASTER_PLAN.md) и [структурированный JSON](roadmap/UNO_1_0_PLAN.json); это **план, не доказательство реализации**.

**Проверенный конфликт количеств на 07.11:** мастер-план Markdown содержит **54 task headings / 11 направлений**, JSON содержит **58 tasks / 12 stages**. Все 54 Markdown IDs есть в JSON; четыре дополнительных JSON-задачи — `UI-01-T01..T04` (темы, UI и доступность). Не затирать эти четыре задачи и не представлять источники как идентичные. Рекомендуется согласовать будущий версионированный план с явным diff, **не переписывая** историческую постановку.

## 7. Как завершать следующую сессию

Оставляйте в этом **стабильном** пути `docs/ENGINEERING_HANDOFF.md` обновлённый снимок с датой и первичными доказательствами. **Не писать здесь второй AGENTS.md** и не перепечатывать действующие правила. Для каждого завершённого блока фиксируйте: файлы/коммиты, отдельные `IMPLEMENTED / HOST_TESTED / ANDROID_BUILT / DEVICE_VERIFIED`, воспроизводимые команды, непрошедшие тесты, исходные SHA/логи, что ещё не решено и кто вправе разрешить следующий шаг. Старые отчёты и доказательства сохраняйте.

**Проверка цепочки перед отправкой результата владельцу:** ссылка открывает **именно текущую feature-ветку**, исходные файлы физически существуют, лог соотнесён с SHA, Android build не приписан новому HEAD, архивные G4-правила не перепутаны с действующими. `main` и GitHub Actions не трогать без явного разрешения.

## 8. Снимок 2026-11-07 — Grok, foundation hardening

Ветка: `feat/uno-foundation-hardening-20261107`. База до правок: `7ed1786fec5d829f8ddd2653013a047a7c06c854`.

Исправлено в коде, не в отчёте:
- STOP и отказ до вызова native возвращают FALSE и CANCELLED/DENIED. UNKNOWN только если вызов мог уйти в native.
- Повтор того же билета после UNKNOWN не вызывает native второй раз.
- `recoverAfterProcessDeath` не переотправляет нерешённое.
- Семантическая запись не читается как точный факт. Пустой exact — NOT_FOUND.
- Неактивная маска не запускает тело. Проверено тестом.

Проверки: `cd android && bash scripts/run_all_preflight.sh` → `UNO_LAB_PREFLIGHT_SUCCESS (HOST ONLY; NOT ANDROID_BUILT OR DEVICE_VERIFIED)`. Android SDK в этой среде нет. Сборка APK не выполнялась. На A52 не ставилось.

Статус: **FOUNDATION_INCOMPLETE**. Нет доверенного Android-порта, нет постоянного журнала на устройстве, нет модели и весов, нет native readback, нет проверки на телефоне. Каркас не выдавать за UNO 1.0.
