# UNO R5.3 — Полная нормативная кандидатная спецификация
**Статус:** PRECODE_CANDIDATE_READY_FOR_OWNER_REVIEW  
**НЕ OWNER_APPROVED_PRECODE**  
**Дата:** 2026-11-02  
**Основание:** Astra Final B2 + независимый Stage 1 + Stage 2 crosswalk + исправления IR01–IR08

---

## 1. Системная модель и состояния

\[
X = (w, \tau, S, T, R)
\]
\[
S = (v, \Theta, s, g, \beta, P, M, Q, H_{\rm ctx}, U)
\]
\[
T = (\nu, e, {\rm stop}, {\rm owner}, {\rm cap}, L, D)
\]

- \(s, g \in [-1,1]^d\), \(\beta \in [0,1]^{128}\), каждая строка \(P\) в \(\ell_2\)-шаре радиуса 1.
- \(\Theta\) и граф неизменны в runtime.
- \(\beta\) — 128 маргинальных факторов из data dictionary, **не** полный Bayesian belief.
- Время \(\tau\) — монотонные наносекунды сессии. Wall-clock не авторизует действия.

### Causal clock (S2–S3)
\[
K_{\rm race}(dw', d\Delta, d\eta \mid w, S, T, R, u_R),\quad 0 \le \Delta \le d_R
\]
\[
(S^+, T^+, R^+, a) = \delta(S, T, {\rm Enqueue}(R, \eta, \Delta), {\rm head})
\]

STOP-latch читается перед каждым primitive и dispatch.  
После linearization STOP не обещает отмены already-in-flight эффекта.

---

## 2. Контракция и селектор (исправление IR01 / S1-01)

Для **фиксированной общей маски** \(M\):

\[
c_M = \max_j \bigl(1 - \alpha M_j (1 - \gamma)\bigr)
\]

**Доказательство (локальное):**  
Для каждой координаты  
\[
|(T_M h)_j - (T_M h')_j| \le (1 - \alpha M_j)|\Delta h_j| + \alpha M_j |\Delta F_j| \le [1 - \alpha M_j(1-\gamma)]\|\Delta h\|_\infty.
\]
Максимум по \(j\) даёт \(c_M\).

- Полная маска (\(\alpha=0.5\), \(\gamma=0.9\)): \(c_M = 0.95\).
- Хотя бы один неактивный блок: \(c_M = 1\).

**Контрпример adaptive selector:**  
\(d=2\), \(F=0\), \(\alpha=1/2\). Селектор: \(M=(1,0)\) при \(h_1>0\), иначе \((0,1)\).  
Для \(h=(\varepsilon,1)\), \(h'=(-\varepsilon,1)\): начальная дистанция \(2\varepsilon\), конечная \(1/2\), отношение \(\to\infty\).  
**Нет универсальной конечной Lipschitz-константы.**

Fair-sweep валиден только при одинаковом пути масок и фиксированном \(z\).

---

## 3. Тензорный реестр B2 (подтверждён независимым расчётом)

Параметры: \(V=32768\), \(m=128\), \(\chi=4\), \(J=2\), \(b=64\), \(A=128\), \(H=902\).

\[
P_{\rm alloc} = Vd + 951d + 2d^2 + 4md + J[2\chi d^2 + \chi bd + (\chi+1)d] + H(d+1) + V + n_b(2d+5) + 33
\]
\[
P_{\rm free} = P_{\rm alloc} - 318(d+1)
\]

| \(d\) | Allocated | Free | Frozen |
|-------|-----------|------|--------|
| 512 | 23 015 887 | 22 852 753 | 163 134 |
| 1024 | 55 451 639 | 55 125 689 | 325 950 |
| 1536 | 97 340 959 | 96 852 193 | 488 766 |
| 2048 | 148 683 847 | 148 032 265 | 651 582 |

24 active verbs. Endpoint heads: только строки 3–23 обучаемы. Остальные frozen zero.  
Быстрая \(P\) (\(Ad\)) не входит в \(\Theta\).

---

## 4. Память (исправление IR02 / S1-02)

Агрегация:
\[
r = \sum_{i \in I} \omega_i v_i
\]
**Не является lossless.**

**Контрпример:** две записи с одинаковым key, значениями \(v\) и \(-v\), равными весами → \(r = 0\).

Нормативные режимы результата:
- `COMPLETE`
- `CONFLICT`
- `TRUNCATED`
- `UNKNOWN`
- `DENIED`

Точный recall — только через явный путь `RetrieveExact` с provenance, TTL/boot generation, conflict key и snapshot consistency.  
Второй интеллектуальный сервис не вводится.

---

## 5. WAKE и SENSOR (IR03 / S1-03, S1-04)

**Owner decision (обязателен выбор одного варианта):**

### Вариант A — Required
- WAKE research baseline: microphone → VAD → PCM → \(W_{\rm audio}\) → shared \(F\) → CTC → deterministic phrase grammar → wake proposal.
- Метрики: false activations/hour, false rejects, activation latency, idle energy.
- Если общий ASR слишком дорог — требуется отдельная acoustic wake-head (\(1\times d\)) с полным пересчётом manifest.
- SENSOR: typed dictionary каналов, SI units, ranges, freshness TTL, missing-mask semantics (mask=0 ≠ измеренный ноль).

### Вариант B — Optional
- Пути заморожены. Claims о функциональности запрещены.

Текущий `w_wake` (\(1\times32\), metadata-only) **не называется acoustic wake**.

---

## 6. Обучение

\[
J_{\rm base}(\Theta) = \mathbb{E}\Bigl[\sum_j \lambda_j L_j(\Theta;\tau) + \lambda_c C(\tau)/C_{\rm ref}\Bigr]
\]

Censored / incomplete trajectories не дают free pass. Coverage constraints и terminal loss присутствуют.  
Online \(P\) обновляется только на verified path.  
Данных нет → статус `REQUIRES_DATA`.

---

## 7. Authority, STOP, Readback

- Authority внешняя. Learned weights не расширяют capability.
- STOP до linearization → запрет dispatch.
- После linearization → no promise to cancel in-flight OS effect.
- Verified success только при fresh readback + matching ticket/epoch.
- No automatic retry on mismatch or failed feedback.
- Causal effect ≠ receipt (confounding явно признан).

---

## 8. Ресурсы

Аналитические MAC upper bounds (включая полный text event, audio, vision) существуют.  
Реальные latency, peak PSS, energy, thermal на A52 — `REQUIRES_DATA`.  
Никакой конфигурации не присваивается статус viable без измерений.  
MAC ≠ joules, MAC ≠ latency.

---

## 9. NCR-EVO

Изолированная лаборатория. Bounded typed DSL.  
Termination следует из bounded loops, correctness — нет.  
Self-regeneration не доказан.  
Adaptive holdout bias не закрывается одним alpha-spending.  
Статус: `SPECIFIED_UNTESTED`.

---

## 10. Политика масок

При \(n_b=16\):
- Cyclic-prefix: \(16\times15 + 1 = 241\) nonempty masks.
- Arbitrary nonempty: \(2^{16}-1 = 65535\).

Не эквивалентны. Owner acceptance + same-task quality/resource comparison required.

---

## 11. Полные матрицы

### D01–D10
| ID | Verdict | Blocking |
|----|---------|----------|
| D01 | OWNER_DECISION | Thresholds + WAKE/SENSOR choice |
| D02 | SPECIFIED_UNTESTED | Trained model + official manifests |
| D03 | REQUIRES_DATA | Licensed corpora |
| D04 | PARTIAL | Conflict + raw-payload tests |
| D05 | PROVEN_CONDITIONAL | Owner auth protocol + A_cap traces |
| D06 | REQUIRES_DATA | Quality metrics |
| D07 | REQUIRES_DATA | A52 measurements |
| D08 | SPECIFIED_UNTESTED | Sandbox + equal-budget experiment |
| D09 | PARTIAL | SAF offline policy + ABI |
| D10 | OWNER_DECISION | Threat/quality limits |

### X01–X12
| ID | Verdict |
|----|---------|
| X01 | OWNER_DECISION (mask policy) |
| X02 | PROVEN_CONDITIONAL |
| X03–X06, X10, X11 | PROVEN_CONDITIONAL / SPECIFIED_UNTESTED |
| X07, X08, X09 | PROVEN_LOCAL |
| X12 | REQUIRES_DATA |

### B01–B14
OPEN: B01–B03, B05–B10, B13.  
PARTIAL: B04, B11.  
RESOLVED as artifact: B12.  
NOT AUTHORIZED: B14.

---

## 12. Нерешённые вопросы (точный перечень)

1. Owner choice: WAKE/SENSOR Required vs Optional.
2. Owner choice: cyclic-prefix vs arbitrary masks.
3. Owner-approved thresholds \(q_j\) и task battery.
4. Лицензированные корпуса для всех модальностей.
5. Измерения latency / PSS / energy / thermal на целевом A52.
6. Конкретный протокол owner enrollment / authentication / consent expiry.
7. Обученные веса и locked evaluation.
8. Official manifests и quant certificates для LR2/H2 (если остаются кандидатами).
9. SAF offline acceptance policy.
10. Equal-budget experiment для NCR-EVO.

---

## Вердикт

**PRECODE_CANDIDATE_READY_FOR_OWNER_REVIEW**

Все доказанные математические дефекты исправлены с явными формулами и контрпримерами.  
Эмпирические и owner-gates сохранены открытыми.  
**PRE-CODE BASELINE не утверждён.**
