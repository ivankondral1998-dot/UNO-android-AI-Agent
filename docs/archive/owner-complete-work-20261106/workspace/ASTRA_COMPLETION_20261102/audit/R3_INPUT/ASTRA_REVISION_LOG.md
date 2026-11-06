# Журнал исправлений математического завершения

## B2 до независимого R1

Сохранён весь Workv1.1 и original brief. Новый проект добавил причинный clock/outbox, immutable snapshot, input-aware memory query, canonical proposal-conditioned h_issue, q_R observability, единый conditional compute, полные shapes и ресурсные сценарии, loss/gradient/данные, crash reconciliation, Android capability matrix и D01–D10, ограниченный NCR-EVO и falsification.

## Независимый R1 — FAIL

Frozen входы: audit/R1_INPUT. Неизменённый отчёт: audit/R1_REVIEW.md. Найдены шесть исправимых ошибок: per-frame q0, нулевая цена отказа, ложный all-trainable count, detached replay gradient, practical power, peakRAM sum. Это существенные результаты аудита, а не косметические замечания.

## Исправления для R2

01: только непустые masks после turn admission; halt завершает inner computation; β только turn-end.
03: L3a task/coverage objective; fixedP0 offline; frozen-row optimizer; Unicode alphabet normalization.
02/04/07: allocated/free/frozen rows, 24 verbs/21eligible endpoints, Pactive21d; machine tensor manifest и exact arithmetic обновлены.
05: GL crop в физических sample coordinates и повторный left padding; payload index/COW/WAL/image/stream/tokenizer/DSP allocations; additive work и live memory раздельно.
06/08/09: practical power26268, δ0power9457; peak capacities как sup live; доказательства/матрица согласованы.
10/final: сохраняют PENDING до реального заключения reviewer.

После R2 любое изменение нормативных документов требует повторного чтения и hashes; старые отчёты не перезаписываются.

## Дополнительные замечания R2

Независимый reviewer до прерывания по лимиту сообщил ещё две ошибки. Его frozen R2_INPUT сохранён. (1) L3a joint coverage не равнялась per-stratum coverage: заменено на indicator/π_j, указан matching unbiased dual estimator,π_j>0 и default candidate c_j=.9. Контрпример12 классов сохранён в03. (2) log acceptance score нельзя сравнивать с положительным probability threshold: зафиксированы product≥u_min/logscore≥log(u_min), а internal0–2 обходят endpoint-heads и завершаются без dispatch/P update. Новые строкиN81/N82 отражают эти изменения. Полный независимый reread ещё требуется.

Дополнительно R2 выявил bypass effect policy через generic UI-click и неоднозначную temporal conjunction. В05 закреплён effect-level registry, app-private local surfaces и A_ui; неизвестные downstream effects запрещены. В01/07 закреплены CURRENT_ALL и OBSERVED_ALL; разновременные TRUE не доказывают одновременность. Контрпримеры добавлены в08, обязанностиN83/N84 в09.

## R3 freeze

После полного R2_REVIEW внесены все четыре исправления и ограничение сравнения terminal+cost. Входы R3 зафиксированы отдельным MANIFEST. Старые R1/R2 не изменялись; final PASS пока не объявлен.
