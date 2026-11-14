# UNO WP-04 — экспериментальный локальный нейрочат, 2026-11-09

## Основание
Владелец согласовал направление «UNO 1.0 как полезный Android-продукт с временными готовыми лицензированными весами; собственное R5.3/F и исследования отдельно». Результаты PocketPal Qwen3-0.6B на Huawei nova 10 SE: ~13.93, 13.78, 13.58, 12.62, 11.83 token/s; TTFT до 13.43s в длинном чате. Wi-Fi виден активным: строгий network-off не доказан. На Samsung A52 ~6.98..14.04 token/s. Это измерения PocketPal, НЕ UNO.

## Scope и неизменённые границы
- Прежняя лабораторная UnoActivity сохраняется; новая UnoChatActivity открывается отдельной кнопкой. Ни DENY_ALL Android NativePort, ни owner auth, ни STOP/прочие эксперименты не ослабляются.
- CPU-only GGUF JNI библиотека `uno_llama`, pinned upstream `ggml-org/llama.cpp@a4d4f2fd4ec85ec6a0a9ece4870416c1b6cc24f5` под MIT, вложена Git submodule. Минимальная версия Android приложения остаётся API 26, для Huawei Android 12 API31 подходит на уровне manifest (не равно device verification).
- Qwen3-0.6B Q4_K_M **кандидат**, не автоматически выбранная модель для релиза. Веса в git/APK не добавлены. Native загружает только владелец выбранный GGUF из локального provider в app-private hashed file. `INTERNET` permission нет. SAF ограничен системными local provider authorities; всё равно требует проверки реального Android офлайн-режима.
- Общий ограниченный диалоговый контекст: один системный prompt без прав, до 8 последних точных реплик + новый ввод, 2048 token context / 128 output, no fake Android action / no runtime weight update. История до 40 реплик атомарно в app-private JSON; **не зашифрована**, НЕ семантическая долговременная память и НЕ доказанный результат ОС. При проблеме чтения fail-closed, пользовательские секреты вводить не надо.
- Кнопка «СТОП ОТВЕТА» отменяет только inference at token/prefill boundaries; не выдаётся за системный STOP. Native model reload и generation сериализованы mutex+single-worker.
- Cross-process isolated NeuralWorkerService из scaffold пока placeholder. В этом WP-04 нейроинференс внутри приложения, поэтому **нет утверждения о настоящей изоляции небезопасного JNI от доверенного Android-контура**. Прежде чем расширять полномочия, нужна отдельная security review и перенос inference в изолированный процесс.

## Репликация
```
git submodule update --init --recursive
cd android
bash scripts/run_all_preflight.sh
gradle --no-daemon :core:unoHostTests :app:assembleDebug :app:lintDebug
```
SDK35, NDK27.2.12479018, CMake3.22.1, Gradle8.7, JDK17; only arm64-v8a. CI debug builds use unique package suffix.

## Статусы
- Source integration: **IMPLEMENTED в кандидатном дереве**, только после git commit ниже.
- Host: **NOT YET TESTED** для нового кода на момент подготовки.
- Android build/lint: **NOT YET VERIFIED**; Actions workflow при коммите этого workflow запускает необходимую единичную проверку.
- Huawei/Samsung device: **NOT TESTED** для UNO neural chat.
- Состояние UNO: **FOUNDATION_INCOMPLETE, RELEASE_READY=FALSE**. Research math R5.3 not replaced.

## Риски
`llama_chat_apply_template` из C API поддерживает не все GGUF Jinja templates — при несовместимом шаблоне backend должен отказать, а не выдумать ответ. На Huawei API31 фактическая загрузка native библиотеки и возврат токенов остаются открытым device gate. Prompt восстанавливается каждый ход, что объясняет возможный рост TTFT; постоянную KV/semantic memory не имитировать. Нет гарантий производительности, памяти, теплового режима, качества и коммерческой пригодности. Лицензия конкретного GGUF и attribution проверяются до распространения.
