# UNO-N0-04 — A52 TEST B, owner-reported 2026-11-05

Source: verbatim metrics and qualitative movement information pasted by owner in the ChatGPT conversation. Not independently acquired logcat or independently hashed installed APK.

Device: samsung SM-A525F, API34, sensor TYPE_LINEAR_ACCELERATION (type 10), native sensor not a simulated oracle.

## TRAIN B (previously saved, for comparison)
```text
MODE=B / learn=true
valid=80; time=20709 ms; sensorEvents=1081; skippedWindows=0
class changes=12; model=63/80; persistence=68/80; Markov=66/80; ALWAYS_STILL=40/80
new neurons=9; total=19; connections=83; CONTESTED=12
inference mean 98 µs, p95 187 µs, max 215 µs; Java heap snapshot 3151 KiB
CHECKPOINT COMMIT_AND_READBACK_PASS / 76f6d041270ab3b8 / rules=19
```

## TEST B (new owner evidence)
```text
UNO-N0-04 / REAL SENSOR / RESEARCH v0.4.0
Устройство: samsung SM-A525F / Android API 34
Физический сенсор: linear_acceleration (type 10)
Источник: TYPE_LINEAR_ACCELERATION
Проверка сохранённого состояния: PASS_SHA256 / completed=3 / nodes=19 / 76f6d041270ab3b8

=== START B — КОНТРОЛЬ / MODE=B / learn=false ===
END B — КОНТРОЛЬ; valid=80; time=20813 ms; sensorEvents=1086; skippedWindows=0
Физических смен класса движения: 23; модель 57/80; постоянство 57/80; числовая Markov-таблица 57/80; всегда STILL 6/80
Новые нейроны: 0; всего 19; connections 83; CONTESTED=12
Вычисление прогноза: mean 147 µs, p95 205 µs, max 235 µs (НЕ энергия/пиковая RAM)
Java heap snapshot 3187 KiB; NOT PSS
GATE: metric gate tentative PASS; check persistence and complete A→B→A protocol
CHECKPOINT: COMMIT_AND_READBACK_PASS / 45e6bb9f143c64d3 / rules=19
ОБЯЗАТЕЛЬНО закрой и повторно открой приложение для повторного TEST A.

CHECKPOINT: COMMIT_AND_READBACK_PASS / 45e6bb9f143c64d3 / rules=19; RESTORE: PASS_SHA256 / completed=3 / nodes=19 / 76f6d041270ab3b8; NEURONS: 19; SYNAPSES: 83
```

Owner's accompanying note: «Правда сейчас я двигал телефоном резво крутил его но не резко».

## Assessment against frozen card

- Test B valid: 80 windows, 23 physical class changes (>=8 threshold), zero skipped windows, frozen graph/no new neurons.
- Graph 57/80 = 71.25%, persistence 57/80, numeric Markov 57/80, always STILL 6/80. **TIE**, not superiority to the two baselines. Frozen metric criterion graph >= max(two baselines) is MET for TEST B alone.
- Sensor event count=1086, runtime=20813ms. Inference mean/p95/max=147/205/235us; Java heap snapshot=3187KiB, not PSS/energy.
- Saved B state restored at start (19 nodes, short hash 76f6d041270ab3b8), then new checkpoint committed and immediate readback hash 45e6bb9f143c64d3 for completed=4. A *new* process restart after TEST B is STILL required before RETEST A.
- TEST B movement distribution differs substantially from TRAIN B. Changes 12 -> 23; ALWAYS_STILL correct count 40/80 -> 6/80 (sensor label frequency shifted). Owner describes brisk rotation; do not attribute TEST B accuracy changes exclusively to learning or forgetting. TYPE_LINEAR_ACCELERATION reflects measured linear acceleration, not pure angular velocity; movement and sensor separation may affect categories.
- No evidence yet of adaptive performance superiority, retention of A after B, energy efficiency, causal verified Android action, or general intelligence. No sealed independent dataset.
- Four of five stages completed: TRAIN A, TEST A, TRAIN B, TEST B. Frozen protocol final step: close and reopen app (expect RESTORE PASS_SHA256 / completed=4 / nodes=19 / short hash 45e6bb9f143c64d3), then RETEST A in A-like movement. **No reset, no reinstallation or retraining**. Compare to TEST A 64/80 and all baselines. G4/G5 not approved.
