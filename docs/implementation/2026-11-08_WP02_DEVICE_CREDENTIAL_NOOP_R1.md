# UNO WP-02 — Android device-credential NOOP proof, R1

**Дата:** 2026-11-08. **Действующие правила:** только корневой `/AGENTS.md`. **Ветка:** `feat/uno-foundation-hardening-20261107`. Изменение не относится к Neural Language, обучению весов или реализации нейронного F. **Status:** `IMPLEMENTED` (UI + platform proof request), `HOST_TESTED` (35 JVM cases), `ANDROID_BUILT=FALSE`, `DEVICE_VERIFIED=FALSE`, `FOUNDATION_INCOMPLETE`.

## Реализованная безопасная часть

Текущая `UnoActivity` остаётся offline-лабораторией и сохраняет **`TrustController(DenyAllAndroidPort(), DenyAllLedger())` и `NoWeightsNeuralPort`**. Android-системный эффект не добавлялся.

- `android/app/src/main/kotlin/org/unovyra/uno/OwnerConsentState.kt` — одноразовый процессный state machine: один `Pending` challenge, один `Ready` результат; 128-битный случайный процессный session nonce, различающиеся requestCode без повторения в живом Activity, SHA256 digest/verb/набор требуемых permissions; monotonic 60-s TTL; STOP/revoke/foreground/perms повторно проверяются перед **consumption**, результат с чужим requestCode и повторный callback отбрасываются. Токены **никогда не сохраняются**, прошлый consent не оживает после restart. Любая ошибка означает refusal. State machine не выдаёт `Ticket` и не имеет ссылки на `NativePort`/SQLite dispatch.
- `AndroidDeviceCredentialPlatform.kt` — платформенный `KeyguardManager` для **текущего Android user/profile**, проверяет `isDeviceSecure`, `isDeviceLocked`, `isKeyguardLocked`, активность `Activity`, требуемые `checkSelfPermission`, получает OS `createConfirmDeviceCredentialIntent`, запускает через `Activity.startActivityForResult`. Только `RESULT_OK`, доставленный в `UnoActivity.onActivityResult`, может перевести challenge в `Ready`. Допуск повторно проверяется при ручном расходовании `Ready`.
- `UnoActivity`: две отдельные owner-initiated кнопки «Проверить владельца через экран Android» и «Проверить одноразовое согласие · без действия». **Никаких** memory/OS actions после успешного диагностического consent. STOP вызывает `ownerGate.stop()` вместе с прежними STOP. `onDestroy` уничтожает grant. `onPause` сжигает уже `Ready` (но не незавершённый OS prompt — это нормальный lifecycle при открытии системного диалога).
- Режим **ровно `NOOP`, verb=2**, как в `ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md`; **verb=0 — ABSTAIN, не NOOP**. У запроса нет прав и эффектов, digest от фиксированного `UNO_OWNER_CREDENTIAL_NOOP/1`. Значение `OwnerConsentState.consume()==true` разрешает **только показать диагностическую строку**, а не выполнять Android/native действие. Ни объект `Consent`, ни объект `Ticket` в ядро не передаются.

## Математика и заимствования Jarvis

Сохраняются инварианты источников R5.3, без подмены первоисточников: `ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` (T, ν/e/STOP), `ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` (`M ≠ L ≠ P`, `used+receipt+M-ref`), `ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` (§1: A_cap, owner/cap/consent; §2: closed verb registry и NOOP=2), `ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md` (A_cap/A_tx/A_fs conditional), `NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md`. **Здесь нет доказанной capability containment для реальных эффектов**, так как `NOOP` не имеет native linearization.

Отдельно проверен исходный Jarvis V21 `kolakbro5995-cpu/JarvisLab`, `feature/v21-local-offline-runtime-20261101` @ `9c60f81d81d11a0977be1d36d928a3b5d273bbef`:
- `AndroidOperationAuthority.kt` Git blob `41e464d921d3f4d5c1497b36498d56d333f9135f` — повторный snapshot owner/permissions/context и revocation у native-гейта.
- `ConfirmationTicketGate.kt` Git blob `51a4ff33f0da78113c5fe672982ffb561a7097c7` — one-use, epoch, TTL, invalidation при STOP.
Эти идеи реализованы независимо в маленьком self-contained компоненте. Ничего не копировалось из Jarvis, не переносились его `OwnerGate`, cloud-session, lab-bypass, старые веса и архитектура.

**API verification:** Android Developers, `KeyguardManager.createConfirmDeviceCredentialIntent` — Android API 21+, deprecated с API29, но документирован `startActivityForResult` + `RESULT_OK`; `isDeviceSecure` API23+. Официальная документация: https://developer.android.com/reference/android/app/KeyguardManager . Этот старый путь — **временный кандидат для minSdk26 / targetSdk35**, не одобренный окончательный authentication UX. `BiometricPrompt` / profile-specific authentication требуют дальнейшей оценки, SDK build и A52 device tests; сторонние зависимости не добавлены.

**Ограничения и остаточные угрозы:** Успешный device-credential challenge подтверждает, что ОС приняла учётные данные **Android-пользователя/профиля**; не доказывает отдельную физическую идентичность заявленного «владельца UNO». Caller внутри доверенного Android app process и системный callback являются предпосылками A_cap, а не криптографическим доказательством. Процессный session nonce не antirollback counter. `onActivityResult` и launch могут быть отменены lifecycle; fail closed. `OwnerConsentState` пока не соединён с `AndroidOutcomeStore`, native action gate, owner policy и readback; **никакого privileged action grant нет**. Предельная задержка STOP/OS linearization не измерена. Случай `RESULT_OK` до возобновления Activity обрабатывается без преждевременной проверки `KeyguardManager`; состояние revalidated при `consume`.

## Испытания и исходные файлы

- `OwnerConsentState.kt` — Git blob `42a9846a541285bf4a539f56138f95bcb00c1d23`.
- `AndroidDeviceCredentialPlatform.kt` — Git blob `beef1fc8fe53cefa14f432686656e1c8738dabb9`.
- `android/scripts/owner_gate_host/OwnerConsentStateTest.kt` — Git blob `81a09f32b6daf6393bf7edafd0ebab4029cf2c06`.
- `android/scripts/owner_gate_host/AndroidDeviceCredentialPlatformTest.kt` — Git blob `58256075fb6613b0ffee401aeb3734b37e18e5d9`.
- `android/scripts/owner_gate_host/stubs/*` — test-only Android fake API, **не включается в Android приложение**.
- `android/scripts/test_owner_consent_host.sh` — в `run_all_preflight.sh`; compile against stubs with `kotlinc`, execute both JVM suites.

**Выполнено:** 24/24 process-local state tests (cancelled result, stale code, duplicate OS callback, invalid digest/verb, changed permission scope, STOP, expired grant, monotonic regression, lock/foreground loss) + 11/11 Android adapter host-stub tests (secure/locked, missing permission, foreground, null credential intent, OS throw, monotonic platform time) = **35/35 PASS**, конкретные Kotlin исходники побайтово совпадают с GitHub.

**Не выполнено:** реальный `Android SDK assemble`, Android instrumentation, OS-credential dialog on A52, tests in work-profile / screen-off / device-credential absence, полноценный полный host-preflight **на новом HEAD**, пользовательское устройство, native readback, реальное Android полномочие или выпуск APK. GitHub Actions не запускались, `main` и Jarvis не изменены.

## Следующий проверяемый этап

После SDK и A52 lifecycle испытаний оформить **строго один разрешённый локальный контракт** (например `CREATE_LOCAL_NOTE` с отдельной explicit confirmation, content readback и SQLite transaction), привязать consent к exact `Proposal` и закрыть on-device STOP/unknown/restart матрицу. **Не** открывать каталог остальных эффектов и не выдавать `NOOP` за законченный Android trusted controller. Отдельная модель/веса/Neural Language не затрагиваются без нового разрешения.
