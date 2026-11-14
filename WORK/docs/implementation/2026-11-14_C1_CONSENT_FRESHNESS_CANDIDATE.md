# UNO C1 — проверка срока согласия на границе dispatch, кандидат 2026-11-14

Статус: **SOURCE_PATCHED / HOST_UNTESTED / ANDROID_UNBUILT / DEVICE_UNTESTED**. Это ограниченная доработка существующего Android UNO, не новая архитектура F и не разрешение OS-действий.

## Источники и защита математической преемственности

- Действующие правила: `main/AGENTS.md`, версия UNO-AGENTS-2026-11-12-V4.
- Исходный Android HEAD: `feat/uno-permanent-full-foundation-20261111@ec9764f03dcdca305b575b41514d0aa153d2aab7`.
- R5.3: `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` (S2/S3, S7), `ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` (Android authority, STOP, endpoint).
- Исправления единого цикла: `design/uno-unified-cycle-data-20261112`, UDC v0.3 (CANDIDATE).
- Связанный независимый аудит: `audit/uno-terra-math-training-20261112`; никакие выводы не повышаются до owner approval.

## Конкретный дефект C1

До патча `TrustController.prepare` проверял `Consent.expiresAtNanos`, но `Ticket.deadlineNanos` сохранял только внешний task deadline. `dispatchOutcome` затем принимал старую временную метку `now` без новой проверки consent expiry. Долгое ожидание UI/журнала могло привести к ошибочно допустимому вызову.

Патч задаёт `ticket.deadlineNanos = min(taskDeadline, consent.expiresAtNanos)` и перепроверяет монотонное время на подготовке, перед native invocation (включая после journal.arm) и перед/после readback. Инъекция доверенных часов в `TrustController` опциональна только для старых host-тестов; Android Activity передаёт `SystemClock.elapsedRealtimeNanos`. При ошибке/регрессии часов заявка отклоняется.

**Ограничение:** контроллер и тестовый порт остаются reference-only; `DenyAllAndroidPort` и `DenyAllLedger` сохранены. Между последним замером и фактической точкой действия OS остаётся отдельная TOCTOU/STOP-линеаризация. Полное закрытие Android C1 требует отдельного trusted native dispatcher, независимых проверок полномочий и device fault tests. Не перепутать `SOURCE_PATCHED` с закрытым продуктовым gate.

## Изменённое

- `android/core/src/main/kotlin/org/unovyra/uno/core/Controller.kt`: TTL/clock gates, старый контракт host вызовов сохранён.
- `android/app/src/main/kotlin/org/unovyra/uno/UnoActivity.kt`: доверенные монотонные часы, Android effects всё ещё deny-all.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ConsentFreshnessTest.kt`: 8 отрицательных/положительных fake-native сценариев.
- `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt`: подключение тестов к общему раннеру.

## Приёмка и реальный статус

В GitHub source patch записан в отдельную ветку с сохранением исходной feature-ветки. Исходные R5.3/UDC/Terra/UNO-TRAIN-001 не изменялись. `main` и GitHub Actions не трогались.

**Не выполнялось:** Kotlin host runner, Gradle build/lint, подпись нового APK, установка/испытание A52. Среда текущего чата имеет Kotlin 1.9 и Java 21, но не Android SDK/Gradle; текущие исходники доступны через GitHub connector, а не как полный локальный checkout. Ни один тест C1 не объявлять PASS до настоящего запуска.

Канал подписи отдельно проверен **метаданными**: приватный `ivankondral1998-dot/UNO-owner-signing-backup`, `channel.json` application_id `org.unovyra.uno`, public signer SHA-256 `58c92aec4b4ffe2dda8e1cb481e0216b2f51f3aabe4470b919036e7abdb99f51`, совпадает с ранее записанными receipt APK. PKCS12/password **не читались**, не переносились и не коммитились в исходный репозиторий. Доступность файла не равна проверенному паролю или реальной новой подписи.

Следующий обязательный gate перед дальнейшими исправлениями/подписанием: checkout этой ветки на машине с инструментами, `cd android && bash scripts/run_all_preflight.sh`, затем `gradle :app:assembleDebug :app:lintDebug` без новых GitHub Actions, сравнение package/versionCode/signer и безопасное обновление только после backup app-private данных. Никаких самостоятельных переустановок и удаления прежнего UNO.
