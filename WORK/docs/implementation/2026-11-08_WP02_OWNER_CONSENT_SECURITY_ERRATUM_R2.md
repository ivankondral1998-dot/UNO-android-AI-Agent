# UNO WP-02 — OWNER CONSENT SECURITY ERRATUM R2

**Дата:** 08.11.2026. **Статус:** три воспроизведённых в JVM дефекта исправлены в рабочей ветке; `PROVEN_LOCAL` только для Java/Kotlin process-state fixtures. **`ANDROID_BUILT=FALSE`, `DEVICE_VERIFIED=FALSE`, `FOUNDATION_INCOMPLETE`.**

**Полномочия:** только корневой `/AGENTS.md`; оригиналы Astra/R5.3, Grok, Jarvis, архивы исследований и предыдущий `2026-11-08_WP02_DEVICE_CREDENTIAL_NOOP_R1.md` сохранены без переписывания. Это версионированная коррекция, а не обновление математической модели, весов или требований к Neural Language.

## Исправленные дефекты и независимые контрпримеры

**SEC-01: Scope escalation в диагностическом подтверждении.** Старый `OwnerConsentState.begin()` проверял только `Scope.valid()` с `verb in 0..23`. Kotlin-host пример `Scope(15, "a".repeat(64), emptySet())` мог пройти `begin`, OS-result callback и `consume`, несмотря на UI, обещающий **только NOOP**. Привилегированный Android port тогда отсутствовал; поэтому это **реальный defect policy-binding, а не доказанный побочный эффект ОС**. Исправление: `begin` и `consume` принимают только точный `OwnerConsentState.diagnosticNoopScope()`: Astra verb **2 (NOOP)**, SHA-256 от фиксированного `UNO_OWNER_CREDENTIAL_NOOP/1`, пустой набор permission. Нет произвольных action grants и model-supplied scopes; будущим verbs потребуется отдельная review/authority и owner policy.

**SEC-02: Повтор идентификатора системного запроса при пересоздании Activity/gate.** Старый каждый `OwnerConsentState` начинал с requestCode `0x4100`. В Kotlin-host тесте два последовательных экземпляра выдавали один code, а `RESULT_OK` с идентификатором прежнего экземпляра принимался новым pending request. Исправление: process-wide `AtomicInteger` + случайный CSPRNG offset в закрытом диапазоне `0x4100..0x7fef`; в одном процессе номера **не повторяются** до исчерпания диапазона, далее отказ. Новый adversarial тест проверяет stale callback через два экземпляра и 64 конкурентных экземпляра. **Оставшееся ограничение:** Android requestCode всего ~14 бит на этот диапазон и не является криптографической привязкой; между **разными запусками процесса** случайное совпадение возможно. OS delivery/caller identity, device reboot и Activity recreation требуют instrumentation/A52. Не объявлять детерминистический no-replay при process death.

**SEC-03: UI text не был привязан к семантике согласия.** До исправления `begin(scope=NOOP, exactDescription="Разрешить удалить файл?")` мог запустить credential flow. При текущем фиксированном UI это не давало ОС-эффекта, но инвариант точного согласия не enforced в policy. Исправление: единая `OwnerConsentState.DIAGNOSTIC_DESCRIPTION`, сравниваемая **на равенство** в `begin`, использованная в `UnoActivity`. Нельзя подставить сообщение другой операции. Текст, как и consent, не является proof of native dispatch.

**Отдельная исправленная ошибка утверждения о тестах:** предыдущие fake-platform сценарии с `permissionsGranted=false` при `emptySet()` не являются доказательством реальной Android permission revocation. У диагностического NOOP **нет** требуемых permissions; в Android `emptySet().all {...}` возвращает true. Названия этих тестов исправлены: они доказывают реакцию на принудительный отказ тестовой платформы, а не работающую authorization конкретного Android-эффекта.

## Источники/трассировка

- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md`: `T=(ν,e,stop,owner,cap,L,D)`, причинность/STOP.
- `.../ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md`: закрытая схема verbs, **0 ABSTAIN, 1 CLARIFY, 2 NOOP**, `A_cap`, актуальные permissions, exact proposal digest, one-use, independent readback.
- `.../ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md`: история/semantic memory не даёт permission; `M ≠ L ≠ P`.
- `docs/precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md`: STOP/linearization, только условная теорема с `A_cap/A_tx/A_fs`, возможная неопределённость/реальное Android испытание; контрпример adaptive selector оставлен без изменений.
- `docs/audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md`: MATH-C01 FAIL для полного бюджета Python B2, MATH-C05 Android trust BLOCKER; их этот patch **не закрывает**.
- **Jarvis только read:** `kolakbro5995-cpu/JarvisLab`, branch `feature/v21-local-offline-runtime-20261101` SHA `9c60f81d81d11a0977be1d36d928a3b5d273bbef`, `AndroidOperationAuthority.kt` blob `41e464d921d3f4d5c1497b36498d56d333f9135f`, `ConfirmationTicketGate.kt` blob `51a4ff33f0da78113c5fe672982ffb561a7097c7`, `AndroidOperationAuthorityHostTest.kt` blob `5d8a8424655ed085976bcd5f7c90f1801b67e179`. Заимствованы **только требования** context/permission/epoch revalidation и STOP; legacy OwnerGate и lab bypass из Jarvis не переносились.
- Android Keyguard reference https://developer.android.com/reference/android/app/KeyguardManager: `createConfirmDeviceCredentialIntent` deprecated API29, `RESULT_OK` после фактической проверки Android-профиля; рекомендован BiometricPrompt. Ни один вариант не доказывает индивидуального владельца UNO без user/profile policy.

## Воспроизводимость и границы

**Modified files:**
- `android/app/src/main/kotlin/org/unovyra/uno/OwnerConsentState.kt` Git blob `bb8c8d9d8f2abdddafec05fe836a0e1ca2028cc4`.
- `android/app/src/main/kotlin/org/unovyra/uno/UnoActivity.kt` Git blob `a0d9fd894cb4ad633ed6116e9e454d18ccdbca5b`.
- `android/scripts/owner_gate_host/OwnerConsentStateTest.kt` Git blob `6b6a1bfaa02cfceb964ae3ec53b37b95dba67d41`.
- Android platform adapter/stubs/test runner сохранены и компилировались без изменения.

**Actual local execution:** `kotlinc-jvm` + JRE, 31/31 owner-state + 11/11 Android adapter stub = **42/42 PASS**, повторно в пяти отдельных JVM-процессах. Regression tests включают запрет verb15, чужого digest, лишних permissions, misleading prompt, точное NOOP описание, stale code across instances и uniqueness 64 concurrent instances. Предыдущий reference core JAR 12+23+11+12 = **58/58 PASS** отдельно. SQLite SQL 14/14 (host CPython sqlite3), inspector 11/11 (host stubs) повторно PASS; итого **125 тестовых случаев разных уровней**, **НЕ 125 реальных Android интеграций**.

**NOT RUN:** общий `cd android && bash scripts/run_all_preflight.sh` для полного свежего репозитория, Gradle APK/lint через Android SDK, физическое устройство A52, Keyguard OS dialog, stored outcome ↔ one-use owner ticket ↔ trusted native OS effect/readback, STOP/dispatch linearization, disk loss/power-cut. Основной действующий порт по-прежнему `DenyAllAndroidPort()+DenyAllLedger()`, модель `NoWeightsNeuralPort`. Нет обученных весов/единого рабочего F. `main`, Jarvis, Neural Language не менялись. GitHub Actions не запускались.

## Следующий безопасный переход

Сначала **собрать Android APK без GitHub Actions** с реальным SDK, подтвердить вызов и lifecycle Keyguard на A52, STOP во время challenge и после, тесты при блокировке и revoke. Затем разрешённый владельцем узкий app-private effect с точной typed schema и проверяемым native readback через **одну** SQLite transaction и fresh session/owner preflight. Ни boolean из этого diagnostic gate, ни stored `REFERENCE_READBACK_CLAIM` не являются правом на OS action или `VERIFIED_COMPLETION`.
