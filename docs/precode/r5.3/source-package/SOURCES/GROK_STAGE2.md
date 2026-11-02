# GROK_POST_ASTRA_STAGE2_INDEPENDENT_COMPARATIVE_AUDIT_FULL.md

**Независимый сравнительный аудит UNO — полный Этап 2**  
Дата: 2026-11-02  
Stage 1 зафиксирован без изменений.  
Охват: финальная Astra (B2), R4 IR01–IR08, D01–D10, X01–X12, B01–B14, R5 proposals (после собственного анализа).  
Production-код не писался. PRE-CODE BASELINE не утверждается.

---

## A. Проверка R1/R2 → финальная Astra

### R1-01 (q=0 per-frame abstain)
- **Источник:** ASTRA_01 / ASTRA_05.  
- **Проблема:** длинные потоки при q=0 могут «выживать» без прогресса.  
- **Исправление в финальной Astra:** per-event admission требует q≥1 или explicit resource abort; turn-level admission отделён.  
- **Статус:** CONDITIONAL.  
- **Остаточная предпосылка:** корректный учёт residual budget и fairness scheduler.  
- **Контрпример:** не построен при заявленных bounds; при нарушении residual — возможен starvation (вне спецификации).

### R1-02 (loss от отказа / incomplete trajectory)
- **Источник:** ASTRA_03 L3 / L3a.  
- **Проблема:** модель могла экономить compute отказом и исчезновением targets.  
- **Исправление:** censored / incomplete trajectories не дают free pass; coverage constraints и terminal loss.  
- **Статус:** CONDITIONAL.  
- **Остаточная:** требует корректного 1{Z=j}/π_j и π_j>0.

### R1-03 (allocated/free/frozen rows)
- **Источник:** ASTRA_02.  
- **Проверка:** 24 active verbs, E={3…23}, free = alloc − 318(d+1). Градиенты маскируются, экспорт сохраняет нули.  
- **Статус:** PROVEN_LOCAL.  
- **Контрпример:** отсутствует при соблюдении mask.

### R1-04 (Frozen P=0 vs stop-gradient)
- **Источник:** ASTRA_03 / ASTRA_04.  
- **Исправление:** P обновляется только по verified path; stop-gradient на replay не создаёт ложный meta-gradient.  
- **Статус:** CONDITIONAL.  
- **Остаточная:** точный derivative только для заявленного objective.

### R1-05 (power при δ=.02 / 0)
- **Источник:** ASTRA_06 / NCR.  
- **Статус:** REQUIRES_DATA. Sample-size и independent units не закрыты без эксперимента.

### R1-06 (E5 costs)
- **Источник:** ASTRA_05.  
- **Исправление:** разделение additive (CPU/J/IO) vs peak (RAM/disk) vs critical-path walltime.  
- **Статус:** CONDITIONAL (спецификация); измерения отсутствуют.

### R1-07 (CTC / TTS / Unicode / wake)
- **Источник:** ASTRA_01 / ASTRA_03.  
- **Статус:** CONDITIONAL. Заявленные уточнения присутствуют; полное закрытие зависит от данных.

### R2-01 (L3a coverage)
- **Источник:** ASTRA_03.  
- **Исправление:** условный coverage, 1{Z=j}/π_j, matching dual.  
- **Статус:** CONDITIONAL. Формула в финальной ASTRA_03 проверена; повреждённая историческая версия не используется.

### R2-02 (qR·qY ≥ u_min)
- **Источник:** ASTRA_03 / ASTRA_05.  
- **Исправление:** internal verbs 0–2 без ticket/OS/P.  
- **Статус:** CONDITIONAL.

### R2-03 (UI_TYPED_ACTION containment)
- **Источник:** ASTRA_05.  
- **Статус:** CONDITIONAL на A_ui / A_cap.

### R2-04 (CURRENT_ALL vs OBSERVED_ALL)
- **Источник:** ASTRA_01 / ASTRA_04.  
- **Статус:** CONDITIONAL. Асинхронные readbacks требуют temporal consistency (epoch/ticket).

**Итог по R1/R2:** большинство CONDITIONAL / PROVEN_LOCAL. Универсальных закрытий нет. «10 замечаний закрыты» — только на уровне спецификации при предпосылках.

---

## B. IR01–IR08 — доказательства

### IR01 — Masked Lipschitz
- **Контрпример:** два состояния, отличающиеся только в неактивном блоке \(M_j=0\). После шага разница сохраняется → Lipschitz ≥ 1.  
- **Корректный коэффициент:**  
  \[
  c_M = \max_j \{1 - \alpha M_j (1-\gamma)\}.
  \]
- Full-mask: \(c=0.95\). Sparse: \(c_M=1\).  
- **Статус:** STILL_FAIL для глобального sparse bound. Full-mask и fair-sweep теоремы сохраняются.  
- R5 proposal \(c_M\) корректен при фиксированной маске; ломается при state-dependent adaptive selector.

### IR02 — Memory aggregation
- **Контрпример:** два записи с одинаковым key, values \(v\) и \(-v\), равные веса → \(r=0\). Noninjective.  
- Raw payload / RetrieveExact / conflict key в текущей S4 не специфицированы полностью.  
- **Статус:** STILL_FAIL (семантика). R5 — предложение, не закрытый ABI.  
- Дополнительные риски: ABA, false timestamp, top-k limit, поздний revoke — не закрыты.

### IR03 — WAKE / SENSOR
- V2.2: 13 классов (включая WAKE, SENSOR). Astra D01: 12 rows.  
- Тензоры \(W_{\rm wake}\), \(W_{\rm sensor}\) есть, отдельных strata/loss/false-wake метрик нет.  
- **Статус:** STILL_FAIL (scope). Требует owner choice: required или optional + freeze.

### IR04 — Owner authentication
- Threat model: A_cap предполагает доверенный owner/controller input.  
- Что не гарантируется: lock state, multi-user, overlay/tapjacking, consent expiry, session binding.  
- **Статус:** OPEN (B08). Neural head не может создавать owner identity.

### IR05 — Cyclic-prefix vs arbitrary
- \(n_b=16\): cyclic-prefix = \(16\times15 + 1 = 241\) nonempty masks.  
- Arbitrary nonempty = \(2^{16}-1 = 65535\).  
- **Статус:** Design substitution. Не эквивалентно. Требует owner acceptance + quality comparison. Expressivity loss без data не выводится.

### IR06 — SAF / offline
- App без INTERNET, но document provider может fetch remote.  
- **Статус:** Boundary gap. Нужна explicit local-provider-only policy или opt-in вне offline guarantee.

### IR07 — LR2/H2 ABI
- B2 counts независимо подтверждены (d=512/1024/1536/2048).  
- LR2/H2 — derived, не official manifests / quant certificates.  
- **Статус:** PARTIAL. B04 не полностью закрыт до export/dequant parity.

### IR08 — Text event cost
- Full 128-token event включает encoder + memory + selector + heads > F+vocab lower bound.  
- Числа согласованы. Не смешивать с latency/joules.  
- **Статус:** PROVEN_LOCAL (арифметика).

---

## C. Полный реестр

### D01–D10 (кратко, полный статус)
- D01: NOT PASS (thresholds + WAKE/SENSOR).  
- D02: CONTRACT RESOLVED / OPEN (trained + manifests).  
- D03: NOT PASS (data).  
- D04: PARTIAL (conflict + payload).  
- D05: CONDITIONAL (owner auth + A_cap tests).  
- D06: NOT PASS.  
- D07: NOT PASS (A52).  
- D08: SPECIFIED / UNTESTED.  
- D09: PARTIAL (SAF + ABI).  
- D10: NOT PASS.

### X01–X12
- X01: Conditional (cyclic-prefix ≠ arbitrary).  
- X02–X08, X10: mostly Conditional / Resolved на спецификации.  
- X09: Updated (full event MAC).  
- X12: OPEN.

### B01–B14
- OPEN: B01–B03, B05–B08, B09 (memory), B10, B13.  
- PARTIAL: B11.  
- Resolved as artifacts: B04 (partial), B12.  
- NOT AUTHORIZED: B14.  
B04 не объявляется полностью закрытым до реального export/dequant/parity.

### Сквозные worst-case traces
1. **STOP после dispatch:** P не обновляется; late readback → UNKNOWN.  
2. **Crash до/после physical effect:** PREPARED / MAY_HAVE_EXECUTED; no blind retry.  
3. **Stale readback:** epoch/ticket mismatch блокирует P.  
4. **Concurrent manual action:** external observation; не автоматический success.  
5. **Contradictory memory:** текущая агрегация может обнулить (IR02).

Безопасность опирается на A_cap, A_tx, A_fs, durable L/D.

### B2 / LR2 / H2
- Rank-64 не эквивалентен B2 (span-129 counterexample).  
- Выбор только по MAC/параметрам запрещён. Обученных весов и on-device benchmarks нет.

### NCR-EVO
- G_const immutable. Termination от bounded loops, не correctness.  
- HT/IPW требуют positive inclusion. Adaptive holdout bias не закрыт alpha-spending.  
- Self-regeneration PASS не объявляется.

---

## D. Итоговый вердикт

| Область | Статус |
|---------|--------|
| Математика локальных свойств | CONDITIONAL |
| Доверенная граница | CONDITIONAL (A_cap) |
| Обучение | REQUIRES_DATA |
| Память | PARTIAL |
| Android / A52 | REQUIRES_DATA |
| NCR-EVO | SPECIFIED / UNTESTED |
| Общий pre-code | **NOT BASELINE** |

**Оставшиеся блокеры (приоритет):**
1. W4 → \(c_M\).  
2. Memory conflict + raw payload semantics.  
3. WAKE/SENSOR decision + SAF offline policy.  
4. Owner authentication contract.  
5. Legal data + thresholds + A52 measurements.  
6. Trained Θ + locked evaluation.

**UNO PRE-CODE BASELINE не утверждается.**  
Решение владельца.

---

**Конец полного отчёта Этапа 2.**  
Все проверки выполнены независимо. R5 proposals учтены как кандидаты, не как baseline.
