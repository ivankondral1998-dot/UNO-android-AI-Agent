# UNO — Jarvis V20 → единая лаборатория R2 (2026-11-10)

## Область и первоисточники

- Ветка: `feat/uno-foundation-hardening-20261107`, исходный HEAD до R2: `5163aa12793155f610c347a85feb7829fb957465`.
- Действующие права и приоритеты: корневой `AGENTS.md` V3; изменения только в feature-ветке, без публикации, обучения весов, изменения main, удаления или установки на A52.
- Jarvis APK: `JarvisLab-V20-Sol-Experiment-20261029.apk`, 131854930 байт, SHA-256 `984fc3f975e5cb38210e49c57bce6ea562f54f5f139e45e2569bd9fd27aeea07`.
- Повторно разобраны DEX method-id: `RuntimeDiagnostics.runUnifiedDetailed` (classes13.dex), `LabCognitiveDiagnostics.runAll` и `stats` (classes10.dex), `TaskEvidenceLedger.detailedDiagnostic` и `latencyDiagnostic` (classes11.dex), `ConfirmationTicketGate.issue/consume` (classes13.dex). Это доказательство методов и связанного API, **не** восстановление их реализации, runtime-результатов или пригодности лицензии. Старый Local Brain в UNO не переносился.

## Реальные изменения исходников

1. В существующий `android/core` добавлен **малый чистый Kotlin verdict evaluator** `UnoDiagnosticSummary.kt`: `ABORTED` при STOP/прерывании, `FAIL` при FAIL/неизвестном verdict/нуле проверок, иначе только `PARTIAL`. Никакой набор лабораторных PASS не является приёмкой агента.
2. `UnoActivity.runUnifiedSelfTest()` использует этот evaluator и записывает в JSON `summary` с количеством `passed/failed/incomplete/aborted/unrecognized`; STOP перепроверяется **непосредственно перед выводом**. Пустые `DeviceLab.results` без причины остановки теперь FAIL. Никакого автоматического согласия, записи в точную память, native Android dispatch.
3. Статический предохранитель `android/scripts/static_contract_check.py` требует путь через evaluator, а `test_static_contract_check.py` содержит отрицательный тест удаления этого пути.
4. `android/scripts/apk_update_gate.py` — **проверка совместимости двух APK без установки** через `aapt` и `apksigner`: точный `applicationId`, совпадение сертификатов SHA-256, строго увеличенный `versionCode`. Несовпадение FAIL и запрет предлагать owner in-place update.
5. `android/scripts/test_apk_update_gate.py`: восемь регрессий; включены в `run_all_preflight.sh`. Новые `UnoDiagnosticSummaryTest`: семь регрессий; включены в `AllHostTests.kt`. Ни один старый тест и ни одна старая кнопка лаборатории не удалены.

## Проверено / не проверено

- `HOST_UNIT_TESTED_LOCAL`: 7/7 нового Kotlin evaluator и 8/8 Python APK-gate тестов локально, **не** весь GitHub Gradle/JVM preflight. Тесты запускались на хосте вне Android. Исходный APK Jarvis по SHA проверен повторно.
- `IMPLEMENTED`: изменения закоммичены в feature-ветку; код сохраняет существующий `org.unovyra.uno.scaffold` в Gradle. Новый package не создавался.
- `ANDROID_BUILT`: **NO для новых коммитов R2**. Успешный Actions #42790494227 относится к предыдущему `5163aa1` и не подтверждает изменения R2.
- `DEVICE_VERIFIED`: **NO**, на Samsung A52 текущая R2 не устанавливалась и не испытывалась.
- `RELEASE_READY`: **NO**, интеллект/новые веса/Android real action readback ещё не реализованы.

## Одна установка вместо десятков ярлыков

Текущий `uno-feature-android-verify.yml` целенаправленно генерирует **новый side-by-side package** `org.unovyra.uno.scaffold.ci<RUN_ID>` для CI; это не обновление существующего UNO. **Не предлагать владельцу устанавливать эти CI APK.** Ранее установленное приложение, ключ подписи и versionCode на A52 не установлены достоверно из одного лишь имени скачанного APK. Результат `apk_update_gate.py` между двумя произвольными файлами также **не** доказывает, что первый фактически стоит на устройстве.

Будущее обновление:
```bash
python3 android/scripts/apk_update_gate.py \
  --installed-baseline-apk PREVIOUS_CONFIRMED_INSTALLED.apk \
  --candidate-apk CANDIDATE.apk \
  --aapt /path/to/aapt --apksigner /path/to/apksigner
```

Использовать только baseline, достоверно соответствующий установленному пакету, проверять versionCode, подпись и сохранность данных. Нет гарантии совместимого обновления, пока стабильная подпись не определена. Не очищать данные и не удалять старые приложения без отдельного разрешения.

## Следующий gate

На текущем R2 SHA: целиком прогнать `cd android && bash scripts/run_all_preflight.sh`, `:core:unoHostTests`, `:app:assembleDebug`, lint и статические отрицательные тесты в доступной Android SDK 35 среде. Выполнить review результатов, только затем решать вопрос о **единственном** обновляемом APK. Для физического A52 нужен один запуск единого теста и JSON; owner authentication, настоящий OS action readback, restart/reboot остаются отдельными честными MANUAL_REQUIRED, а не «PASS».
