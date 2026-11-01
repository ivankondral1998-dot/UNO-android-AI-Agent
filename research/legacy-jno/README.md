# JNO Generation 2 — исторический исследовательский пакет (НЕ UNO Core)

Источник: приватный `kolakbro5995-cpu/JarvisLab`, зафиксированный коммит `393d273feea87242a8c330f66a037b243bed8e1a` (ветка `feature/v21-jno-native-feedback-20261101`). Оригинальные Kotlin-исходники, бинарные веса и документы скопированы побайтово как Git blobs: контроль точных Git SHA записан в `PROVENANCE.json`. Бинарная модель перенесена без изменения Git blob SHA.

**Не подключать этот каталог к Android production или библиотекам UNO автоматически.** Код находится в старом package `io.jarvis.mobile.v21`, использует старый символический симулятор: 2 контекста, 6 действий, 6 исходов. `observe` — fast-weights delta-rule, а не общесистемная UNO-формула, понимание произвольного языка или самостоятельная эволюция.

Модель/веса JNO — **не новые веса UNO**. Этот пакет нужен лишь для воспроизводимого baseline и изучения проверок: checksum, all-or-nothing snapshot restore, отсутствие Android-authority в нейронной части, bounded cycles и host-проверка.

## Проверка Kotlin smoke (требуются JDK и kotlinc)

Из корня репозитория: `bash research/legacy-jno/test_legacy_core.sh`.

Тест проверяет локальную работу оригинального JNO Core, **не** полноценный UNO, Android APK или устройство. До фактического выполнения не считать его PASS.

## Предел переноса

- Не переносятся `ActionEngine`, `AndroidOperationAuthority`, Hearing, Android cloud/legacy, old LocalBrain v0/v1/v2, CELL и вся старая архитектура.
- Оригинальный JarvisLab сохраняется для происхождения и проверки: в его V21 ветке этот код используется. Удалять его до проверки зависимостей нельзя.
- Формула UNO должна охватывать единый цикл восприятия → связи/веса → состояние → решение → Android authority → readback → пластичность, а не один этот класс.
