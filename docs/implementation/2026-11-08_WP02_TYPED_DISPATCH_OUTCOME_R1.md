# UNO 1.0 — WP-02: типизированный причинный результат dispatch (R1)

**Дата:** 08.11.2026. **Статус:** `IMPLEMENTED + HOST_TESTED` для JVM reference controller и fake-native; `ANDROID_BUILT=FALSE` для этого изменения, `DEVICE_VERIFIED=FALSE`, `FOUNDATION_INCOMPLETE`. Владелец ядра и весов работает над ними отдельно: этот change не затрагивает neural F, модель, обучение или model selection.

**Действующие правила — только корневой [AGENTS.md](../../AGENTS.md).** Данный документ — evidence/трассировка, не второй набор полномочий.

## Источники: что проверяет математика и чего она НЕ доказывает

- [ASTRA 01 — полный цикл, causal clock и endpoint evidence](../precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md), §§1,6–7: выход `δ`, outbox, `STOP`, отдельное время/источник наблюдения, условия `CURRENT_ALL`. Запись команды или возврат из native != доказательство успеха.
- [ASTRA 04 — память, исходы и восстановление](../precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md), §§1,4–5: `M` (семантическое представление) ≠ `L` (trusted outcome journal) ≠ `P` (предсказание). `UNKNOWN` не превращается в `VERIFIED_COMPLETION`; `used+receipt+memory` требуют атомарной доверенной транзакции.
- [ASTRA 05 — capability boundary](../precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md), §§1–2: proof of containment требует **A_cap/A_tx/A_fs**, owner confirmation/permissions, STOP и native readback; `NativePort` fake не является Android authority.
- [ASTRA 08 — пределы формальных доказательств](../precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md), T6–T7: receipt не доказывает causal attribution или физический exactly-once effect.
- [R5.3 formal corrections](../precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md), trust/STOP: условный proof только при live capability и линейризованном dispatch; отсутствие полного Android-внедрения не делает инварианты безусловными.
- [WP-02 causal bridge R1](2026-11-08_WP02_CAUSAL_MATH_BRIDGE_R1.md): предыдущая интеграция `J_P → J_M → native`, остающаяся reference-only.

## Исправленное разделение причинных событий

**До:** `TrustController.dispatch(): NativeEndpoint` возвращал `FALSE` и при отказе **до вызова native**, и при возврате `FALSE` **после вызова**. По одному `FALSE` невозможно узнать, был ли native вызван. Использовать такой enum в будущих outcome labels, памяти или обучении — ошибка причинности.

**Сейчас:** `DispatchAttempt` — отдельный тип в `Contracts.kt`, выдаваемый `TrustController.dispatchOutcome()`:

| Тип | Что утверждается | Чего НЕ утверждает |
| --- | --- | --- |
| `Rejected(DispatchRejection)` | **Этот вызов** не вошёл в `NativePort.dispatch`. Причина: non-issued/forged/closed/STOP/deadline/digest/journal. | Нет отрицательного OS endpoint label, нет доказательства отсутствия **прошлых** эффектов. |
| `Invoked(NativeEndpoint.TRUE/FALSE/UNKNOWN)` | **Этот вызов** достиг reference `NativePort.dispatch` один раз и вернул указанный status; `UNKNOWN` также может означать исключение из callback. | Не доказывает, что ОС применила эффект, что его совершил UNO, что он остаётся истинным «сейчас», или что native readback уже прошёл. |
| `Unresolved` | Повторная отправка не выполняется: билет был ранее диспетчеризован или его судьба не восстановлена. | Не доказательство факта отправки или успеха любого конкретного OS effect. |

**Legacy-метод `dispatch(): NativeEndpoint` сохранён для существующих host tests и помечен `@Deprecated`.** Он преобразует `Rejected → FALSE`, `Invoked → nativeReturn`, `Unresolved → UNKNOWN`, то есть **сознательно теряет различие**. Любые новые компоненты, особенно `L/M/Verify` и Android trusted controller, должны использовать типизированный метод; legacy native return нельзя считать обучающим label. Удаление legacy ABI без нового решения и проверки существующих клиентов не выполнялось.

`readbackAndCommit` остался отдельным путём, только валидный независимый `NativeEvidence(TRUE, generation/time/source/ticket)` может инициировать commit. Типизированный dispatch не ослабляет этот барьер. В текущей реализации все эти проверки выполняются на fake-native и in-memory ledger; **не переносить доказательство на Android**.

## Проверенные файлы и host tests

- `android/core/src/main/kotlin/org/unovyra/uno/core/Contracts.kt` — Git blob `2422bafb5f9486b87247e2073e1dcbf241a851a5`.
- `android/core/src/main/kotlin/org/unovyra/uno/core/Controller.kt` — Git blob `44403764997831d425797607ee605216a721aa5a`.
- `android/core/src/main/kotlin/org/unovyra/uno/core/ActionIntentJournal.kt` — Git blob `5dd300ae5b7a30a9c577eb218153d2453dd6a534` (не изменён).
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionJournalControllerIntegrationTest.kt` — Git blob `c016fb9851462c6096b51feb147cde344eef775c`.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionIntentJournalTest.kt` — Git blob `5434d3986bb214ee82e88c6b23a65b3bbda85118` (не изменён).

На локальной JVM **точно эти файлы** компилировались `kotlinc 1.9.0 / OpenJDK21`: **23/23** integration + **12/12** journal = **35/35 PASS**, повторный запуск с тем же JAR **5/5 полных прогонов PASS**. 10 новых integration-тестов адресно проверяют typed refusal/forgery/journal STOP/expired/digest, `Invoked(FALSE)` vs `Rejected`, `Invoked(TRUE)` без ложного readback, `UNKNOWN`/no retry, crash/Unresolved. Старые 13 integration-тестов сохранены. Предупреждения Kotlin по `@Deprecated` ожидаемы и не равны ошибкам компиляции.

**Не проверено:** полный `android/scripts/run_all_preflight.sh` для нового HEAD, Android SDK Gradle/lint, целостность готового APK, device A52, crash during fsync, real Android readback, physical/OS STOP race. GitHub Actions не запускались. `main` не изменён.

## Остаточные блокеры — не утверждать FOUNDATION_COMPLETE

1. **A_cap / trusted OS authority:** реальная идентификация владельца и permissions, permission denial, exact confirmation и узкий allowlisted native executor вне worker. Активный Android runtime всё ещё `DenyAllAndroidPort` и `NoWeightsNeuralPort`.
2. **A_tx/A_fs:** `ActionIntentJournal` append+sync и hash chain **не равны** проверенному SQLite transactional backend / authentication / Keystore / анти-rollback. `L,D,used,receipt,M-ref` не коммитятся атомарно.
3. **STOP/linearization:** reference callback под `@Synchronized` может задержать STOP до выхода native; проверка STOP перед callback не даёт атомарной OS linearization. Это **ещё открытый блокер**, даже при успехе JVM-тестов.
4. **Causal outcome:** `NativeEndpoint.TRUE` и `readback(TRUE)` должны быть интерпретированы с target time и источником; `CURRENT_ALL` не доказать набором асинхронных samples. Непроверенный outcome не попадает в trusted completion.
5. **Модель/маски/ресурсы:** neural F и веса не выбраны; `ComputeBudgetGate` не интегрирован с реальными kernels. Фиксированная маска допускает лишь условную оценку `c_M`, adaptive hard selector — известный контрпример; MAC ≠ joules/device. Исторический Python budget MATH-C01 остаётся FAIL.

**Следующий WP-02 этап:** создать узкий Android trusted adapter с явной permission/owner проверкой, отдельным от neural agent, и fault-injection для durable commit + readback; не включать privileged effects до этой приёмки.
