# UNO — атрибуция каркаса Grok / Work и независимая проверка математики B2

**Дата:** 2026-11-07. **Класс:** SOURCE_PROVENANCE + CONDITIONAL_MATH_AUDIT. **Владелец не утверждал модель B2.** Это НЕ новые правила проекта: действующий источник разрешений — корневой `AGENTS.md`.

## 1. Что реально произошло

| Объект | Фактически доступный источник | Проверяемое заключение |
| --- | --- | --- |
| `UNO_GROK_CORRECTED_MINIMAL_ORGANISM_PAPER_FOR_OWNER_REVIEW.md`, 2026-11-03 | Локальный архив `UNO_GROK_CORRECTED_MINIMAL_ORGANISM_2026-11-03.zip`, SHA-256 `1b6eaf63c731313bf0c7840bda22c3b53269cf7195f4688ee5feef9f1cb1a523` | **Бумажная** Grok-ревизия. SHA документа `7d762c32aa533e8ce4bfd4f42a8f60b2de4c1b4e8d6999ed6cf8b696c491dd1b` совпадает с записью `SHA256.txt` и отдельным файлом. В документе прямо указано: «Код не писался». |
| `UNO_UNOVYRA_FRAMEWORK_R3_ASTRA_COMPATIBLE.md` | Упомянут в `docs/implementation/2026-11-07_WP01_SCAFFOLD_REUSE.md` | Его отдельный оригинальный файл/байты в этом проходе **не установлен**. Не заявлять побайтовую идентичность или полное прочтение R3. |
| `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip` | Локальный полный Work handoff, 841121 байт, SHA-256 `4f9f59123b40a47a4bc2783f3633f0314a69fbac8c7cdb638dad3b3a1efc59b1` | Содержит `06_NON_NORMATIVE_OLD_SCAFFOLD`: Python B2 `reference/uno_ref`, Kotlin `:core`, Android shell/заглушки, тесты. Наличие в Work-архиве **не доказывает персональное авторство каждого исходного файла**. |
| Текущий `android/` | Ветка `feat/uno-foundation-hardening-20261107`; источник `feat/uno-production-foundation-20261106` | Переиспользует **Kotlin/Android-подмножество Work B2 scaffold**, а не полноценную Python F-модель; B2 веса, F, trained model, JNI/Binder inference НЕ перенесены. |
| `UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW(1).md` | Локальный Work owner-review paper, SHA-256 `b4a65751806d96573d21e727f817582db62764862b19131ca892ddece39affb2` | Более развёрнутые расчёты B2 и компактных кандидатов; только историческая **не утверждённая** кандидатная спецификация. |

**Побайтовая проверка происхождения Kotlin:** архивный `Contracts.kt` = Git blob `ecd3d3e6ae5f677d817223e8dcbb6e086f4b30d8`; `Controller.kt` = `c094f331904cc1638141c6f4be8f3b7b02ba91bc`; `Memory.kt` = `7c862cb56259d42b2c4d33696ace7fd16f1bc689`. Они совпали с объектами исходной feature-ветки до hardening. Архивный scheduler: `4c342a79368fee331065bb3d98494d241d87f631`; в рабочей ветке позже изменён, поэтому не заявлять тождество его текущих байтов. Все исходники исторического архива сохранены.

## 2. Проверенные математические утверждения

Проведён **новый** независимый арифметический расчёт из выражения в Work owner-review paper (не просто доверие старому PASS). Использованы размеры `d,V,b,J,χ,m_mem,rank` и отдельная свёртка Kotlin/Python manifest-классов. Для B2-512/1024/1536/2048 старый `reference/uno_ref/weights.py` независимо перечисляет формы; подсчёт точно совпал с исторической формулой.

| Кандидат | Allocated | Descriptors | TEXT K8 MAC | Статус |
| --- | ---: | ---: | ---: | --- |
| B2-1024 | 55 451 639 | 198 | 175 448 160 | ARITHMETIC_PASS |
| B2-512 | 23 015 887 | 118 | 54 161 472 | ARITHMETIC_PASS |
| C384 | 8 698 053 | 68 | 17 403 448 | ARITHMETIC_PASS |
| C256 | 3 339 727 | 78 | 7 256 128 | ARITHMETIC_PASS |
| C256R32 | 3 012 047 | 94 | 4 634 688 | ARITHMETIC_PASS |

Последние три строки — **конфигурации гипотетических кандидатов**, не подтверждение их языкового качества. Ни один из расчётных MAC не есть измеренный p95, RAM или энергия A52. Отдельно `E_text=Vd` может доминировать расход даже при узком F.

- **Фиксированная маска:** при `α=0.5, γ=0.9` аналитическая условная граница `c_M=max_j[1−α M_j (1−γ)]` даёт `0.95` при всех активных блоках и `1.0` при хотя бы одном выключенном. Это не global agent stability. `PROVEN_LOCAL` при условиях на нормы, фиксированный `z` и маску.
- **Адаптивный selector:** пример `T_+(x,1)=(x,0.5)` при `x>0`, `T_-(x,1)=(0.5x,1)` при `x≤0` даёт отношение расстояний `0.5/(2ε)` для входов `(+ε,1)` / `(−ε,1)`; оно не ограничено при `ε→0`. Глобальная контракция из fixed-mask условия **не следует**. `COUNTEREXAMPLE`.
- **Маски:** для `n_b=16`: cyclic contiguous prefix с произвольным стартовым сдвигом допускает `16·15+1=241` уникальных непустых масок; все непустые битовые маски — `2^16−1=65535`. Не заменять одно пространство другим без изменения политики и повторной проверки.
- **Точная память:** семантическая средняя от `v` и `−v` с равными весами равна нулю. Обратимый recall из агрегата невозможен; нужен отдельный `RetrieveExact`. `PROVEN_LOCAL`.
- Старый Python reference: `pytest -q` с `OPENBLAS_NUM_THREADS=1` завершился **61 passed** (на хосте; синтетические тесты, не обученный интеллект).

## 3. Конкретные переносимые ошибки и пробелы

| ID | Доказательство или контрпример | Критичность и граница |
| --- | --- | --- |
| MATH-C01 — *неполная проверка бюджета* | В `reference/uno_ref/config.py` `ResourceBudget.charge()` изменяет лишь `remaining_mac`. При `remaining_bytes=0, remaining_tokens=0, remaining_ns=0`, но большом MAC `NeuralEngine.tick(TEXT, d=64, forced_prefix=1, forced_k=1)` реально возвращает `COMPUTED_UNTRAINED` и списывает 125124 MAC. | **FAIL** для будущей гарантии лимитов байтов/токенов/времени. Приведённый код — только исторический Python reference, не Android runtime. Нельзя переиспользовать как resource admission без исправления и трёх независимых oracles. |
| MATH-C02 — *неясная семантика пустого exact recall* | `MemoryStore.exact` при пустом индексе выдаёт `COMPLETE` с 0 records; новая Kotlin-модель различает `NOT_FOUND`. | **CONTRACT_DIVERGENCE**: надо согласовать ABI/UX до постоянной памяти. Сам по себе `COMPLETE empty` не доказывает ложную запись; опасность — если потребитель интерпретирует как наличие факта. |
| MATH-C03 — *бумажная нейронная модель ≠ Android runtime* | В Kotlin `:core` есть `NeuralPort` и `NoWeightsNeuralPort`, в `:app` только placeholder isolated service; `F` и обученные веса в APK отсутствуют. | **SPECIFIED_UNTESTED/NOT_IMPLEMENTED**, нельзя утверждать перенос Grok/Work математики в UNO 1.0. |
| MATH-C04 — *WAKE не доказан* | `W_wake[1,32]` из исторического manifest использует metadata; отдельный acoustic wake detector не реализован в действующем APK. | **NOT_IMPLEMENTED**, отдельная проверка quality/false-wake/idle-energy. |
| MATH-C05 — *trust boundary* | Старый Kotlin `TrustController` был имитацией OS authority; после hardening реальный native effect, owner authentication, durable outbox и independent Android readback всё ещё отсутствуют. | **BLOCKER** на подключение привилегированного Android port, несмотря на host-тесты. |
| MATH-C06 — *устаревшая пластичность* | `reference/uno_ref/learning.py` содержит P update на тестовом verified path. | Исторический исследовательский механизм; по `AGENTS.md` от 07.11.2026 самопереписывание весов/двухскоростное обучение НЕ входит в runtime UNO 1.0. Не подключать автоматически. |

## 4. Операционное правило для дальнейшей разработки

Сначала сверять **требование владельца → бумажную формулу/контракт Grok/R5.3 → независимый контрпример → код Python B2 → Kotlin/Android interface → тест → реальное устройство**. Не переносить legacy F, B2 ширину, модель, runtime, weight format, quant thresholds или fast P как принятый продуктовый выбор. Каркас должен оставаться **единым интеллектуальным организмом** с отдельной неинтеллектуальной доверенной Android-границей.

Без нового решения владельца не обучать веса, не включать в UNO 1.0 runtime-пластичность, не объявлять R5.3 approved и не запускать GitHub Actions. `main` не изменять.

**Воспроизводимый счётчик:** `python3 docs/audits/2026-11-07/verify_b2_geometry_v1.py` (Python stdlib only). Его 5 конфигураций и условные границы пересчитаны локально; новый APK, training или Android benchmark этот инструмент не проверяет.\n\n**Граница аудита:** source bytes и host math подтверждены; отдельные байты Grok R3 и невыложенные исходные ZIP 6–7 ноября не удостоверены; Android Gradle-сборка **после hardening** и испытание на A52 не выполнялись. Исходный полный Work scaffold остаётся в своем ZIP, не является нынешним product runtime.
