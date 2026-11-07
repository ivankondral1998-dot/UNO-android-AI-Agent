# UNO 1.0 — аудит и усиление основания WP-01 (7 ноября 2026)

**Статус:** частично `HOST_TESTED`; новая Android-сборка и физическое испытание НЕ выполнены. Это отчёт об исходниках и тестах, **не** новый действующий набор инструкций. Единственные действующие правила — корневой `/AGENTS.md` V3 или более позднее явное решение владельца.

## Проверенная точка и сохранность

- Приватный репозиторий: `ivankondral1998-dot/UNO-android-AI-Agent`.
- Исходная разрешённая рабочая ветка: `feat/uno-production-foundation-20261106`, HEAD при начале: `ebdfd3f8263592a4906a9829b3b93cadd2256a9c`.
- Для рискованных исправлений открыта новая **изолированная** ветка `feat/uno-foundation-hardening-20261107` от этого SHA. Старая feature-ветка и `main` не исправлялись.
- Источники `Controller.kt`, `Memory.kt`, `Contracts.kt` из вложенного исторического ZIP сверены с исходными Git blob SHA в действующей ветке; это побайтовый baseline до исправления.
- Новый код **не** добавляет Android permissions, сетевые запросы, настоящий каталог эффектов, обучение весов или работающий нейроинференс. `DenyAllAndroidPort` остаётся подключённым.

## Дефекты и сделанные изменения

| ID | До исправления | Изменение | Статус |
| --- | --- | --- | --- |
| FND-01 | Изменяемые `Proposal.canonicalArgs` могли измениться после вычисления digest и разрешения | Снимок аргументов в `prepare`; перед передачей NativePort — отдельный deep-copy билета и сверка digest | `HOST_TESTED` для fake-native |
| FND-02 | Выданный `Ticket` был публично изменяемым; повтор `dispatch` можно было попытаться спровоцировать сбросом `phase/used` | Закрытый реестр реально выданных билетов по идентичности; одноразовая отметка dispatch независимо от изменяемых полей | `HOST_TESTED` |
| FND-03 | `NativeEndpoint.FALSE` мог завершить путь `readbackAndCommit` как успешный | Только независимый `TRUE` может зафиксировать успешный commit, `FALSE` не подменяет успех | `HOST_TESTED` fake-native |
| FND-04 | `UNKNOWN` после dispatch требовал отдельного явного сохранения неопределённости | При `UNKNOWN` остаётся `MAY_HAVE_EXECUTED`, повторный dispatch невозможен | `HOST_TESTED` in-memory |
| FND-05 | `ExactMemory.write/read` отдавали mutable `ByteArray`, через которые можно повредить внутренний объект | Defensive copy на запись/чтение; синхронизированные операции; отдельный `NOT_FOUND` | `HOST_TESTED` in-memory |
| FND-06 | Публичный `BoundedScheduler.stopLatch` можно было перевести обратно в false; старая очередь сохраняла работу после STOP | Private latch, `stop()` очищает очередь; `poll(nowNanos)` требует явного монотонного времени, отбрасывает просроченное | `HOST_TESTED` |
| FND-07 | Статический preflight можно было обойти добавлением permissions, exported-компонентов или заменой deny-all | Проверка XML и фактической wiring-строки, ограничение сетевых/effect API; восемь негативных мутационных тестов | `HOST_TESTED` фикстуры |
| FND-08 | ADB-скрипт без `--serial` мог попасть не на тот телефон при нескольких устройствах | Требуется ровно одно авторизованное устройство либо явный serial; добавлен `--expect-model`; четыре unit-теста | `HOST_TESTED` фикстуры |
| FND-09 | Любой вызывающий мог записать `EntryKind.VERIFIED_COMPLETION` без Android readback | Generic write теперь отказывает с `VERIFIED_COMPLETION_REQUIRES_NATIVE_READBACK`; тест на подделку provenance | `HOST_TESTED`, настоящий trusted writer ещё отсутствует |
| FND-10 | UI лаборатории заявлял 45 секунд для STRESS при фактическом лимите 60 секунд | Подпись UI приведена к лимитам 12/60 секунд; Android UI после правки не пересобран | `IMPLEMENTED_UNBUILT` |

Изменения FND-01–06 **не превращают** `TrustController` в production Android authority: current adapter имеет временный `InMemoryLedger`, симуляторный `NativePort` и тестовую булеву модель согласия. Настоящая доверенная Android-граница НЕ реализована.

## Выполненные проверки и точные границы

1. Локальная Kotlin/JVM-проверка с `kotlinc 1.9.0` / JRE 21: 10 базовых CoreSelfTest + 14 новых FoundationHardeningTest = **24 PASS**, 0 зафиксированных падений. Прогон включает повторное предъявление ticket, подмену аргументов во время dispatch, отрицательный и неопределённый readback, one-way STOP, нарушения изоляции памяти, TTL очереди.
2. Проверены SHA Git blob исправленных `Controller.kt` (`5ca9296cd55ebd0311d5f002a14a108a7943d609`), `Memory.kt` (`08e259985ff5fa3f8da10292aac0cfba026df951`), `Scheduler.kt` (`2c6830916e6b4ffe218e8fe5bb5806200304ac22`), `FoundationHardeningTest.kt` (`90874128e4cf7cdeafb7b26597963884117c6369`). Этим подтверждается, что проверенный локально код соответствующих файлов перенесён без побайтового расхождения.
3. Локальные Python unit-тесты мутаций манифеста/источников: **8 PASS**. Локальные тесты чистой функции выбора ADB serial: **4 PASS**. Они проверяют **только** фикстуры/логику, не работающий Android и не настоящее подключение USB.
4. Новый suite включён в `android/core/src/test/kotlin/.../AllHostTests.kt`, Python проверки — в `android/scripts/test_lab_tools.py`. **Полный** совокупный прогон репозитория после изменений, Gradle `:core:unoHostTests`, `:app:assembleDebug` и `:app:lintDebug` в этой сессии **не запускались**. Предыдущий Android APK из другого commit не является APK этой ветки.
5. GitHub Actions **не запускались**; workflow-файл не менялся; ветка для hardening не входит в разрешённый ранее push trigger.
6. Локальный пакет доказательств: `UNO_FOUNDATION_HOST_EVIDENCE_20261107_V2.zip`, SHA-256 `b833ebdf4b42a31b9a216ebf994976aad770b13ad5c45a67154201d21e897b58`. Включает тестируемое **подмножество** исходников, host-логи 24 Kotlin и 12 Python проверок; **не** полный Android-проект. V1 архив сохранён отдельно.

## Нерешённые критические границы

- **WP-02 / Android authority:** реальная проверка владельца и прав, атомарная граница native dispatch/STOP, долговечный журнал PREPARED/UNKNOWN/commit и независимый Android readback отсутствуют. `@Synchronized` защищает reference-контроллер от host-группы гонок, но STOP может ждать уже выполняющийся native вызов. Нельзя подключать privileged Android Port по результатам этих unit-тестов.
- **WP-05 / память:** точная память пока in-memory. Нет согласованной encrypted persistence, WAL, анти-rollback/boot-identity, безопасного забывания, snapshot-consistency при process death. `expiryMonotonicNanos` нельзя переносить через перезагрузку без boot identity/rebase.
- **WP-03/04 / интеллект:** нейросеть отсутствует, формат и лицензия весов не выбраны, не выполнены device parity, реальный русский диалог, planner, ASR/TTS и end-to-end memory/action loop. Не запускать обучение без отдельного разрешения.
- **Android lifecycle/UI:** `UnoActivity.onPause()` переводит reference-контроллер в STOP, но read-only лаборатории могут быть запущены снова вручную. Перед включением настоящих действий нужен явный протокол безопасного возобновления с проверкой владельца; автоматическое `clearStop()` недопустимо.
- **Реальная безопасность офлайна:** статический кодовый фильтр и отсутствие permission INTERNET не доказывают сетевую изоляцию будущих зависимостей, системных SAF-провайдеров или других компонентов.
- **Физические результаты:** на новом APK нет Samsung A52 install/logcat/probe, неизвестны батарея/thermal/PSS/latency/настоящие effect races. Никакого измерения Joules/task не было.
- **Подлинность исторических исследований:** текстовые отчёты R5.3/N0/FRTR доступны; часть оригинальных 13 ZIP 6–7 ноября существует только в отдельном архиве/индексе, поэтому их данные не объявляются полным воспроизведением.

## Приёмка следующей контрольной точки

На разрешённой среде с JDK 17 / Kotlin 1.9.24 / SDK35 вручную выполнить `cd android && bash scripts/run_all_preflight.sh`, затем без запуска Actions `gradle :core:unoHostTests :app:assembleDebug :app:lintDebug`; сохранить полный stdout/stderr и SHA APK. После сборки — только по согласованию с владельцем установить **собственный** APK на Samsung A52 / Android 14 и снять raw-данные `adb_collect.py --serial <DEVICE> --expect-model SM-A525F --out ./evidence` (точное значение `ro.product.model` проверить на телефоне). Перед WP-02 создать lock/fault-injection тесты настоящего доверенного Android-порта и transaction journal. Ни один старый PASS не переносить на эти gate без повторного испытания.

**Итог:** основание стало устойчивее к ряду конкретных ошибок и лучше проверяет собственные ограничения. Это не окончательно безопасный foundation и не готовый интеллектуальный продукт. Исходные документы и `main` сохранены.
