# RESEARCH — первоисточники и эксперименты UNO

**Это не production runtime.** Материалы организованы без создания нового F/парадигмы.

- **`source-r53/`**: исходный полный пакет ASTRA/R52 и NORMATIVE. Сначала `00_START_HERE.md`, далее `NORMATIVE/01–06`, затем полные `SOURCES/ASTRA_CURRENT` и адресные оригиналы. Исходный Git tree сохранён.
- **`terra/`**: независимые исправления и пределы из аудита 12.11.2026 (C1–C4, retrieval/observability, training readiness) — кандидат для сопоставления с WORK, не применённый автоматически.
- **`udc/`**: исходный UDC v0.3 причинного цикла, состояния, GOAL/PROPOSAL, tests T01–T17.
- **`f-gradients/`**: research reverse-mode F и Wk/Wv causal memory replay. Старые логи/тесты — историческое свидетельство, не запуск этого checkout.
- **`train001/`**: исследовательский TRAIN-001, Adam/checkpoint/synthetic fixtures. **Не запускать обучение** по одной только готовности папки. Оригинальные пути в `*.sh` ещё могут подразумевать старое расположение `android/` и `research/` в корне; перед запуском адаптировать и проверить.
- `legacy-jno/`: архив чужих весов Jarvis, НЕ модель UNO. `weight-kernels/`: вычислительные исследования.
- `archive-main-20261114/`: полный снимок старого main по Git tree; read-only исторический контекст.
- `archive-recovery-docs/`, `archive-recovery-research/`: сохранённый исторический source-recovery snapshot. Могут содержать дубли архивных формул; НЕ заменяют source-r53 и terra.

Состояние исходных 19 веток: [BRANCH_INDEX.txt](BRANCH_INDEX.txt). В старые ветки обращаться только при разборе provenance, не для выбора новой рабочей основы. Разрешения: главный [main/AGENTS.md](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/main/AGENTS.md).

Чтобы научная поправка стала WORK: укажи конкретную формулу, прямой путь к реализующему файлу, контрпример/тест, составимый commit SHA и статус; никакого автоматического признания всех исправлений правильными.
