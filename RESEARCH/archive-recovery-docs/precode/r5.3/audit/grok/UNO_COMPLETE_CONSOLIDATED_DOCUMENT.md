# UNO — Полный сводный документ
**Кандидатная математическая спецификация и аудит**  
Дата: 2026-11-02  
Статус: PRECODE_CANDIDATE_READY_FOR_OWNER_REVIEW  
**НЕ OWNER_APPROVED_PRECODE**

---

## 1. Независимый Stage 1 (слепой аудит)

### Ключевые находки
- **S1-01 HIGH:** Adaptive selector не имеет глобального Lipschitz. Контрпример с пороговым переключением. Исправление: \(c_M = \max_j(1-\alpha M_j(1-\gamma))\) только для фиксированной маски.
- **S1-02 HIGH:** Агрегация памяти non-injective (\(v\) и \(-v\) → \(r=0\)).
- **S1-03 MEDIUM:** Текущий WAKE — metadata-only, не акустический.
- **S1-04 MEDIUM:** SENSOR покрытие неполное.
- **S1-05 HIGH:** Ресурсы A52 не измерены.
- **S1-06 MEDIUM:** Verified completion ≠ причинный эффект.

Параметры B2 независимо пересчитаны и совпадают с заявленными.

---

## 2. Stage 2 — Сверка и исправления

Все находки Stage 1 подтверждены историческими аудитами (IR01–IR08).  
Нормативная математика приведена к согласованному состоянию в R5.3.  
Исторические утверждения APPROVED/COMPLETE без подтверждения владельца помечены как ошибочные.  
PRE-CODE BASELINE владельцем не утверждался.

---

## 3. Нормативная спецификация R5.3

### Контракция
\[
c_M = \max_j \bigl(1 - \alpha M_j (1-\gamma)\bigr)
\]
Full mask: 0.95. Любой неактивный блок: \(c_M=1\). Adaptive selector — без глобальной гарантии.

### Параметры B2
| d | Allocated | Free |
|---|-----------|------|
| 512 | 23 015 887 | 22 852 753 |
| 1024 | 55 451 639 | 55 125 689 |
| 1536 | 97 340 959 | 96 852 193 |
| 2048 | 148 683 847 | 148 032 265 |

### Память
Режимы: COMPLETE / CONFLICT / TRUNCATED / UNKNOWN / DENIED.  
Точный recall только через RetrieveExact. Агрегация не lossless.

### WAKE / SENSOR
Owner decision: Required (с метриками) или Optional (freeze + запрет claims).  
Текущий `w_wake` не является acoustic wake.

### Authority
STOP до linearization блокирует dispatch. После — не отменяет in-flight.  
Success только по fresh readback + matching ticket/epoch. No automatic retry. Causal ≠ receipt.

### Остальное
- β — маргинальные факторы, не полный belief.
- NCR-EVO изолирован, self-regeneration не доказан.
- Ресурсы A52 — REQUIRES_DATA.
- Cyclic-prefix (241) ≠ arbitrary (65535). Owner choice.

---

## 4. Решения для владельца

1. WAKE и SENSOR — обязательные или опциональные?
2. Политика масок — cyclic-prefix или произвольные подмножества?
3. Пороги качества \(q_j\).
4. Стартовый размер модели (после измерений на телефоне).

**Что доказано:** ограниченность состояния, формы весов, внешняя authority, non-injectivity памяти, отсутствие глобального Lipschitz у adaptive selector.  
**Что требует данных/телефона:** качество, latency, энергия, реальный wake, обучение.

---

## 5. Handoff для реализации (после утверждения)

Инварианты кода:
- Authority внешняя.
- STOP-семантика соблюдается.
- Success только по свежему readback.
- No automatic retry.
- P только на verified path.
- Memory aggregation не lossless.
- WAKE/SENSOR строго по выбору владельца.

Минимальный slice: ввод → proposal → подтверждение → одно действие → readback → P или UNKNOWN.

---

## 6. Открытые gates

- Owner choices (WAKE/SENSOR, masks, thresholds).
- Лицензированные корпуса.
- Измерения A52.
- Обученные веса и locked evaluation.
- Конкретный протокол owner authentication.

---

## Вердикт

**PRECODE_CANDIDATE_READY_FOR_OWNER_REVIEW**

Математически согласованный кандидат готов для проверки владельцем.  
PRE-CODE BASELINE не утверждён.  
Переход к коду возможен только после явного решения владельца.

Production-код не писался. Репозитории не изменялись.