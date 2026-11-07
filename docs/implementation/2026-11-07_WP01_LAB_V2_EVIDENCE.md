# UNO WP-01 — автономная Android-лаборатория v2 (7 ноября 2026)

**Рабочая ветка:** `feat/uno-production-foundation-20261106` до изменений `dc20297aa555080da9d5064cc753b9190d296968`. Действующие инструкции — только корневой `AGENTS.md`.

## Реализовано

- Ручные профили QUICK/STRESS, прерывание STOP, переход в фон, максимальная длительность 12/60 секунд.
- Метрики Android 14: CPU/matmul, Java/native heap, PSS/RSS, GC, process CPU time, battery temperature/current/voltage/charge/energy counter if OEM supports, thermal status/headroom, readable CPU frequency, storage, ordinary sensors.
- Нагрузки: sustained CPU, parallel CPU, bounded heap, bounded multithread queue/STOP, SHA-256 corruption detection on synthetic copy, app-private write/fsync/readback.
- ADB offline collection (`meminfo`, `procstats`, `gfxinfo`, package, battery, thermal and UNO app JSON) + JSON validation/compare, localhost-only script tests.
- Bounded app-private report log (max 30, refuse more, do not silently delete) and explicit missing values, no data upload, zero manifest privileges.
- Исправление найденного дефекта Kotlin research-scheduler: thread-safe enqueue/poll, STOP/REVOKE/death bypass the full queue, no output of pending low-priority events after STOP. Old host assertion expecting SENSOR after STOP was corrected to the safer behavior.

## Выполненные проверки в среде исполнителя

- `bash android/scripts/host_verify.sh` -> **38 host assertions PASS**.
- `python3 android/scripts/test_lab_tools.py` -> **6 unit tests PASS**.
- `python3 android/scripts/static_contract_check.py` -> **7 conditions PASS** (static only).
- `android/scripts/run_all_preflight.sh` -> exit code 0; raw log `evidence/preflight.txt`.
- AndroidManifest.xml: **0** `<uses-permission>`.

## Что не проверено

- В среде нет Android SDK/Gradle; Android-код не компилировался через AGP, **APK не собирался**.
- Телефон Samsung A52 недоступен по ADB, нет новых физических логов; **DEVICE_VERIFIED=false**.
- Нет измерения физических Joules, достоверного разрешённого Android-dispatch, AI weight inference или качества языка. Очередные PASS относятся только к указанным алгоритмам.
- `getThermalHeadroom`, `getRss`, BatteryManager properties, частоты CPU и сенсоры могут вернуть `null`/`UNSUPPORTED` на конкретной прошивке; не выдумывать значения.
- Жёсткий стресс ограничен тепловым/батарейным предохранителем и прекращается при уходе приложения в фон; он не взламывает ОС и не удаляет файлы пользователя.

## Следующая реальная приёмка

1. Android APK из этого коммита на SDK 35 / JDK17 локально.
2. `adb_collect.py` до/после QUICK и STRESS; сравнение p50/p95/p99, термального статуса, PSS/RSS, задержек кадров и расхода батареи.
3. Проверка сценариев процесса, airplane mode, low-memory pressure, doze/standby — без несогласованного изменения настроек телефона.
4. Отдельный WP-02 для настоящих полномочий Android/STOP dispatch и native readback.

**Важно:** этот файл не заменяет корневой `AGENTS.md`, а является техническим отчётом и критериями физических испытаний.
