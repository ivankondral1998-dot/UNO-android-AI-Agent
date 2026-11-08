# UNO / WP-02 — единая запись reference used+receipt; сверка Jarvis V21 (R1)

**Дата:** 2026-11-08. **Действующие полномочия:** только корневой `/AGENTS.md`. **Ветка:** `feat/uno-foundation-hardening-20261107`. Отдельные источники Astra/Grok/Jarvis не изменены. Производственные веса, ядро F, Neural Language и приложения Jarvis не изменялись.

## 1. Что реализовано (узкий, проверяемый результат)

Ранее reference `TrustController.readbackAndCommit()` после положительной проверки вызывал `ledger.commit(t,evidence)`, затем **отдельный** `ActionIntentJournal.recordReadbackClaim(...)`. Это две логические фиксации: crash между ними делает состояние неоднозначным. `InMemoryLedger` фактически не хранит данные после смерти процесса.

Новый **reference-only** путь, только когда передан `ActionIntentJournal`:

- До native: `PREPARED` → `MAY_HAVE_EXECUTED` в append-only журнале с `fd.sync()` до вызова fake `NativePort`. Старые негативные safety-contracts сохраняются.
- После отдельно вызванного reference `readback(TRUE)`, проверок ticket/nonce/epoch/STOP/времени/источника и проверки transient `InMemoryLedger.commit`: **одна** append+sync запись v2 phase 4 `REFERENCE_USED_RECEIPT`. В том же бинарном record находятся ticket ID, digest предложения, идентификатор источника, generation, observedAtNanos, typed TRUE и `used=1`. Обновление in-memory `Ticket.used` происходит после синхронизации; сам объект не является долговечной базой.
- Recovery знает о новой фазе: `Row.used=true`, положительный source-tagged receipt, `Row.recovered=true`; уже выданный ticket не допускается к повторному `arm` и native. При повреждении/усечении или неверном маркере `used` — fail-closed, **без** усечения/ремонта; даже пересчитанная корректная SHA цепочка не спасает семантически недопустимый record.
- Версия 1 и фаза 3 `RECEIPT_RECORDED` читаются как историческое **свидетельство без durable used**: `used=false`. Исторический receipt не повышается до phase 4 автоматически. Старый reader не поддерживает phase4/v2 и должен отказать, а не молча даунгрейдить статус.
- С journal подключённым и `ledger !is InMemoryLedger` `readbackAndCommit` **fail-closed**: запрещено вновь разнести согласование между двумя потенциально постоянными хранилищами. `InMemoryLedger.commit` при этом только проверяет локальный билет и ничего на диск не пишет. Не выдавать это за полноценную реализацию production `DurableLedger`.
- Ранее созданный `internal recordReadbackClaim` с phase 3 сохранён **только для совместимости исторического формата и отдельных тестов**; он не создаёт used=true.

**Доказуемое на локальном JVM уровне (PROVEN_LOCAL при допущениях ниже):** внутри одного нового phase4 record `used` и предъявленная reference-контроллером положительная readback-запись сохраняются/восстанавливаются вместе. Нет состояния phase4 с восстановленным `used=true` и отсутствующим receipt — parser откажет. Отказ до native не становится `NativeEndpoint.FALSE` как будто это проверенный исход ОС: новый API `DispatchAttempt` по-прежнему используется отдельно.

## 2. Что не доказано и НЕ заявляется

- **Это НЕ A_tx всей UNO.** Не записаны в одну транзакцию `L,D,P-version,M-ref`, полноценный reason/event-state, источник данных памяти или фактическая Android-сессия. Общего persistent memory backend нет; `Row.used` является только reference terminal bit.
- **Это НЕ доверенный OS readback:** `NativePort` в этой ветке fake, source-tag и timestamp могут быть подделаны кодом того же модуля; `internal` не является системной границей безопасности. Никакой native generation не подтверждён Android. `RECEIPT` также не доказывает causal attribution или нынешний эффект.
- **Это НЕ A_fs и anti-rollback:** `FileDescriptor.sync()` был вызван в JVM тестах, но power-cut, filesystem metadata, Keystore/MAC, malicious byte replacement, disk-full, concurrent-process fault injection и Android storage behaviour не испытаны. SHA-256 hash chain без ключа не является аутентификацией. 4096 tickets и отсутствие безопасной ротации остаются лимитом.
- **STOP:** event до OS linearization нельзя отправлять; после уже начатого эффекта STOP его не отменяет. Reference `@Synchronized native.dispatch` не доказывает гонки OS linearization и задержку STOP на Android.
- **Math:** fixed common mask `c_M` условен; hard adaptive selector не globally contractive; `M` semantic/non-injective не exact; MAC != joules/PSS; веса/ширины/ABI не выбраны. Этот WP-02 код **не** меняет математику F и не объявляет R5.3 approved baseline.

## 3. Первичные математические источники

- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` — causal clock, state `T=(ν,e,stop,owner,cap,L,D)`, outbox, STOP priority, receipt time/endpoint semantics.
- `.../ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` — exact memory/provenance, `M ≠ L ≠ P`, `used+receipt+P-version+M-ref` в одном trusted commit; rollback/cross-boot limits.
- `.../ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` — `A_cap`, permission/owner gate, Android authority and resource constraints.
- `.../ASTRA_CURRENT/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md` — assumptions `A_tx`, replay/censoring proof boundaries, no universally proven exactly-once physical action.
- `docs/precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md`, `03_CONSOLIDATED_SUBSYSTEM_CONTRACTS.md`; `docs/audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md` — later source corrections and independent math audit. Оригиналы не редактировать.

## 4. Проверенная переработка идей Jarvis (только чтение)

**Jarvis source:** private `kolakbro5995-cpu/JarvisLab`, `feature/v21-local-offline-runtime-20261101`, snapshot SHA `9c60f81d81d11a0977be1d36d928a3b5d273bbef`. Отдельный проект, только read; лицензии/происхождение проверить перед любым реальным заимствованием.

- `app/src/main/java/io/jarvis/mobile/agent/AndroidOperationAuthority.kt` (Git blob `41e464d921d3f4d5c1497b36498d56d333f9135f`) — однопроцессный lease, Android permission snapshot, principal/target/context revision, STOP epoch, revalidateNative; полезные требования для будущего UNO trusted boundary. **Не** переносить `OwnerGate`, session токены, special lab mode или сам executor как готовую UNO trust реализацию.
- `ConfirmationTicketGate.kt` (Git blob `51a4ff33f0da78113c5fe672982ffb561a7097c7`) — одноразовая привязка подтверждения к action/epoch/context/window revision, TTL и revoke при STOP. Это источник тестовых негативных сценариев, а не готовый durable ticket.
- `ActionEngine.kt` (Git blob `7d3f8ee715d916b9baef9ea8e82e95766349cb3e`) — Android API + ad hoc native readback для отдельных эффектов. Возвращаемый текст `request sent` и callback не должны автоматически означать `VERIFIED_COMPLETION` в UNO.
- `tests/kotlin/AndroidOperationAuthorityHostTest.kt` (Git blob `5d8a8424655ed085976bcd5f7c90f1801b67e179`) — адресные негативные сценарии revoked permissions, changed target, STOP after consent, native revalidation. Это host fixtures Jarvis, **не** пройденные UNO тесты.

Применён **только принцип:** explicit owner/permission/consent/STOP должен жить в доверенном Android-контуре и повторно проверяться непосредственно перед действием. Этот этап WP-02 **не** добавлял Android 권 полномочий, не менял Jarvis и не переносил его веса.

## 5. Воспроизводимость именно изменённых файлов

- `android/core/src/main/kotlin/org/unovyra/uno/core/ActionIntentJournal.kt` — Git blob `7ad7482bb2aef8d6228e94db98f13ea2df42ce78`.
- `android/core/src/main/kotlin/org/unovyra/uno/core/Controller.kt` — Git blob `c8dc3a4ba2e33404f55ac21d91310963017ce823`.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionReceiptRecoveryTest.kt` — Git blob `ba7b4c300597af9febcfe8b8639610ef9fcbc33e`.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionAtomicReferenceCommitTest.kt` — Git blob `63fd32b3066e5cb2de94a4bb245c51830e858daf` — 12 new regression cases.
- `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt` — добавлен тест в общий runner.

**Host proof:** `kotlinc-jvm` + Java, семь source/test Kotlin файлов: `ActionIntentJournalTest` 12/12, `ActionJournalControllerIntegrationTest` 23/23, `ActionReceiptRecoveryTest` 11/11, `ActionAtomicReferenceCommitTest` 12/12 = **58/58 PASS**. Выполнены **3 последовательных повтора всех 58 сценариев**, каждый PASS. Проверены v1-v2 replay, physical-byte tamper with recomputed unkeyed SHA, truncated v2 write, unknown/STOP, no redispatch. Все четыре слоя ограничены JVM reference/fake native.

**NOT RUN:** весь `cd android && bash scripts/run_all_preflight.sh` для нового HEAD, Android Gradle/lint, A52, device storage fault injection, native readback, Android owner UI/permission checks. GitHub Actions не запускались; `main` не изменялась. **FOUNDATION_INCOMPLETE**.

## 6. Следующий архитектурный переход (открытый)

Следующий production шаг должен заменить reference `InMemoryLedger`/journal на **единую реальную локальную Android transactional storage domain**, включающую `used+receipt+M-ref` и версию состояния/реестр capability. Нужны fault-injection на каждой durable boundary, санкционированный источник native readback и fresh owner/session/boot policy. До доказательства — `DenyAllAndroidPort`; новый phase4 file **не** является правом выполнить действие.
