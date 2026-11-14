# UNO-N0-05 — полный пятиэтапный эксперимент на Samsung A52 (05.11.2026)

**SOURCE:** последовательные сообщения владельца с отчётом Android-приложения `UNO-N0-05 / REAL SENSOR / DIAGNOSTIC RESEARCH v0.5.0`, включая категоризованную CSV-трассу 400 окон (стадии 1–4 присланы ранее, стадия 5 с полным повтором стадий 1–4 прислана теперь). Этот GitHub-документ сохраняет точные агрегаты и ключевые наблюдения, **но не является полной дословной выгрузкой 400 CSV-строк**. Трасса в беседе; независимый Android logcat, сырые XYZ-отсчёты и хеш установленного на устройстве APK отсутствуют.

Устройство в отчёте: samsung SM-A525F, Android API 34, реальный `TYPE_LINEAR_ACCELERATION` (type 10). Исследовательский APK, без обучаемых числовых синаптических коэффициентов; числовая арифметика датчика и счётчики присутствуют.

## Пять стадий

| Стадия | learn | valid | transitions | model | persistence | Markov | always STILL | new/total nodes | connections | CONTESTED nodes | origin NEURON / NO_MATCH / CONTESTED |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TRAIN A | true | 80 | 17 | 60/80 | 64/80 | 64/80 | 63/80 | 6 / 6 | 26 | 3 | 14 / 11 / 55 |
| TEST A | false | 80 | 16 | 64/80 | 64/80 | 64/80 | 68/80 | 0 / 6 | 26 | 3 | 8 / 0 / 72 |
| TRAIN B | true | 80 | **5** | 74/80 | 76/80 | 76/80 | 74/80 | 5 / 11 | 47 | 4 | 28 / 20 / 32 |
| TEST B | false | 80 | **5** | 74/80 | 75/80 | 75/80 | 76/80 | 0 / 11 | 47 | 4 | 5 / 1 / 74 |
| RETEST A after restart | false | 80 | 26 | 55/80 | 54/80 | 54/80 | 24/80 | 0 / 11 | 47 | 4 | 12 / 20 / 48 |

Each stage reports `skippedWindows=0` and `AUDIT invariants=PASS`. All reported `TIE_OUTPUT` and `CONTESTED_AND_TIE` origin counts are zero.

| Стадия | neuron correct/wrong | fallback correct/wrong | neuron same/different from persistence | wins/losses vs persistence | wins/losses vs Markov | changed-neuron-decisions |
|---|---|---|---|---|---|---|
| TRAIN A | 7/7 | 53/13 | 10/4 | 0/4 | 0/4 | 4/80 |
| TEST A | 7/1 | 57/15 | 8/0 | 0/0 | 0/0 | 0/80 |
| TRAIN B | 24/4 | 50/2 | 24/4 | 1/3 | 1/3 | 4/80 |
| TEST B | 2/3 | 72/3 | 3/2 | 0/1 | 0/1 | 2/80 |
| RETEST A | 6/6 | 49/19 | 7/5 | 2/1 | 2/1 | 5/80 |

### Пятый этап — точные метрики приложения

```text
Проверка сохранённого состояния: PASS_SHA256 / completed=4 / nodes=11 / 0b6d15b7802a9bbc
START A — ПОВТОР ПОСЛЕ ПЕРЕЗАПУСКА / MODE=A / learn=false
END A — ПОВТОР ПОСЛЕ ПЕРЕЗАПУСКА; valid=80; time=20849 ms; sensorEvents=1087; skippedWindows=0
Физических смен класса движения: 26; модель 55/80; постоянство 54/80; числовая Markov-таблица 54/80; всегда STILL 24/80
Новые нейроны: 0; всего 11; connections 47; CONTESTED=4
AUDIT origins: NEURON=12, NO_MATCH=20, CONTESTED=48, TIE_OUTPUT=0, CONTESTED_AND_TIE=0
AUDIT neuron correct/wrong=6/6; fallback correct/wrong=49/19; neuron same/different from persistence=7/5
AUDIT wins/losses vs persistence=2/1; wins/losses vs Markov=2/1; firedSum=115; maxFired=2; multiTopWindows=0
AUDIT invariants=PASS; changed-neuron-decisions=5/80
N0-05 frozen utility candidate=FAIL; threshold neuron-different-from-persistence>=8 AND model>=max(persistence,Markov)+3
Вычисление прогноза: mean 145 µs, p95 194 µs, max 313 µs (НЕ энергия/пиковая RAM)
Java heap snapshot 4862 KiB; NOT PSS
CHECKPOINT: COMMIT_AND_READBACK_PASS / a53c30a924879de0 / rules=11
DEVICE PROTOCOL COMPLETE.
RESTORE: PASS_SHA256 / completed=4 / nodes=11 / 0b6d15b7802a9bbc; NEURONS: 11; SYNAPSES: 47
```

## Independently recomputed from owner-provided stage aggregates

- All five stages: UNO **327/400**, persistence **333/400**, numeric Markov **333/400**, always STILL **305/400**. The graph is six correct predictions behind both baselines across all 400 observations.
- Three frozen tests combined: UNO **193/240 (80.4167%)**, persistence **193/240**, Markov **193/240**. Individual differences: TEST A = 0, TEST B = -1, RETEST A = +1. This equal aggregate does not imply per-row predictions were the same.
- Frozen origins: NEURON = **25/240 (10.4167%)**, CONTESTED = **194/240 (80.8333%)**, NO_MATCH = **21/240 (8.75%)**. Thus fallback due to CONTESTED or NO_MATCH = **215/240 (89.5833%)**.
- Changed neural decisions versus persistence across frozen tests: **7/240**, with **2 wins and 2 losses**, net 0 improvement.
- Final RETEST A changes physical movement distribution: class transitions 26 vs TEST A 16; always-STILL correct 24 vs 68. A-retention accuracy 55/80 vs earlier TEST A 64/80 cannot isolate forgetting from this change.
- The qualitative trace shows a high-frequency contested mechanism in COINCIDENCE_6 and COINCIDENCE_10. Under current graph rules, a contradictory result contests the rule and its common context then falls back to persistence; the app's source-count audit now directly supports prevalence of fallback. The unobserved physical cause for contradictory labels (stochasticity vs missing contextual feature) remains unresolved.

## Frozen pre-registered criteria and result

The original frozen card `research/uno-n0-05/RESEARCH_CARD_FROZEN_BEFORE_DEVICE_RUN.md` requires all five stages to have >=8 class transitions and full TRACE+SHA-reload; B TRAIN and B TEST have only 5. Consequently full **DIAGNOSTIC OPERATIONAL GATE = FAIL/INVALID_LOW_MOTION_DIVERSITY** despite completion of 400 predictions, invariants PASS and restored 11-node state PASS_SHA256. Diagnostic pipeline and checkpoint mechanism work as reported; the *full five-stage acceptance gate* does not pass.

Exploratory learned-neuron utility candidate requires >=8 altered predictions AND >=3 additional correct answers versus both persistence and Markov on at least 2 of 3 frozen tests. TEST A: overrides0, delta0; TEST B: overrides2, delta-1, invalid diversity; RETEST A: overrides5, delta+1. **UTILITY GATE = FAIL (0 of 3 qualify)**. A positive +1 on the last test is a real counted result, but below frozen threshold and offset by -1 on TEST B.

**Statuses:** ANDROID_BUILT (prior CI), DEVICE_RUN_OWNER_REPORTED_COMPLETE, CHECKPOINT_RESTORE_OWNER_REPORTED_PASS, SOURCE_COUNTER_AUDIT_OWNER_REPORTED_PASS; FROZEN_OPERATIONAL_GATE_FAIL_INVALID_DIVERSITY; FROZEN_NEURON_UTILITY_GATE_FAIL; SCIENTIFIC_SUPERIORITY_NOT_SHOWN; DEVICE_INDEPENDENT_LOGCAT_UNAVAILABLE. No power/PSS/heat, independent OS action readback, artificial general intelligence, or production UNO established.

This is an *archival recording* of outcomes, not an update to the frozen card, algorithm or phone APK. No change to `main`, original R5.3, G4/G5 or production training authorization.
