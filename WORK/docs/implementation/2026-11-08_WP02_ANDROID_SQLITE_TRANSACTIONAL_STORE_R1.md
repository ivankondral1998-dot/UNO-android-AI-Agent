# UNO — WP-02 Android SQLite transactional outcome store, R1

**Дата:** 2026-11-08. **Ветка:** `feat/uno-foundation-hardening-20261107`. **Полномочия:** `/AGENTS.md` в текущей ветке; этот документ не изменяет решений владельца.

**Честный статус:** `IMPLEMENTED_UNWIRED` для Android Kotlin adapter, `HOST_TESTED_SCHEMA` для настоящего SQLite на Linux/Python, `KOTLIN_STUB_COMPILED` для синтаксиса. **Не `ANDROID_BUILT`, не `DEVICE_VERIFIED`. `FOUNDATION_INCOMPLETE`.** Класс не подключён к `TrustController`/Android native port; `UnoActivity` по-прежнему использует `DenyAllAndroidPort`, `DenyAllLedger`, `NoWeightsNeuralPort`. Это реальный Android storage API, но ещё не действующая доверенная граница.

## Почему не ещё один JVM-журнал

До этого WP-02 создал reference-only `ActionIntentJournal` с фазами `PREPARED → MAY_HAVE_EXECUTED → REFERENCE_USED_RECEIPT`. Вариант v2 синхронизирует `used` и receipt в **одном file record**, но не предоставляет единой Android SQL-транзакции для `used+readback+memory_ref` и не может сам авторизовать OS effect.

В `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeStore.kt` добавлен `SQLiteOpenHelper` для **app-private** `uno_outcome_v1.db`. Внутри Android SQLite одного trusted app process используются `beginTransactionNonExclusive`, `setTransactionSuccessful`, `endTransaction`, WAL, foreign keys и ограничения SQL. Колонки `operations`: `ticket_id`, digest предложения, 128-bit process session nonce, owner epoch (сейчас только связанный атрибут), deadline/prepare/dispatch monotonic times, phase, used, endpoint, source, generation, observed time и `memory_ref`. `memory_records` содержит неизменяемые bytes **только reference readback claim** с content hash; payload не является нейронным embedding, точной памятью пользователя или verified completion.

## Причинные условия и границы

1. `stage(ticket)` допускает запись **только PREPARED** и только новых `id` при корректном digest, сроке и bounded quota. Не является авторизацией владельца. После reboot/process restart создаётся **новый случайный session nonce**; старые tickets не могут быть автоматически вооружены из БД.
2. `arm(ticket)` делает `MAY_HAVE_EXECUTED` долговечным **до** потенциального native-вызова, но **не вызывает native**. Состояние не даёт право на эффект; прежний код `ActionIntentJournal` сохранён без удаления или переноса данных.
3. `recordReadbackClaim(ticket,evidence)` требует активную process session, `WAIT_READBACK`, `TRUE` либо `FALSE` (не `UNKNOWN`), положительный generation, допустимый tag, `dispatch_ts ≤ observed_ts ≤ current_elapsed_ts < deadline`. В **одной SQLite-транзакции** вставляется bounded запись `memory_records` и обновляются `phase=3, used=1, outcome, source_tag, generation, observed_ns, memory_ref`. Не даёт отдельно commit memory при неуспехе операции. `FALSE` здесь означает только *заявленный native sample*, не отказ `Rejected`.
4. `inspectAfterRestart()` **никогда не возвращает executable Ticket**: все строки лишь для диагностики/reconciliation. `Inspection.Unavailable` явно отличается от `Inspection.Rows(emptyList())`. `PRAGMA quick_check`, foreign keys, hashed content validation и fail-closed schema migrations сохраняют запрет на молчаливый ремонт/очистку.
5. `stop()` блокирует последующие storage writes, но не гарантирует отмену уже начатого OS-effect или hard real-time linearization. Между проверками STOP и commit есть гонка; OS trust port всё ещё отсутствует.

**Нельзя заявлять:** что `REFERENCE_READBACK_CLAIM` — действительный Android result или независимый success; что `SQLite` даёт аппаратную гарантию A_fs/anti-rollback; что memory payload является exact memory/provenance пользователя; что вычисления `F`, веса, ASR, планирование, Android permissions/consent уже подключены. Сохранённый process nonce не является owner session credential. В базе нет `P-version`, общего `D/L` serializer, полного `M` store, ключевой аутентификации, ротации WAL и проверенной power-loss устойчивости. Вместимость `4096` operations и `32` active — bounded implementation policy, не утверждённый RAM профиль. SQLite на A52 не проверялся.

## Доказательная база именно этого изменения

**Новые файлы:**
- `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeStore.kt` — Git blob `9db7d76ab29969592503593555fe3062a94fd871`.
- `android/scripts/test_sqlite_outcome_schema.py` — Git blob `65dea3f27d24dcf4a7eb71f70508fa3285cf24c8`; SQL считывается **непосредственно из Kotlin `CREATE_*` констант**, это не пересказ схемы.
- `android/scripts/run_all_preflight.sh` — включает новый тестовый скрипт. Исторические host-JVM tests и script не удалены.

**Локально запущено:** Python `sqlite3` с реальной файловой SQLite: `14/14 PASS` по схеме, constraint, WAL, FK, prepare/arm, atomic used+outcome+memory ref, повторному открытию, дубликатам, stale timestamp, rollback после всех updates/до update, запрету удаления referenced memory и сохранению unresolved. Три независимых повторных прогона `14/14 PASS`. Kotlin source **скомпилирован без ошибок только против тестовых Android stubs** с `kotlinc-jvm`; это не Android SDK и не запуск реального SQLiteOpenHelper. Предыдущий Kotlin reference host JAR был отдельно перепроверен: `12+23+11+12 = 58/58 PASS`; это не полный текущий `run_all_preflight.sh`. `main` не изменена, GitHub Actions не запускались.

**Пределы теста:** Python выполняет реальную SQLite-схему и моделирует отдельные переходы; он **не исполняет Kotlin-методы** `stage/arm/recordReadbackClaim`. `kotlinc` с заглушками подтверждает только типы/синтаксис относительно этих заглушек, не совместимость с Android API 35. Требуются manual Gradle assemble/lint, Android instrumentation, property-based transaction fault injection, disk-full/crash/reboot/rollback tests на A52, ресурсные PSS/IO/thermal измерения. Старые `ActionIntentJournal` и новая SQLite база пока не синхронизированы; никакой автоматической миграции не вводилось.

## Сохранённые источники, включая Jarvis

- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` — causal clock, STOP, time/endpoint.
- `.../ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` — `M ≠ L ≠ P`, atomic `used + receipt + P-version + M-ref`, crash ambiguity, bounded WAL, exact vs semantic.
- `.../ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` — A_cap, owner/permission, delegated OS dispatch; local note verbs 15–18 и reference readback.
- `.../ASTRA_CURRENT/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md`; `NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md` — A_tx/A_fs условны; STOP после OS linearization не отменяет effect.
- `docs/audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md` и `docs/implementation/2026-11-08_WP02_ATOMIC_REFERENCE_RECEIPT_JARVIS_REVIEW_R1.md` — предыдущие проверочные пакеты.
- **Jarvis V21, только чтение:** приватный `kolakbro5995-cpu/JarvisLab`, `feature/v21-local-offline-runtime-20261101` @ `9c60f81d81d11a0977be1d36d928a3b5d273bbef`; `AndroidOperationAuthority.kt` @ `41e464d921d3f4d5c1497b36498d56d333f9135f`; `ConfirmationTicketGate.kt` @ `51a4ff33f0da78113c5fe672982ffb561a7097c7`. Сверены one-use/epoch, STOP, permission revalidation и контекст подтверждения. **Не копировать** OwnerGate, cloud/session зависимость, special lab bypass, старые веса/JNO, Jarvis BrainPort/Orchestrator; лицензии перепроверить до заимствований.

**Следующий фактический блокер WP-02:** отдельная доверенная Android authority (owner identity + system permission + exact consent + live STOP/revocation), узкий локальный native effect contract с native readback, проведение всех его фаз через **этот** SQLite backend, интеграционные испытания на устройстве. До этого `DenyAllAndroidPort` должен оставаться единственным действующим портом.
