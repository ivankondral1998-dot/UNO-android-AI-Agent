# UNO 1.0 — WP-02: причинный контракт, долговечный intent и пределы доказательства

**Дата:** 2026-11-08. **Версия документа:** WP02-CAUSAL-BRIDGE-R1. **Действующие полномочия — только корневой `/AGENTS.md`.** Это инженерная трассировка исходной математики на конкретный код, не утверждение новой нормативной модели, весов или runtime.

**Статус:** часть reference-контроллера `IMPLEMENTED + HOST_TESTED` на JVM; Android authority, полноценный атомарный журнал завершения, независимый native readback, полная сборка APK, испытания A52 — **НЕ выполнены**. `FOUNDATION_INCOMPLETE`.

## Первичные источники, не заменять пересказом

1. `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md`, §§1, 5–7: состояние `X=(w,τ,S,T,R)`, `T=(ν,e,stop,owner,cap,L,D)`, causal clock, один outbox на шаг, приоритеты STOP/REVOKE, admission/linearization, time semantics `CURRENT_ALL/OBSERVED_ALL`, действительные terminal status.
2. `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md`, §§1, 4–5: `M ≠ L ≠ P`, происхождение записей, долговечные `PREPARED/SENT`, `used+receipt+M-ref` в единой trusted transaction; невозможность точного восстановления без complete causal record. Online P для UNO 1.0 **отложено решением владельца**.
3. `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md`, §§1–2, 6: допущения `A_cap/A_tx/A_fs`, полномочия и STOP вне нейросети, закрытый каталог эффектов, явная system permission/consent/identity, readback и бюджет.
4. `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md`, Т6/Т7: гарантия no unauthorized effect **условна** на trust assumptions; receipt ≠ доказательство causal attribution, power-cut и anti-rollback не доказаны.
5. `docs/precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md` и `03_CONSOLIDATED_SUBSYSTEM_CONTRACTS.md`: fixed-mask условная оценка, adaptive counterexample, `RetrieveExact ≠ RetrieveSemantic`, STOP и full-system contracts.
6. `docs/audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md`: независимая проверка счётчиков/масок, ошибки Python B2 budget/empty memory, provenance Grok paper против Work scaffold. Не подменять исследовательскую формулу наличием Kotlin API.
7. `docs/implementation/2026-11-08_WP02_ACTION_INTENT_JOURNAL_HOST_R1.md`: предыдущая реализация standalone журнала. Исходный исторический документ описывает состояние **до нынешнего интеграционного шага**.

Новая feature-ветка использует данные источники как **ограничения**; исторические формулы, исследования, SHA-инвентари, Astra/R5.3 и B2 Python reference не исправлялись задним числом.

## Формализованное частичное свойство и реализация

Обозначения: `J_P(t)` — успешно синхронизированная запись `PREPARED` для ticket `t`; `J_M(t)` — успешно синхронизированная запись `MAY_HAVE_EXECUTED`; `N(t)` — вход в `NativePort.dispatch(t)`. В **тестовой ветке с явно переданным `ActionIntentJournal`** выполняется проверяемый по коду порядок:

```
ConsentDigestCheck(t) ∧ active(epoch,STOP) →
  J_P(t) → reference-ledger.prepare(t) → ticket issued
  → immutable proposal digest check → J_M(t) → STOP recheck
  → [optional] N(t) → native endpoint/UNKNOWN
```

- Если `J_P` не записан, билет не выдаётся. Отказ `reference-ledger.prepare` **после** `J_P` может оставить orphan `PREPARED`; это умышленно консервативно и не исполняет ОС-эффект.
- Если `J_M` не записан или STOP уже установлен при последней проверке, `N` не вызывается. Журнал и контроллер используют разные STOP-источники; production Android должен свести допуск в одну доверенную границу.
- Повторная передача issued ticket после `N` или после `UNKNOWN` не вызывает `N` ещё раз. После перезапуска `J_M` не разрешает `arm` прежнего ticket. Восстановление не равно успешному выполнению и не допускает слепой retry.
- `FALSE` на пути до `N` означает **отказ в отправке**, но это НЕ independently sampled `NativeEndpoint.FALSE` для endpoint-предиката. Текущий ABI технически использует один enum для двух смыслов: **семантическая коллизия остаётся blocker для production API**. Строго разделить `DENIED_PRE_DISPATCH` и `OBSERVED_FALSE` в будущей Android границе; не обучать по pre-dispatch FALSE как по отрицательному эффекту.
- `UNKNOWN` после возможного `N`, exception или crash означает неизвестный исход/возможный side effect. `COMMITTED` не выводится из `J_M`, результата вызова или сообщения модели.
- STOP немедленно устанавливает latch, но `TrustController.dispatch()` держит монитор через native call. Между последней проверкой и физическим OS call остаётся временное окно. **Ни bounded STOP latency, ни atomic OS linearization, ни hard power-cut durability этим JVM-кодом не доказаны.**

**Это частичное свойство обусловлено** корректной однопроцессной serial execution, успешным `FileDescriptor.sync()`, текущей файловой системой и целостностью reference fake port. **Нижеобозначенные допущения остаются `SPECIFIED_UNTESTED`:** `A_cap`, `A_tx`, `A_fs`, real Android owner consent, generation/boot uniqueness, independent readback, atomic receipt/used/memory transaction. SHA-256 hash-chain журнала не является authentication/MAC/anti-rollback; no automatic journal compaction.

## Изменённые файлы

- `android/core/src/main/kotlin/org/unovyra/uno/core/Controller.kt`: опциональная явная инъекция `intentJournal` в reference controller; `prepare` долговечно фиксирует намерение до выдачи билета, `dispatch` требует успешный `arm` до `NativePort.dispatch`; пред-native invalid/forged `PREPARED` возвращает `FALSE`, не имитируя возможную отправку. Без указанного журнала старый reference/fake-only путь сохранён для обратной совместимости тестов.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionJournalControllerIntegrationTest.kt`: **13** integration host cases, включая crash/replay, foreign/not-issued ticket, STOP, native exception, digest tamper, orphan `PREPARED`, durable phase ordering.
- `android/core/src/test/kotlin/org/unovyra/uno/core/FoundationHardeningTest.kt`: обновлён ожидаемый pre-native denial для поддельного issued ticket.
- `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt`: добавлен integration test runner.

**Тестовые свидетельства:** `kotlinc-jvm 1.9.0`, OpenJDK 21, 13/13 новых controller/journal integration тестов + 12/12 существующих standalone journal тестов = **25/25 HOST PASS**. Для этого прогона **все четыре core/test файла**, реально подаваемые в компилятор, должны быть побайтово проверены с GitHub; SHA Git blobs:

- `Controller.kt`: `619c5e33c19594c782444cd99e27dd7e64379d5e`.
- `ActionIntentJournal.kt`: `5dd300ae5b7a30a9c577eb218153d2453dd6a534`.
- `Contracts.kt`: `ecd3d3e6ae5f677d817223e8dcbb6e086f4b30d8`.
- `ActionJournalControllerIntegrationTest.kt`: `1e497120a374f1c547898f24119f7af4f79e0a72`.
- `ActionIntentJournalTest.kt`: `5434d3986bb214ee82e88c6b23a65b3bbda85118`.

Компиляция и 25 тестов **не** заменяют полный `cd android && bash scripts/run_all_preflight.sh`, Gradle Android assemble/lint, независимую device аттестацию или физический fault-injection. После этих изменений новая APK не собрана. GitHub Actions не запускались.

## Обязательное продолжение (в тех же математических границах)

1. Android trusted authority: owner identity/profile, permissions на момент отправки, exact consent, one-time ticket/nonce/boot/session, bounded effect registry, native linearization + независимый readback. Не включать privileged port до интеграционных отрицательных тестов.
2. Trusted persistent `L,D,used,receipt`: настоящий transactional backend с восстановлением ambiguous outcomes; `A_tx/A_fs` подтверждать fault-injection и OS, не экстраполировать `fd.sync` в гарантированный power-cut.
3. Точная память `RetrieveExact` и provenance/consent vs семантическая `SUMMARY_ONLY`; `CURRENT_ALL` не подменять набором разновременных TRUE. Память и prediction P не могут давать права.
4. ComputeBudgetGate применять **перед** реально дорогой модельной операцией, а не после. Historical `MATH-C01` остаётся FAIL; ресурсные MAC/байты/токены ≠ энергетика устройства. Fixed-mask contraction только `CONDITIONAL`; hard adaptive selector глобально не доказан. Для 16 блоков нельзя смешивать 241 cyclic prefix masks и 65 535 arbitrary masks.
5. F/веса, ASR/WAKE, лицензии, ресурсный envelope и полный end-to-end цикл — отдельные ещё не реализованные gates. Изменения модели/весов и обучение не выполнялись.

**Итог:** доказанный локальный порядок «намерение на диске → arm до fake-native» и запрет ряда неверных состояний; **не** законченная Android-защита и **не** готовый UNO 1.0.
