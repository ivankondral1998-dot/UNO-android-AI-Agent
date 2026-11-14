# UNO N0-07 — Samsung A52 owner-reported full 5-stage 400-window study (2026-11-06)

**Evidence grade:** DEVICE_OWNER_REPORTED / APP_TRACE_ANALYZED / FIVE_STAGES_COMPLETED / FROZEN_UTILITY_FAIL. This is not independent device instrumentation or an R5.3 result. No new code or training runs performed by the agent.

## Provenance and precise limits

Owner pasted the original app's 400-line categorical CSV into the project ChatGPT conversation on 2026-11-06 (five 80-window stages). Stage 1–4 app summary and original pasted 320 rows were reported in the preceding user message; see `research/uno-n0-07/results/OWNER_A52_FIRST_FOUR_STAGES_20261106.md`. Stage-5 rows were carefully transcribed into a **semantically equivalent, regenerated 80-row CSV** at `research/uno-n0-07/results/OWNER_A52_STAGE5_CATEGORICAL_TRACE_RECONSTRUCTED_20261106.csv`: not a byte-level copy of phone export, no phone-file hash. Stage-5 app's final summary and exact `restoreStatus` strings were **not** supplied: stage-5 aggregate below is derived from row data, not a claim that an app log printed the numbers.

Original signed research APK: `org.unovyra.n007` v0.7.0-research, built at `5fc805d33f6e28d77c5ecaab88098ecc567d9a03` through private run 42104813304. Source relevant for inference and stage-5 eligibility: `research/uno-n0-07/android/MainActivity.java`, `core/TinyOrganism.java`. Both original files remain immutable.

## Five stages, with frozen gates clearly separated

| Stage | Type | Predictions evaluated | Tiny F correct | Persistence correct | Markov correct | Always STILL correct | Label changes | Diversity acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 A | training, weights update | 80 | 42 | 59 | 58 | 22 | 21 | PASS |
| 2 A | control, weights frozen | 80 | 14 | 65 | 65 | 66 | 15 | PASS |
| 3 B | training, weights update | 80 | 42 | 58 | 55 | 7 | 22 | PASS |
| 4 B | control, weights frozen | 80 | 24 | 52 | 35 | 43 | 28 | PASS |
| 5 A | control, weights frozen, after app relaunch | 80 | **77** | **77** | **77** | **3** | **3** | **FAIL: INVALID_LOW_MOTION_DIVERSITY** |
| **All 400, descriptive** | mixed train+control | **400** | **199 (49.75%)** | **311 (77.75%)** | **290 (72.5%)** | **141 (35.25%)** | **89** | Mixed / NOT one valid single gate |

**Strict frozen evaluation with valid movement-diversity gates only (stage 2+4):** Tiny F **38/160 (23.75%)**, persistence **117/160 (73.125%)**, numeric Markov **100/160 (62.5%)**. **FAIL** relative to both baselines. Training-stage accuracy is not held-out evidence.

**All three frozen stages, descriptive only (stage 2+4+5):** Tiny F **115/240 (47.9167%)**, persistence **194/240 (80.8333%)**, Markov **177/240 (73.75%)**, always STILL **112/240 (46.6667%)**. Do not use as a passing three-stage evaluation because stage 5 violates the pre-registered diversity threshold.

## Stage 5 derivation (from owner-pasted CSV)

Original stage-5 CSV contains 80 consecutive rows, stage=5, mode=A, index=1..80 without gaps; `model=MOVE` in all 80. Actual label run lengths: `MOVE` rows 1–68 (68), `STILL` 69–70 (2), `MOVE` 71–79 (9), `STILL` row 80 (1). Therefore **77 MOVE, 3 STILL, 0 JOLT**, class changes at indices **69, 71, 80** (three changes). This yields F=77/80, Markov=77/80, persistence=77/80, ALWAYS_STILL=3/80; no superiority, even on this very skewed stage. All rows show `executedBlocks=4, skippedBlocks=4` (two passes × two actual chosen blocks) in accordance with source, without claiming phone power consumption.

The source requires stage=4 (the fifth stage) be available only after `loadedFromDiskThisActivity=true` and `!corrupt`. That flag is assigned by `loadCheckpoint()` only after SHA256 and `TinyOrganism.restore()` succeed in a new Activity. **Conditional on running the unchanged APK, stage 5 being run implies a successful app checkpoint restore path.** However, independent device readback of weight hashes was not supplied; the final `restoreStatus` report is needed for complete evidence. Moreover, this is checkpoint restoration, not retained predictive usefulness.

## Error mechanism: observed vs unproven

- In **all 240 control rows**, model predicts `MOVE`, irrespective of the prior two discrete labels. Control-stage true labels: **115 MOVE, 112 STILL, 13 JOLT**. Thus F correctness on this mixed set is exactly the true MOVE count, not evidence of three-class discrimination. It misses **112/112 STILL** and **13/13 JOLT** in control; conditional true-class recalls: MOVE **115/115**, STILL **0/112**, JOLT **0/13**.
- This is an **observed collapse to a single predicted class**, not an inferred software exception. The root cause of the collapse is **UNKNOWN** without inspecting intermediate hidden activations, sensory logits/softmax, head weights and state evolution. Possible hypotheses include learned bias, recurrent state dynamics and distribution shift. No hypothesis has been proven.
- Stage-5 high numerical accuracy (96.25%) resulted from the 77/80 `MOVE` class prevalence, and ties both trivial baselines. Does **not** repair the severe stage-2/stage-4 failures. The original A-training and A-control had different actual class distributions, and stage 5 is even more different; no matched A replay with a frozen identical time series was performed.
- The owner's 10 feedback taps in training stages update a separate intention head (`teachOwnerIntent`) and tagged ledger. Sensor predictions can be affected indirectly by semantic memory on future events, **but neither the direction nor size of any effect is known from these logs**. No separate owner-intent accuracy was measured.
- The 160 cumulative `SENSOR_WEIGHT_COUNT` is a training-event counter, not a per-device cryptographic weight delta. Host test separately showed learning updates, but not predictive success on A52. This APK does **not** implement real independent Android action readback or learn from actual OS action outcomes. STOP/permissions unaffected.

## Next scientific step, not authorization to alter original

Preserve the entire original APK, branch, logs, source and artifacts. Do not retroactively optimize on these 400 observations and then reuse them as an untouched holdout. For a **new, separately frozen research candidate**: controlled balanced STILL/MOVE/JOLT on the phone in matched train/control windows; log per-class confusion matrix, score distributions, logits, state norms and before/after checkpoint/weight fingerprints; separately evaluate owner teaching vs no teaching; retain persistence, Markov and fixed network baselines. Actual API/Android independent postcondition path must remain separate and is still UNTESTED.

**Project gate remains:** G4 PRECODE_CANDIDATE; OWNER_APPROVED_PRECODE=FALSE, PRODUCTION_CODE_AUTHORIZED=FALSE. `main` unchanged; no GitHub Actions required for this analysis.
