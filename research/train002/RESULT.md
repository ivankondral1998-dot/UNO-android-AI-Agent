# TRAIN-002 — результат подготовки, 15.11.2026

**IMPLEMENTED / HOST_TESTED / CONDITIONAL. Новые CUDA/Windows/quality испытания НЕ выполнены.** В облаке выполнялись только read-only оценка старых весов, короткие контрактные тесты и12 синтетических diagnostic updates для проверки аварийного resume. Матрица нового обучения только подготовлена.

Ветка сохранена: `research/uno-train-001-s4-20261115`. База и контрольная точка TRAIN001: `b371b627ef743b876e13daadf3b57d6013f37652`. По проверенной нумерации текущего дерева/remote train refs TRAIN002 ранее не назначен. Изменены только новые файлы `research/train002`; TRAIN001/main/production/Actions не изменялись. Новых веток, удалений исходников/результатов и переписывания Git history нет.

## Что установлено по TRAIN001

Архив результатов SHA256 `6f39bf1b5a96cfb7a18d48c5c2deb13e3f78c6f5ee18c80502d934998318dcdc`. Checkpoint SHA256 `d85b14a2ab0e6e2c254d1ac45e64c56b28be9b2248a165869632919ef2847404`: step1000, cursor4000, validation-best950. Файлы с Windows-разделителями имён нормализованы без изменения содержимого. Source SHA и все5 входных SHA совпали с прежним пакетом. Полная контрольная запись — BASELINE_TRAIN001.json. Второй большой handoff ZIP не перенесён из-за лимита32MiB; требуемые исходники и данные восстановлены из сохранённых файлов с точным совпадением SHA.

CPU-оценка сохранённого best950 по исходной функции дала полное совпадение исходного отчёта, включая floating MSE:

| Условие | Верно /320 | MSE |
|---|---:|---:|
| full |253|.40702484116153936|
| memory_off |148|.6755877372890198|
| zero_values |148|.6755877372890198|
| erased |163|.6597859503120655|

Это независимая CPU-репродукция оценки; сам CUDA training остаётся SOURCE_REPORTED по предоставленному пользователем запуску. `memory_off` — отключённое чтение уже обученной сети, а не заново обученный baseline без S4. `zero_values` сохраняет attention, но r=0, поэтому в этих уравнениях совпадает с memory_off. Erased меняет исходные наблюдения и пересчитывает source F/память; это другая интервенция.

Выполнены дополнительные inference controls: prefix-random keys235/320, обратная перестановка содержимого221/320, перестановка целых key/value пар253/320. Это не результаты обучения таких контрольных моделей с нуля. У best950 изменились8151/8192 координат Wk и8107/8192 Wv; RMS delta≈.02683/.02923. Это подтверждает фактические обновления, но само по себе не доказывает необходимость каждого матричного обучения.

Экспортированы2240 индивидуальных записей для7 условий: ответы/предсказания, score, правильный/выбранный ID, все распределения attention, причинные номера/порядок/версии/ссылки и observed write fields. Репозиторий содержит компактный `evidence/predictions.jsonl.gz`; ZIP — также полные key/value/source-state tensors для4 основных условий. Остальные полные tensor-traces воспроизводятся audit_previous.py и закреплены SHA в full_trace_manifest.json. Старые журналы не переименованы в новые проверки.

## Почему r5 пока нельзя объяснить только отсутствием порядка

1. **Доказан конфликт вспомогательной цели.** В старом тесте64 группы повторно используют WRITE-prefix между r2/r5; в30 случаях одна и та же запись получает несовместимые targets `value[0]`. До будущего query сохранённый v один и тот же. Пример `.25` против `-1` даёт нижнюю границу среднего weighted value term `.078125`. Это локальное доказательство противоречия supervision, не доказательство невозможности решить задачи общим F.
2. **Старый тест несбалансирован.** В `r5_order/96`0 положительных меток из16; last-record top1=0/16, итоговый ответ4/16. Весь r5: full33/64 и memory_off33/64. Общий прирост памяти здесь приходится на r1–r4, а не на подтверждённое решение порядка.
3. **Информация о порядке присутствует.** Диагностическая ridge-регрессия, настроенная только на240 train-records, на128 исторических test-records декодирует first/second write из key+value с86.71875%, slot sign100%. Это отдельный аналитический probe, не новая runtime-голова и не доказательство, что штатный softmax/decoder умеет воспользоваться этой информацией. Source-state-only результат87.5% отдельно, он не подменяет результат по доступным S4 key/value.
4. Пересечений точных raw episodes/WRITE-prefix между train/validation/test нет. Внутритестовые повторения между rungs и последовательные Java seeds учитываются отдельно. В старом JSON `groups.mse` фактически SSE; новый отчёт даёт SSE и нормированное MSE.

Парный descriptive cluster-resampling по64 историческим seed-группам: full−memory_off≈.3281, интервал[.2625,.390625]. Это **не** подтверждающий population CI: старые seeds/клетки коррелированы и несбалансированы, seed обучения всего один. Полный отчёт в evidence/audit.json. Причины routing/decoding/supervision ещё нельзя ранжировать причинно без новых контролируемых запусков.

## Что реализовано для нового этапа

Chronology: монотонные event IDs, record ordinal, previous/next, previous-version и сохранение всех версий. Нейронное чтение не вызывает neighbor() для выбора ответа. Все прошлые записи остаются в softmax. Один минимальный candidate: `k=tanh(Wk h+.5c(sequence,ordinal,version))`; value и F/S5 прежние. Нет cluster/cell архитектуры, новых обучаемых матриц, ручного gold key или raw-answer shortcut. Границы и производные — MATH.md; это явное исследовательское расширение Astra04, а не утверждение полного тождества исходной формуле. Ω/Adam/clip/LR сохранены; fixed route/K2, Double reference / FP32 master с FP64 projection threshold и cap tolerance2e-6, без S6/AMP/FP16 equivalence.

Новая locked выборка: train864 / validation144 / test1152, seed2026111502, независимые hashed namespaces, точные raw/prefix overlaps0, баланс в каждой family×length cell. Парные complement-примеры хранятся вместе. После erasure пара имеет одинаковый вход и противоположные labels: deterministic accuracy обязана быть50%, проверяется автоматически. Test SHA256 `397f4ee7e2af4780b62cc945dfaeeb6b7b7fbb75b2293373fafbdd770bee2f29`; данные не оценивались моделью основного нового эксперимента.

Сравнения заранее объявлены: original/chrono × legacy/typed, F trained without S4, GRU215, frozen Wk/Wv, random keys, permuted contents;3 seeds,9 arms=27×1000 updates, batch4. Typed протокол одновременно меняет поля и coverage (все writes вместо одной queried записи); это комбинированная интервенция. Clock contrasts держат payload/masks одинаковыми. Новые r6–r9 проверяют предыдущую/следующую/последнюю запись и прошлую версию по публичному anchor/query, одинаковому у всех моделей. Нейронный UNKNOWN/abstain для несуществующих ссылок здесь не обучен.

Общие data/order/update/clip/LR бюджеты; отдельные allocated/active-optimizer parameter counts, timing и CUDA memory. GRU не получает искусственных Astra caps; число параметров не равно compute. Парные hierarchical seed+pair CIs сохраняют общий test draw между seeds и фиксированные family/length strata; по r1–r9 и длинам. Интервалы pointwise/exploratory, без multiplicity correction,3 seeds мало. Новых процентов качества не выдумано.

## Фактические доступные проверки

-12 новых unittest contracts: headers/version retention, balanced/disjoint data, erased-pair identity, baseline loss+all-gradient exact equality с неизменённым TRAIN001 при12/96, candidate finite differences, FP32 vs Double, missing-target/gold independence, bank-pair invariance, freeze/random/no-memory/GRU controls, paired statistics, wrong-arm checkpoint rejection, pinned byte protection, запрет чтения test до завершения study и безопасная начальная публикация.
-12-update diagnostic process test: настоящий forced kill отдельного процесса, exact weights/Adam/CPU RNG/cursor/history/validation-best после resume; resource elapsed/peak намеренно не сравниваются как детерминированные значения. Completed resume не переписывает checkpoint; locked diagnostic test и cached report проверены. Это временный корпус seed42, **не** новый основной тест.
-CPU main training отказал с CPU_MAIN_TRAINING_FORBIDDEN; CUDA Check отказал с CUDA_UNAVAILABLE, успешная квитанция не создана.
-Byte manifest, ZIP CRC/roundtrip, соответствие пакета исходникам и импортов/тестов из распакованного пакета проверены. Python syntax и shell syntax проверены. PowerShell на Windows и реальные CUDA проверки здесь не исполнялись.
-Ревью обнаружило и помогло исправить пропущенную arm/seed attribution; отдельный regression воспроизвёл ошибку до исправления. Инициализация публикуется atomic directory rename только после готового checkpoint0; её прерывание не оставляет ложный опубликованный run. Orphan initialization folders сохраняются.

Checkpoint/optimizer/source/data/config/driver/runtime/RNG/cursor/validation selection связаны; snapshot читает одни и те же pinned bytes. OS locks не позволяют второму writer откатить прогресс. Evaluate не открывает новый тест, пока все27 запусков не завершены; выбор фиксируется до оценки, crash retry/cached report сохраняют pins. Power-loss/fsync каталога, filesystem rollback и полный GPU-driver failure не сертифицированы; SHA не подпись.

## Передача

Единственный актуальный пакет: `/workspace/UNO_TRAIN002_RTX_20261115.zip`, его SHA/размер — evidence/package-final.txt. README.md и Run.ps1 внутри; по умолчанию Check. Suite — только явная команда владельца, максимум1800 секунд на вызов; затем повтор для resume. Никакого основного обучения/007/Actions в облаке не было. CUDA/Windows qualification и вся27-run матрица остаются следующими реальными испытаниями на RTX владельца.

Канонический основной журнал в другой ветке не публиковался: **NOT_PUBLISHED** из-за границ этой задачи (изменения только текущей research-ветки). Готовая запись для append: дата15.11.2026, Codex; задачаTRAIN002; BASEb371b627ef743b876e13daadf3b57d6013f37652; RESULT implementation commit этого этапа (берётся из Git); изменён толькоresearch/train002; факты/evidence/ограничения перечислены выше. Этот RESULT не выдаётся за обновление канонического журнала.
