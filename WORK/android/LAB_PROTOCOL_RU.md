# UNO Android — офлайн-лаборатория WP-01 / WP-02 (версия 2026-11-07)

**Применение:** Samsung Galaxy A52 Android 14 (первое устройство). Android 26+ архитектурно, без root и без сети. Устанавливается только **собранный из этого проекта debug APK**, после физической проверки build origin и SHA.

Сайт `https://uno-research.pages.dev/` — отдельный публичный ресурс. Лаборатория не подключается к нему. Никакие результаты автоматически не загружаются.

## Оперативные действия

1. Сначала выполнить `bash scripts/host_verify.sh` (тесты алгоритмов на ПК) и `python scripts/static_contract_check.py` (не Android-компиляция).
2. **Только при наличии SDK:** собрать `:app:assembleDebug` локально. Для этого нужны JDK17, Android SDK 35, Gradle 8.7+ и разрешение Gradle-плагинов. GitHub Actions запрещены.
3. Установить APK на A52 вручную после проверки SHA/подписанта. Разрешения для базовой лаборатории не требуются. Сначала снять «Снимок состояния» и «Каталог сенсоров».
4. Нажать «Быстрая лаборатория». Затем при нормальном состоянии телефона — «ЖЁСТКАЯ лаборатория». **Не запускать во время зарядки горячего телефона или при явно нестабильной батарее.** Это тесты исключительно приложения, они не изменяют настройки Android и не стирают данные.
5. При любой проблеме нажать STOP, затем закрыть приложение. STOP не отменяет уже исполненную собственную матричную операцию; работа прерывается между ограниченными порциями.
6. На ноутбуке (с включённым USB debugging и разрешённым ADB) сохранить артефакты: `python scripts/adb_collect.py --out ./evidence/`. Скрипт читает `dumpsys`, `gfxinfo`, `procstats` и app-private JSON через `run-as`, ничего никуда не отправляет.
7. Для **явно разрешённого испытания смерти процесса только UNO**: `python scripts/adb_collect.py --out ./evidence/ --restart-uno`. Эта опция *не* используется по умолчанию; сторонние приложения и данные не затрагиваются.
8. `python scripts/validate_lab.py evidence/.../uno_lab_report_*.json` — семантическая проверка выгрузок. `python scripts/compare_lab.py baseline.json candidate.json` — сравнение двух запусков. Цифры не становятся значимым PASS без закрытого протокола, одинакового устройства/профиля и статистической процедуры.

## Реальные измерительные каналы

| Направление | Фактические данные | Семантика и предел |
|---|---|---|
| ОС/устройство | Android SDK/release, модель, ABI, PID, системные monotonic clocks | Metadata, не целостность телефона |
| CPU | naive FP32 matmul p50/p95/p99, sustained CPU batch, параллельная нагрузка, process elapsed CPU, читаемые частоты sysfs | **Не** вычислительная способность конечной нейросети, не A52 peak GFLOPS |
| RAM | PSS, RSS API29+, Java heap used/max, native heap, Dalvik/native PSS, private dirty, available RAM/low memory | Только разрешённые метрики собственного процесса; будущий NN backend не учтён |
| GC | runtime stats `art.gc.*`/`art.heap.*` | Поля зависят от реализации Android, отсутствие ≠ 0 |
| Нагрев | PowerManager thermal status и thermal headroom API30+, температура батареи при наличии | Headroom не температура CPU; severe + батарея ≥44.5°C приводят к ABORT |
| Батарея | уровень, температура, напряжение, статус, текущий ток, накопленный заряд, energy counter при наличии | OEM может не предоставлять свойства; NO доказанного физического `J/task` |
| Диск | свободное место в app-private, запись+fsync+SHA256+чтение 256КиБ/2МиБ | fsync return ≠ crash-durability theorem |
| События | 64-slot bounded queue, переполнение, многопоточная вставка, STOP и запрет новых событий | **Не** атомарный OS-dispatch, пока WP-02 не реализован |
| Целостность | SHA-256 правильно замечает искажение синтетической копии | Не случайная порча настоящего файла |
| Сенсоры | каталог типов/диапазонов/точности, события обычных motion/light/pressure, время и пропуски | Нет эталона физической точности, многие датчики могут отсутствовать |
| UI | задержки таймера main-thread heartbeat ≥350мс и максимум | Не равно точным frame-overrun; отдельный `gfxinfo` и Macrobenchmark |
| Lifecycle | Android Activity pause/stop, остановка лаборатории, дополнительное явное ADB force-stop только UNO | Физический PASS только с A52 и логами |
| Offline | no INTERNET permission, no networking code in core/app, app-private artifacts | **Не** формальное доказательство полной изоляции будущих компонентов |

## Режимы и правила остановки

- `QUICK`: ≤12 секунд, ≤8MiB дополнительного Java heap, CPU sustained≈1с, датчики≈1с.
- `STRESS`: ≤60 секунд, ≤64MiB дополнительного Java heap (и минимум 32MiB Java heap reserve), CPU sustained≈25с, датчики≈4с, параллельная нагрузка.
- STOP и уход приложения в фон отменяют текущий сценарий. Если батарея <15%, температура батареи ≥44.5°C, система сообщает `THERMAL_STATUS_SEVERE` либо истёк бюджет — дальнейшие сценарии не запускаются. Это **лабораторные предохранители**, не утверждённые пороги будущего продукта.
- Никаких намеренных OOM, удаления пользовательских файлов, сетевых вызовов, привилегированных Android-действий, бесконечных циклов и CPU governor adjustments.
- JSON-свидетельства сохраняются только в `files/diagnostics/` собственного приложения; максимум 30 отчётов, затем запись останавливается без стирания прежних. Промежуточный IO fixture принадлежит лаборатории и перезаписывается. `run-as` доступен лишь у debug-приложения.
- **Разделение приёмки:** выполненный workload = PASS для локального сценария, но не PASS устройства, интеллекта, readback или безопасности ОС.

## Что будет проверяться позже (пока NOT_RUN)

- Настоящая многопоточная гонка STOP с **native dispatch** Android (WP-02), forged/expired consent, revoke, READBACK after restart, MAY_HAVE_EXECUTED, идентификация владельца.
- CPU ↔ Android parity одного `F_Θ`, B2 tensor ABI, skip-MAC, INT8/FP16, RAM/PSS полного inference runtime (WP-03).
- Генерация и понимание русского текста, цель, новая сущность, сложные негативные сценарии, закрытый holdout, сравнение с fixed/table baselines (WP-04).
- Конфликт, точность и забывание памяти, snapshot fault injection, ABA, TTL, revoke, corrupt WAL, восстановление после reboot (WP-05).
- Реальные разрешённые ОС-эффекты, точная проверка результата, idempotency, unknown effects, multi-step plans (WP-06).
- PCM audio, ASR/TTS airplane mode, SENSOR/OS semantic accuracy, экран с MediaProjection по согласованию (WP-07).
- Macrobenchmark для startup/frame jank (`:macrobenchmark` отдельным модулем с проверенными зависимостями); Perfetto; native profiling, физический energy measurement (WP-08).
- End-to-end термические и батарейные тесты, privacy/perms, лицензии и коммерческая приёмка (WP-09).

## Границы проверки на 7 ноября

- `core` может пройти **HOST_TESTED**, даже если Android SDK отсутствует.
- `app` — только `IMPLEMENTED_UNBUILT` до успешного Gradle assemble.
- `DEVICE_VERIFIED=FALSE` до записи реальных A52 логов; не подменять them синтетическими fixtures.
- Актуальный `main/AGENTS.md` — единственные активные правила проекта.

## Официальные источники измерений

- https://developer.android.com/reference/android/os/Debug
- https://developer.android.com/reference/android/os/BatteryManager
- https://developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int)
- https://developer.android.com/reference/android/hardware/SensorManager
- https://developer.android.com/tools/dumpsys
- https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
