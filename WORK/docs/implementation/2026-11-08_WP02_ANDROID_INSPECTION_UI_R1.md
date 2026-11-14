# UNO WP-02 — Android SQLite recovery inspection в диагностическом UI, R1

**Дата:** 2026-11-08. **Режим:** feature-ветка `feat/uno-foundation-hardening-20261107`; корневой `/AGENTS.md` определяет все полномочия. **Текущий статус:** `IMPLEMENTED`, `HOST_TESTED` только для изолированного Kotlin-inspector и его stub-контрактов, `ANDROID_BUILT=FALSE`, `DEVICE_VERIFIED=FALSE`. По всему продукту `FOUNDATION_INCOMPLETE`.

## Проблема и сделанное изменение

Предыдущий WP-02 реализовал app-private Android `SQLiteOpenHelper` `AndroidOutcomeStore` и транзакцию для `used / readback claim / memory_ref`, но приложение `UnoActivity` его даже не открывало. При этом в `UnoActivity` оставались `TrustController(DenyAllAndroidPort(), DenyAllLedger())` и `NoWeightsNeuralPort`, что **сознательно сохранено**. Нельзя принимать отсутствие UI-интеграции за доказанное Android recovery.

Теперь добавлен `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeInspection.kt`. В нём есть только inspect/read-only recovery summary (число `PREPARED`, `MAY_HAVE_EXECUTED`, записанных **непроверенных** readback claims). Ни ticket IDs, ни аргументы, ни payloads, ни владельческие данные в summary не возвращаются. `Inspection.Unavailable`, неизвестная будущая фаза, `used` без подтверждающей ссылки, executable recovered ticket, ошибка открытия и отсутствие главного SQLite-файла при наличии `-wal/-shm/-journal` интерпретируются **только как недоступность**, не как «записей нет» или «действие успешно».

В `UnoActivity` добавлены две **ручные** функции: (1) проверить уже существующую SQLite базу **без создания новой**, (2) по явному нажатию создать пустой локальный SQLite-файл и прочитать его. Оба варианта выполняются на существующем background worker и пишут только app-private diagnostic JSON по действующему механизму `DeviceProbe.persist`. Отчёт прямо содержит `verified_os_outcomes=false` и `native_actions_enabled=false`. Повреждённая/недоступная база вызывает ошибку; UI **не говорит об успехе**. В этих путях **нет** `stage`, `arm`, `native.dispatch`, model weights или изменения permissions. Вся уже записанная история остаётся на месте: никаких migrations, очистки, перезаписи старого `ActionIntentJournal` или memory.

Это реальное приложение UI→app-private SQLite **inspect-only**, а не цепочка owner→consent→dispatch→readback.

## Нормативные математические границы

Источник — исходные Astra/R5.3: `ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` (causal clock/STOP), `ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` (`M ≠ L ≠ P`, exact/semantic, atomic `used+receipt+M-ref`), `ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` (`A_cap`, owner/OS permission/readback), `ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md` (условные доказательства `A_tx,A_fs`), `NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md` и текущий `/AGENTS.md`. Эта итерация не меняла математическую модель и не переводит гипотезы в `PROVEN`.

**Jarvis (read-only):** `kolakbro5995-cpu/JarvisLab`, `feature/v21-local-offline-runtime-20261101` @ `9c60f81d81d11a0977be1d36d928a3b5d273bbef`, `AndroidOperationAuthority.kt` blob `41e464d921d3f4d5c1497b36498d56d333f9135f` и `ConfirmationTicketGate.kt` blob `51a4ff33f0da78113c5fe672982ffb561a7097c7`. Полезны независимая authorization/revalidation, one-use ticket и STOP; **ни OwnerGate, ни облачная зависимость, ни Jarvis V0/V1/V2 веса не переносились**. Собственное подтверждение владельца в UNO всё ещё не реализовано.

## Испытания с точным уровнем доверия

Изменённый `AndroidOutcomeInspection.kt` и два host-fixture файла побайтово сверены с GitHub. `android/scripts/test_outcome_inspection_host.sh` компилирует **фактический production Kotlin-inspector** с минимальными подменами Android `Context` и `AndroidOutcomeStore`; 11/11 JVM проверок PASS: отсутствие БД без создания, orphan WAL, явное создание, счётчики по фазам, отказ при недействительном `used`, executable recovered row, unknown phase, storage error/exception, no false completion. Это не исполнение `SQLiteOpenHelper` на Android и не тест `UnoActivity`.

Отдельно повторены прежние доказательства: 14/14 SQL-сценариев на host SQLite из реальных Kotlin-констант (`test_sqlite_outcome_schema.py`), 58/58 прежних reference journal/controller tests из ранее собранного точного JAR. **Всего 83 сценария разных уровней**, не «83 Android end-to-end tests». Новый Kotlin inspector-test зарегистрирован в `android/scripts/run_all_preflight.sh`, но **полный preflight всех исходников на текущем HEAD не запускался**. Не запускались Gradle/SDK Android, UI instrumentation, kill/reboot, power-cut, native readback, измерения на Samsung Galaxy A52. GitHub Actions не запускались.

## Что делать дальше

Следующая реальная зависимость WP-02: реализовать отдельный **доверенный Android authorization gate**, связывающий конкретный эффект с UI/владельцем/актуальными permissions/STOP, затем подключить единственную согласованную SQLite transaction domain и независимый Android readback. До разрешения и доказательной проверки каталога эффектов не заменять `DenyAllAndroidPort`. Гарантии `A_cap,A_tx,A_fs` ещё `SPECIFIED_UNTESTED`. Ядро, веса, Neural Language и Jarvis не изменены, `main` не изменена.
