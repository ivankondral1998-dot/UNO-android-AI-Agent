# UNO B2 / NCR-EVO — математический и предкодовый пакет

Дата: 2026-11-02. Итоговый статус повторного независимого аудита: **PENDING**. Производственная реализация, обучение и release не допущены этой работой.

## Что подготовлено

Полная кандидатная система одного организма: причинный event kernel; shared recurrent F; новые мультимодальные веса; выбор объёма вычислений; цели и планирование; память, онлайн-пластичность и сохранение; native verification и STOP; алгоритмы обучения; Android ABI и ресурсы; отдельный цикл структурного NCR-EVO. Это не маленький прототип и не классификатор вместо UNO.

|Документ|Содержание|
|---|---|
|ASTRA_00_README_AND_SOURCE_PROVENANCE.md|Прочитанные оригиналы, ограничения выводов, происхождение|
|ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md|Полное состояние, время, переходы, F, решения, goals, Verify|
|ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md|Все shapes, allocated/free, инициализация, B2/LR2/H2, quantization|
|ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md|Loss, gradient, coverage, optimizer, данные, FLOP/VRAM|
|ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md|P/M, локальный descent, regret, forgetting, transactions, repair|
|ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md|24 verbs, полномочия, DSP, RAM/disk/MAC/traffic/energy|
|ASTRA_06_NCR_EVO_MATH_AND_FALSIFICATION.md|DSL, surrogate, QD, selection, structural generations, cost/power|
|ASTRA_07_PRECODE_ENGINEERING_D01_D10.md|D01–D10, binary contracts, toolchain, quality/release gates|
|ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md|Доказательства с предпосылками и конструктивные опровержения|
|ASTRA_09_UPDATED_MATRIX_M01_M44_PLUS.md|Исходные44 утверждения и новые N45–N80|
|ASTRA_10_INDEPENDENT_REDTEAM_REPORT.md|Независимый blind/R1/R2 аудит и область заключения|
|ASTRA_11_CODEX_FUTURE_EXECUTION_BLUEPRINT.md|Порядок будущей реализации и независимые oracle checks|
|ASTRA_12_UNKNOWNS_DATA_AND_HARDWARE_REQUESTS.md|Конкретные неизвестные, способы измерения и блокеры|
|ASTRA_REVISION_LOG.md|Исправления без стирания отрицательных результатов|

`evidence/` содержит воспроизводимую арифметику и tensor manifest; `sources/` — все30 оригинальных файлов без изменений; `audit/` — самостоятельные отчёты и frozen snapshots.

## Численные результаты и их пределы

|d|Allocated slow|Free slow|Raw FP16 MiB|Mixed INT8 ABI MiB|F MAC/полный шаг|
|---:|---:|---:|---:|---:|---:|
|512|23 015 887|22 852 753|43.899321|22.268860|4 456 448|
|1024|55 451 639|55 125 689|105.765608|53.285583|17 301 504|
|1536|97 340 959|96 852 193|185.663145|93.318054|38 535 168|
|2048|148 683 847|148 032 265|283.591932|142.366028|68 157 440|

Это подсчёт форм и хранения, не доказательство достаточности размера. Дляd1024 fullK8 ASR-сценарий требует14.21G MAC/s до DSP/контроллера; явные FP16 allocations составляют примерно153.48MiB до capture/backend/controller/driver/snapshot extras. Реальный A52 peakPSS, latency и joules не измерялись. Частичная сумма не названа полной RAM.

Fixed-z inner map contractive при указанных нормах, но c⁸≈.6634: восемь шагов не обеспечивают1% fixed-point accuracy и не доказывают устойчивость всей среды. Online P имеет локальный projected descent для текущего verified sample; универсальный no-forgetting опровергнут. Регенерация требует достаточного сохранённого reference.

NCR-EVO определён как ограниченный поиск структурных алгоритмов. Ручной trace c0→c1/c1b→c2→c3 содержит доказательство corrected algorithm и контрпримеры. Экспериментального ускорения/превосходства нет. Приtrue effect.05 для practical threshold.02 консервативный проект с двумя comparisons требует26268 независимых парных единиц;9457 относится только к threshold0.

## Решение о следующем этапе

Кандидатный математический проект подготовлен; окончательное заключение зависит от финального независимого reread. Доказанного достаточного d, обученных весов, лицензионного корпуса, утверждённого распределения задач и замеров A52 нет. Эти входы не выводятся из числа параметров. Пакет содержит способы их получения и правила PASS/FAIL; неизвестные не заменены выдуманными измерениями.

Старые46/46 тестов не используются как доказательство архитектуры. Новое ядро, APK, обучение и NCR experiments не запускались; GitHub Actions, ветки и JarvisLab не менялись. Следующий допустимый предмет обсуждения — конкретные data/device/quality inputs по12; эта работа не даёт молчаливого разрешения на производственный код.
