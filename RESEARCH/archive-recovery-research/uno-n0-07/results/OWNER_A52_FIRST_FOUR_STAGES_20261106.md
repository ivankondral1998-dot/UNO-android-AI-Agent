# UNO N0-07 — first four physical stages on Samsung A52 (owner report 2026-11-06)

**STATUS:** DEVICE_OWNER_REPORTED_PARTIAL / four of five stages; original research APK `org.unovyra.n007`, 0.7.0-research. This report records literal figures pasted by owner, **not an independent on-device reproduction and NOT a verbatim archive of all 320 row-level CSV observations**. Original full row-level text was supplied in the live chat on 2026-11-06. Full 400-window series and stage 5 readback still pending; never say full protocol finished. No retuning or changed code/tests.

## Owner-reported physical stage data

| Stage | Training | valid | changes | dropped | sensor events | time ms | tiny F | persistence | Markov | always STILL | F overrides | sensory learned cumul. | owner hints cumul. | inference mean/p95/max µs | JavaHeapSnapshot KiB | storage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | --- |
| 1 A train | YES | 80 | 21 | 0 | 1089 | 20868 | 42/80 | 59/80 | 58/80 | 22/80 | 36/80 | 80 | 6 | 438/726/5580 | 4429 | COMMIT_AND_READBACK_PASS completed=1 |
| 2 A control | NO | 80 | 15 | 0 | 1085 | 20787 | 14/80 | 65/80 | 65/80 | 66/80 | 65/80 | 80 | 6 | 262/328/415 | 7805 | COMMIT_AND_READBACK_PASS completed=2 |
| 3 B train | YES | 80 | 22 | 0 | 1088 | 20849 | 42/80 | 58/80 | 55/80 | 7/80 | 35/80 | 160 | 10 | 232/317/534 | 5742 | COMMIT_AND_READBACK_PASS completed=3 |
| 4 B control | NO | 80 | 28 | 0 | 1085 | 20793 | 24/80 | 52/80 | 35/80 | 43/80 | 56/80 | 160 | 10 | 277/317/442 | 4690 | COMMIT_AND_READBACK_PASS completed=4 |

Summed: **UNO 122/320** (38.125%), persistence **234/320** (73.125%), Markov **213/320** (66.5625%), always STILL **138/320** (43.125%); total changes **86**, all 4 stages >=8 diverse changes, dropped 0. All-source aggregate is a descriptive diagnostic mixing training and control, not a pure frozen evaluation.

Frozen controls only stages 2+4: **UNO 38/160** (23.75%), persistence **117/160** (73.125%), Markov **100/160** (62.5%), always STILL **109/160** (68.125%). The network scores much worse than both baselines; this is a clear **predictive utility FAIL** on the two supplied real, unseen-to-training stages.

## Exact pattern in the pasted row-level trace

- Stage 2 (A control): **80/80 model predictions equal MOVE**, including contexts STILL/STILL over repeated observed STILL events and no online sensor training during this stage. Since 66/80 actual observations were STILL (and observed model correctly predicted 14), this alone explains catastrophic low accuracy on A control. The reported `overrides=65/80` is consistent with this result: 65 previous states were non-MOVE. `always STILL=66/80` independently confirms the class distribution.
- Stage 4 (B control): **80/80 model predictions equal MOVE** in the pasted row-level text; 24/80 network correct, while persistence 52 and Markov 35. This is prediction-class collapse observed twice; **cause not yet established** (could include learned head biases, representation/feature limitations, recurrent state drift or mode distribution shift). It does NOT imply the neural engine crashed, since control inference continued, masks ran with `computedBlocks=4, skippedBlocks=4` each step, and source did log outputs.
- Stage 1 and stage 3 training still show varying outputs. Owner pushed **6 explicit hints in A train, 4 in B train** (total 10). App design `teachOwnerIntent()` trains a separate intention head; the 3-class sensor prediction evaluation does not measure this head's owner-meaning accuracy. **Do not claim hints helped or hurt physical sensor accuracy.**
- The `SENSOR_WEIGHT_COUNT` only counts accepted training events (80 then 160), **not an independent per-device weight-difference proof**. Original Java code implements weight updates; host checks establish weight change in isolated tests, but this owner report does not include weight fingerprints.
- `COMMIT_AND_READBACK_PASS` is local same-process serialized-save/readback at each stage, **not** the stage-5 across-relaunch restore evidence. Current app state `stage=4 / restore=OWNER_RESET` reflects earlier owner reset. Stage 5 must be run after closing/reopening the app. Java heap snapshots and 200–400µs averages are not PSS, energy or phone thermal measurements.

## Source / reproducibility / next action

Provenance: owner pasted four stage summaries, owner teaching log, app current state and full 320-line categorical trace in the UNO ChatGPT project on 2026-11-06. Trace header `stage,index,mode,older,prev,model,markov,persistence,actual,executedBlocks,skippedBlocks`; intended 80 per stage. **All rows were reviewed in conversation but not captured as a hash-verifiable raw file in this repository.** This is a summary/diagnostic artifact only.

Source: `research/uno-n0-07/core/TinyOrganism.java`, `research/uno-n0-07/android/MainActivity.java`, original frozen card `research/uno-n0-07/FROZEN_RESEARCH_CARD_20261105.md`, and signed APK evidence `research/uno-n0-07/results/ANDROID_BUILD_EVIDENCE_20261105.md`.

Next: **do not reset, modify APK, change weights, tune thresholds or reinterpret previously observed fixed results**. Owner should fully close and reopen original app, check `Readback of saved checkpoint` and stage 5 availability, run `A — ПОВТОР ПОСЛЕ ПЕРЕЗАПУСКА` for 80 valid windows, and send the complete final report and 400-row categorized trace. Treat `RESTORE PASS/FAIL` as independently separate from earlier per-stage checkpoint readback.

Research interpretation: the whole full-organism learning requirement (owner intention and independently verified Android outcomes) is NOT refuted; no Android action-effect readback exists in N0-07. No change to R5.3, no production approval, no GitHub Actions required for recording observations.
