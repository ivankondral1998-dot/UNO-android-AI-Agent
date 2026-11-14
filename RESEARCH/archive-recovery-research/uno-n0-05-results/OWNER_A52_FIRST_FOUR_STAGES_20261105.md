# UNO-N0-05 — Samsung A52, первые четыре стадии (отчёт владельца, 2026-11-05)

**Источник:** полный текст сводки приложения и категориальной CSV-трассы стадий 1–4 вставлен владельцем в текущую беседу. Эта версия GitHub-отчёта сохраняет точные агрегаты и доказательные фрагменты CSV, **но не выдаёт себя за полную дословную копию 320 CSV-строк**. Пятая стадия пока не предоставлена. Нет независимого logcat, исходных XYZ-измерений и проверенного хеша установленного APK.

Устройство: samsung SM-A525F, API 34; физический TYPE_LINEAR_ACCELERATION, type 10; версия 0.5.0-research. Контрольные данные N0-04 не переносились в N0-05.

## Агрегаты приложения

| Стадия | Обучение | valid | Классовых переходов | UNO | Persistence | Markov | Always STILL | NEURON | NO_MATCH | CONTESTED | New/total neurons | Links | CONTESTED rules |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A train | true | 80 | 17 | 60 | 64 | 64 | 63 | 14 | 11 | 55 | 6 / 6 | 26 | 3 |
| A test | false | 80 | 16 | 64 | 64 | 64 | 68 | 8 | 0 | 72 | 0 / 6 | 26 | 3 |
| B train | true | 80 | **5** | 74 | 76 | 76 | 74 | 28 | 20 | 32 | 5 / 11 | 47 | 4 |
| B test | false | 80 | **5** | 74 | 75 | 75 | 76 | 5 | 1 | 74 | 0 / 11 | 47 | 4 |

Каждая стадия: 80/80 valid, 0 skippedWindows. Источники TIE_OUTPUT=0 и CONTESTED_AND_TIE=0 на всех четырёх стадиях. AUDIT invariants=PASS на всех четырёх стадиях.

| Стадия | neuron correct/wrong | fallback correct/wrong | neuron same/different vs persistence | wins/losses vs persistence | wins/losses vs Markov | changed neural decisions |
|---|---:|---:|---:|---:|---:|---:|
| A train | 7/7 | 53/13 | 10/4 | 0/4 | 0/4 | 4/80 |
| A test | 7/1 | 57/15 | 8/0 | 0/0 | 0/0 | 0/80 |
| B train | 24/4 | 50/2 | 24/4 | 1/3 | 1/3 | 4/80 |
| B test | 2/3 | 72/3 | 3/2 | 0/1 | 0/1 | 2/80 |

Измерения: A train duration 20865ms, events1088, mean/p95/max 138/196/333µs, heap4234KiB. A test 20819ms,1086 events,127/174/214µs, heap3877KiB. B train 20811ms,1086 events,146/208/366µs, heap6565KiB. B test 20793ms,1085 events,142/203/271µs, heap4431KiB. Java heap snapshots ≠ PSS, peak RAM, battery energy.

Checkpoints: A train RESTORE at next start PASS_SHA256 completed=1 nodes=6 short hash 21a890b301aa7960. A test COMMIT_AND_READBACK_PASS short 72185126fad9d65c rules6. B train COMMIT_AND_READBACK_PASS short df2767360053a20f rules11. B test COMMIT_AND_READBACK_PASS short 0b6d15b7802a9bbc rules11. Last displayed RESTORE=PASS_SHA256 completed=1 nodes=6, i.e. it **does not prove** restart restoration of current 11-node post-B state.

## Evidence in supplied categorical trace

A train: `stage 1, index 18, A, STILL, STILL, FLAT, predicted STILL, origin NEURON, top COINCIDENCE_6, actual MOVE` followed by `stage 1, index 21, same A STILL/STILL/FLAT context, origin CONTESTED, predicted STILL`. Later most repeated context windows remain CONTESTED. A frozen test begins with sixteen consecutive STILL windows primarily labeled CONTESTED (COINCIDENCE_6).

B train: `stage 3, index 45, B, STILL, STILL, FLAT, predicted STILL, origin NEURON, top COINCIDENCE_10, actual MOVE`; index 49 begins repeated CONTESTED on COINCIDENCE_10, dominating subsequent windows. B frozen test: 74/80 CONTESTED, mostly COINCIDENCE_10; two neuron decisions differ from persistence and cause 0 gain, 1 loss. B test index 27: NEURON predicts STILL, persistence MOVE, actual JOLT (both incorrect); index 29: NEURON predicts MOVE, persistence STILL, actual STILL (neuron loss). These rows support the reported 0/1 wins/losses.

**Interpretation:** repeated contradictory outcomes for the same coarse condition can set a rule to CONTESTED, leading to persistent fallback. This sequence is **observed** in the CSV. Whether the contradiction represents stochastic dynamics or inadequate qualitative features is NOT established by categorical data alone. The same baseline-tie cause for historical N0-04 is a compatible hypothesis, not retroactive proof.

## Pre-registered gates

Card: `research/uno-n0-05/RESEARCH_CARD_FROZEN_BEFORE_DEVICE_RUN.md`. Requires >=8 transitions **per stage**, full five stages and restart checkpoint with 400-row trace. B train and B test each have 5, therefore both **INVALID_LOW_MOTION_DIVERSITY**. The operational full-device gate is NOT passed. Phone has not completed RETEST A stage (stage 5).

Exploratory neuron-utility criterion requires >=8 meaningful overrides AND >=3/80 improvement versus both persistence and Markov in at least 2 of 3 frozen tests. A test has 0 overrides and 0 improvement; B test has 2 overrides, -1 vs both, and is diversity-invalid. Thus no path to utility PASS within this already-started five-stage run, even if RETEST A passes. On two currently supplied frozen tests, 146 of 160 forecasts (91.25%) are CONTESTED fallback; learned-neuron forecasts 13 of 160 (8.125%), one NO_MATCH; only 2 of 160 predictions differ from persistence. Combined four-stage graph predictions 272/320 vs persistence 279/320 (7 fewer).

No source modification or protocol retuning. No N0-05 scientific superiority; exact cause of ambiguity and new learner improvements remain open research. R5.3 G4 precode candidate, G5 production code unauthorized; no changes to main.
