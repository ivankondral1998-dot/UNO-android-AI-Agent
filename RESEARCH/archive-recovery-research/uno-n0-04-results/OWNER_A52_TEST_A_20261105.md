# UNO-N0-04 — A52 TEST A after TRAIN A (owner-reported), 2026-11-05

Source: owner-pasted Android app report, not independent Android logcat or separately hashed installed APK.

Device: samsung SM-A525F / Android API 34; real sensor linear_acceleration, TYPE_LINEAR_ACCELERATION (type 10).

## Earlier TRAIN A (for paired interpretation)
- valid 80; 20,834 ms; sensorEvents=1087; skippedWindows=0; class changes=26.
- Graph 52/80; persistence 54/80; numerical Markov 50/80; always STILL 44/80.
- 10 new conjunction neurons; total 10; 44 connections; contested=7.
- Graph inference mean 137 µs; p95 194 µs; max 284 µs; Java heap snapshot 6164 KiB.
- Saved checkpoint: COMMIT_AND_READBACK_PASS / 8da36b1e2645d4be / rules=10.

## TEST A (no online learning; actual user-provided results)
- Header at app opening: RESTORE PASS_SHA256 / completed=1 / nodes=10 / 8da36b1e2645d4be.
- START A — КОНТРОЛЬ / MODE=A / learn=false.
- END: valid=80; time=20833 ms; sensorEvents=1086; skippedWindows=0.
- Class changes=16 (>=8 criterion satisfied).
- Model 64/80; persistence 64/80; numeric Markov 64/80; always STILL 56/80.
- New neurons 0; total 10; connections 44; CONTESTED=7.
- Prediction timing mean 143 µs, p95 194 µs, max 383 µs.
- Java heap snapshot 2860 KiB; NOT PSS.
- App says 'GATE: metric gate tentative PASS; check persistence and complete A→B→A protocol'.
- CHECKPOINT: COMMIT_AND_READBACK_PASS / 8b26ccaf2ad90ce5 / rules=10; RETAINED RESTORE PASS_SHA256 / completed=1 / nodes=10 / 8da36b1e2645d4be; NEURONS 10, SYNAPSES 44.

## Evaluation boundaries
- TEST A matches frozen criterion graph >= max(persistence, Markov), but equals both at 64/80 (80%) and does not outperform them.
- TEST A was run with fixed graph (0 new neurons), so the outcome is held-out in time after online TRAIN A; it is NOT a sealed unknown user/task distribution.
- Variation in movement diversity TRAIN A 26 transitions vs TEST A 16 confounds the 52/80 vs 64/80 difference; do not attribute the change to neural learning.
- RESTORE PASS_SHA256 supports saved graph reload, but does not itself prove recovery after force-stopping/crash and future A retention after B. The frozen protocol additionally requires TEST B and RETEST A after app restart.
- This is owner-reported Android result, not independently obtained logcat, battery/PSS/energy measurement or independent OS action readback. Not AGI, novelty, or production UNO proof.
- Current protocol status: TRAIN A complete; TEST A complete/pass comparison and diversity; TRAIN B pending; TEST B pending; RETEST A pending. Overall PASS not asserted.
- Gate status G4 PRECODE_CANDIDATE / OWNER_APPROVED_PRECODE=FALSE / PRODUCTION_CODE_AUTHORIZED=FALSE unchanged. Research source and historical documents untouched.
