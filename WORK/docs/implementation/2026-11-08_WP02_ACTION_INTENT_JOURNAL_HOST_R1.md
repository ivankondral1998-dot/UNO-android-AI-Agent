# UNO — WP-02: персистентный журнал намерений Android-действий, R1

**Дата:** 2026-11-08. **Уровень:** `IMPLEMENTED + HOST_TESTED` для отдельного JVM-компонента. **Не является завершённым WP-02, Android authority или надёжной защитой от физического power-cut.**

**Правила и допуски:** `/AGENTS.md` в рабочей ветке (единственный действующий источник). Цель — безопасная Android-инфраструктура; интеллектуальное ядро и веса не менялись. Работа только в `feat/uno-foundation-hardening-20261107`.

## Реальное изменение

- `android/core/src/main/kotlin/org/unovyra/uno/core/ActionIntentJournal.kt` — новый append-only single-writer журнал, без Android API и без сетевых зависимостей.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionIntentJournalTest.kt` — 12 тестов ошибок, восстановления и запрета повтора.
- `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt` — новый test-object включён в общий runner (весь текущий runner по HEAD локально ещё не проверялся).

Контракт: `prepare(ticketId, proposalSha256)` синхронно записывает `PREPARED`; `arm(ticketId, proposalSha256)` пишет и `FileDescriptor.sync()` состояние `MAY_HAVE_EXECUTED` **до** любой потенциальной отправки внешнего действия. При повторном открытии все ранее записанные tickets помечаются `recovered`: уже `PREPARED` нельзя армуировать, `MAY_HAVE_EXECUTED` также нельзя армуировать повторно. Для нового действия нужны новый ticket и новое разрешение. Журнал сам **никогда не исполняет** эффект ОС, не подтверждает успех и не выдаёт permissions.

Запись содержит только ticket ID, SHA-256 digest предложения, фазу и монотонную последовательность. Цепочка SHA-256 выявляет случайную порчу и частичные записи; это **не MAC, не подпись, не encryption и не доказательство сопротивления злоумышленнику с доступом на запись**. Для файла удерживается single-writer `FileLock`; второй writer получает отказ. Любое повреждение/обрыв записи блокирует открытие, без удаления, автоматического усечения или молчаливого восстановления. Однонаправленный `stop()` запрещает новые операции в данном экземпляре. Ограничение на `4096` уникальных tickets — намеренная bounded policy; нет автоматической ротации/удаления.

**Ограничение против гонок:** STOP и запись диска не заменяют атомарный Android `authorize/dispatch` gate. После успешного `arm()` вызывающий **обязан снова проверить** актуальные permissions, consent и STOP в том же доверенном контуре перед native dispatch. Уже отправленный эффект ОС необратим только по STOP. Вызов `arm` **не даёт** права выполнять действие.

## Что реально проверено

- Локальный `kotlinc-jvm 1.9.0`, JRE 21: новый journal **12/12 PASS**; тестируются single-writer, duplicate, wrong digest, one-way STOP, corrupted checksum, torn tail, recovery PREPARED и MAY_HAVE_EXECUTED, запрет повторного arm и replay 32 последовательных tickets.
- Локальный совмещённый **ограниченный** набор: `CoreSelfTest` (10), `FoundationHardeningTest` (14), `ComputeBudgetGateTest` (17), новый `ActionIntentJournalTest` (12) = **53/53 PASS**. **Граница доказательства:** `CoreSelfTest` в этом локальном наборе перенесён из исторического baseline и адресно адаптирован под текущий scheduler STOP API. Часть остальных исходников взята из ранее побайтово сверенных evidence ZIP. Поэтому это **не** полный, побайтово идентичный текущему HEAD `android/scripts/run_all_preflight.sh` или Gradle-тест.
- Git blob SHA локально проверенных новых source: `ActionIntentJournal.kt=5dd300ae5b7a30a9c577eb218153d2453dd6a534`, `ActionIntentJournalTest.kt=5434d3986bb214ee82e88c6b23a65b3bbda85118`. Сверить с GitHub после commit.
- **Не проводились:** Android SDK compile/lint/Gradle, лаборатория на Galaxy A52, kill -9 во время реального flash write, power-cut и независимый OS readback. GitHub Actions не запускались.

## Блокеры WP-02 / что НЕ выполнено

1. Журнал **не интегрирован** в `TrustController`, `DurableLedger` или `UnoActivity`. Сейчас работают `DenyAllAndroidPort` и `DenyAllLedger`. Подмена fake-native реальными привилегированными действиями запрещена до интеграционного trust gate.
2. Нет Android owner auth, consent/UI, permission checks, independent native readback, системного журнала verified outcomes и атомарного multi-resource commit. Нельзя через публичную функцию журнала объявить `COMMITTED`.
3. Не реализованы encryption-at-rest/Keystore, проверенное приватное расположение файла, безопасная миграция, безопасная ротация журнала, recovery after disk full и установка на Android device. Долговечность файла/каталога при внезапном отключении питания не доказана одним `fd.sync()`.
4. Проверка integrity через SHA-256 без секретного ключа не защищает от злонамеренного изменения журнала. Нельзя считать журнал источником доверенного native evidence.
5. Для точной модели действия `UNKNOWN/MAY_HAVE_EXECUTED` требуется reconciliation с реальным Android readback; автоматический retry запрещён.

**Следующий переход:** запуск полной текущей host/preflight и ручной Android сборки, затем проектирование Android `authority → durable intent → guarded native dispatch → independent readback → verified commit`, отдельные fault-injection на границах. Сохранять deny-all пока нет интеграционного доказательства. Не считать отдельный журнал завершённым каркасом UNO.
