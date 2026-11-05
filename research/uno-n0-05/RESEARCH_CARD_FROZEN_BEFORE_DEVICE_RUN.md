# UNO-N0-05 / Real sensor origin and fallback audit — frozen card — 2026-11-05

State: PRE-DEVICE SPECIFICATION, ISOLATED RESEARCH. Device Samsung SM-A525F / API34. Owner authorized Android research and GitHub Actions on 2026-11-05. No authorization for UNO production G4/G5, training production weights, changes to main, force push, deletion, release publication, cloud/internet on phone.

## Research question

N0-04 concluded 5-stage A→B→A owner run: 19 qualitative neurons, 83 links, 12 contested rules; on all three frozen tests model tied both persistence and a numeric first-order Markov lookup (64/80, 57/80, 63/80), 184/240 each. The frozen N0-04 trace does NOT say how many predictions came from neurons rather than fallback, or whether neuron overrides helped and harmed equally. We must not assert the fallback explanation as proven.

N0-05 is **instrumentation of the same learning/inference algorithm** with no changes to neuron creation, contest marking, max specificity selection or fallback rule. New app package is separate from N0-04 to preserve original checkpoints; therefore old N0-04 results cannot simply be reclassified, and a fresh five-stage physical data experiment is required. Structural rules remain designer-authored, not proof of invention/AGI. Sensor class thresholds and categorical/numeric counters still exist; there are no learned scalar synaptic coefficients.

## Data path and graph origin contract

Physical TYPE_LINEAR_ACCELERATION (fallback accelerometer with gravity subtraction), 250ms windows. Categories STILL (<0.65m/s²), MOVE (<2.5), JOLT (>=2.5). NeuralGraph.predict() uses only MODE A/B (human-provided), previous/older labels, derived trend; later observed categorical label becomes target only after the prediction is scored. Event streams are physical measurements, NOT trusted readback of actual Android operations. Inference does not access future labels.

Each prediction is assigned exactly one of five mutually exclusive outcomes:
- NEURON: one or more maximal-specificity neurons agree and NONE are contested.
- NO_MATCH: no neuron fires (fallback predicts previous label).
- CONTESTED: winning-specificity node is contested without disagreement among top emissions (fallback).
- TIE_OUTPUT: top neurons disagree on emission, none contested (fallback).
- CONTESTED_AND_TIE: both contested top rule and conflicting top outputs (fallback).

Diagnostic counters: source class, firing neuron count, top-specificity count, top neuron ID, learned-neuron same/different from persistence, right/wrong for learned/fallback, counterfactual gains/losses compared with persistence and Markov on exactly the **same next sensor window**. Each stage MUST verify source counts sum to 80, category correct/wrong sum to 80, and (model-persistence correct)=(wins-losses vs persistence), likewise for Markov. Failure is audit FAIL regardless of accuracy. A compact per-window trace (categorical, no raw xyz) is preserved and included in checkpoint SHA-256 envelope; owner can copy it independently. No network or background data collection.

## Frozen experiment, no task/threshold retuning

Same 5 phases as N0-04, each 80 valid prospective predictions, <=60s, >=8 class transitions, zero or explained skipped windows. A: mostly still with occasional smooth hand movements; B: more regular, frequent but gentle movements. Avoid violent shaking. No training in frozen stages. After TEST B, close and reopen app to force a new Activity and checksum-verified checkpoint restore, then RETEST A. Do not reset mid-study. Record package version, phone model/API, sensor, per-stage raw counts, full categorical trace, checksum and all fallback categories.

1. TRAIN A — 80 windows, graph/Markov learn.
2. FROZEN TEST A — 80 windows, no learning.
3. TRAIN B — 80 windows, graph/Markov learn.
4. FROZEN TEST B — 80 windows, no learning.
5. After actual app close/reopen and PASS_SHA256 — FROZEN RETEST A — 80 windows, no learning.

## Independent acceptance and scientific failure conditions

Diagnostic-**operational PASS** only if: all five stages valid and >=8 class changes, model produces structured rules in training, ALL audit invariants pass, a full 400-row categorical trace (80 each) is available and reloads from checked checkpoint after restart, and prior graph node count restores after new Activity. No phone evidence means DEVICE_UNTESTED. CI compile and host equivalence tests do NOT satisfy phone gates.

Strong exploratory **neuron-utility candidate PASS** only if on at least 2 of 3 frozen tests (a) learned-neuron decision differs from persistence on at least 8/80 windows, (b) graph correct >= max(persistence,Markov)+3 of 80. These margins are pre-declared and do not constitute statistical significance or broad-world superiority. If no meaningful neuron decisions and all accuracy ties, mark LEARNED_UTILITY_FAIL, not innovation. If neural overrides help and hurt equally, record both. If CONTESTED dominates origin, report its exact prevalence, not merely node count. If initial A/B motion distribution changes, flag distribution confounding; no sealed holdout or device power claims.

Original N0-04 is unchanged. GitHub action only builds/verifies APK on private research branch; no deployment. Inference equivalence vs untouched original N0-04 should be host-tested with fixed seed; JSON stubs in host tests are NOT persistence validation. Size/memory cap 2GiB, 600s per candidate run and max 3 candidate repetitions; Android stage itself max 60s. No work on main, no production claims.
