# R1/R2 — проверка допустимых выводов

| ID | Grok Stage 2 | Независимый вердикт R5.1 | Недоказанная часть |
|---|---|---|---|
| R1-01 | CONDITIONAL | CONDITIONAL: q≥1 после per-event admission либо terminal abort исключает безмолвное q=0; не гарантирует walltime progress | scheduler fairness, deadline, residual accounting |
| R1-02 | CONDITIONAL | CONDITIONAL: учёт `terminal loss/coverage` предотвращает исключение отказов из denominator только при фиксированных issued tasks и непустом observed stratum | исходное распределение задач, selection/inclusion π>0, calibration |
| R1-03 | PROVEN_LOCAL | PROVEN_ARITHMETIC under fixed schema: 24 verbs total (0–23), **21 external** (3–23), 318(d+1) frozen coordinates | фактический экспорт и нули после обучения не проверены |
| R1-04 | CONDITIONAL | CONDITIONAL: P=0 как независимая константа даёт градиент заявленного offline objective; не gradient полного online learning-through-adaptation | отсутствие bias, real retention |
| R1-05 | REQUIRES_DATA | REQUIRES_DATA: sample size bound не доказывает эффект NCR-EVO | независимые unit, power, registered experiment |
| R1-06 | CONDITIONAL | CONDITIONAL: separated accounting for additive work vs peak memory vs critical latency правильно на уровне размерностей | actual hardware primitive costs |
| R1-07 | CONDITIONAL | CONDITIONAL: CTC/TTS/Unicode/wake определены как контракты | реальные licensed data/metric validation |
| R2-01 | CONDITIONAL | CONDITIONAL: inverse-inclusion weight 1{Z=j}/π_j является unbiased лишь для корректно определённого sampling и независимого label/фиксированных assumptions | π=0, adaptivity, unobserved labels, high variance |
| R2-02 | CONDITIONAL | CONDITIONAL: q_R q_Y по правилу произведения есть Pr(R=1,Y=1|H) при калиброванных моделях; internal 0–2 вне OS/P | отсутствие меток R и Y, model calibration |
| R2-03 | CONDITIONAL | CONDITIONAL on A_ui/A_cap. В реальном Android не проверено | UI surface containment / overlay / OS API |
| R2-04 | CONDITIONAL | CONDITIONAL: CURRENT_ALL требует совместный временной срез или валидные stability certificates; OBSERVED_ALL имеет иную семантику | OS evidence provenance, clock/window guarantees |

Все 11 пунктов рассмотрены. Сам по себе ярлык `PROVEN_LOCAL` не означает, что соответствующий экспорт, runtime, policy и обученный вес существуют.

### Уточнение классификации
Из таблицы Grok R1-03 может создаться впечатление о «24 active verbs». Формально 24 слота схемы, но только 21 слот внешнего действия E={3,...,23}; три внутренних verb 0–2 не авторизуются как privileged OS operations. Веса allocation и free/frozen различаются. Прежний parameter manifest Astra остаётся источником арифметики, никаких новых counts из этой формулировки не выводится.
