# UNO-N0-04 — Samsung A52 TRAIN B (owner-supplied, 2026-11-05)

Source: application text pasted by owner; not independent device logcat. This stage continues previously archived TRAIN A and TEST A. Keep all raw historical records.

## Android report, TRAIN B

```text
Устройство: samsung SM-A525F / Android API 34
Физический сенсор: linear_acceleration (type 10)
Источник: TYPE_LINEAR_ACCELERATION
Проверка сохранённого состояния: PASS_SHA256 / completed=2 / nodes=10 / 8b26ccaf2ad90ce5
Утверждение: NO learned numerical synaptic weights; числовые пороги датчика и счётчики остаются.
Ограничения: реальные показания датчика ≠ проверенные последствия внешних действий; никакой энергии/AGI здесь не измеряется.

=== START B — ОБУЧЕНИЕ / MODE=B / learn=true ===
END B — ОБУЧЕНИЕ; valid=80; time=20709 ms; sensorEvents=1081; skippedWindows=0
Физических смен класса движения: 12; модель 63/80; постоянство 68/80; числовая Markov-таблица 66/80; всегда STILL 40/80
Новые нейроны: 9; всего 19; connections 83; CONTESTED=12
Вычисление прогноза: mean 98 µs, p95 187 µs, max 215 µs (НЕ энергия/пиковая RAM)
Java heap snapshot 3151 KiB; NOT PSS
GATE: metric gate tentative PASS; check persistence and complete A→B→A protocol
CHECKPOINT: COMMIT_AND_READBACK_PASS / 76f6d041270ab3b8 / rules=19

CHECKPOINT: COMMIT_AND_READBACK_PASS / 76f6d041270ab3b8 / rules=19; RESTORE: PASS_SHA256 / completed=2 / nodes=10 / 8b26ccaf2ad90ce5; NEURONS: 19; SYNAPSES: 83
```

## Frozen-protocol interpretation

- TRAIN B completed 80 predictions on real Android accelerometer, 12 class changes (>=8 required), no skipped windows; phase is valid. `learn=true`, so this is NOT the frozen TEST B used for the adaptation gate.
- Model 63/80 = 78.75%; previous-state persistence 68/80 = 85%; numeric Markov 66/80 = 82.5%; always STILL 40/80 = 50%. Model was five correct predictions below persistence and three below Markov on this training stage, despite nine new structural rules.
- Network structure now 19 conjunction neurons, 83 connections, 12 contested rules. The report does not prove new rules improved prediction, and lack of stability/causality remains.
- Graph inference time mean/p95/max 98/187/215 microseconds; Java heap *snapshot* 3151 KiB. Neither is measured battery energy, PSS, peak memory, heat, or whole-app footprint.
- `RESTORE PASS_SHA256 / completed=2 / nodes=10` attests restore of prior TEST A checkpoint. Current B 19-node checkpoint has only `COMMIT_AND_READBACK_PASS` at this moment. RESTORE of the 19-node graph, retention after learning B, and post-restart TEST A remain UNTESTED.
- App's `tentative PASS` line does not override pre-registered multi-stage frozen criteria (TEST A, TEST B, RETEST A each graph >= max(persistence, Markov); motion diversity >=8; checkpoint restore PASS_SHA256).
- Next in fixed sequence: **TEST B** (MODE=B, learn=false), then close/reopen and **RETEST A**. Do not reset or retrain differently before completing protocol.
- Status DEVICE_RUN_OWNER_REPORTED for Stage TRAIN B, PROTOCOL_INCOMPLETE for full A→B→A. Not independent device instrumentation, not new AI invention, not validation of production UNO. G4/G5 unchanged.
