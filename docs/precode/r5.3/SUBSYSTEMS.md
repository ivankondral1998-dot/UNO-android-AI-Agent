# Подсистемы: где лежит ПОЛНОЕ определение

| Область | Полный математический источник | Критическое дополнение |
|---|---|---|
| Causal clock, state S, shared F, adaptive compute, goals | sources/astra/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md | W4 ERRATA |
| Tensor layouts, allocated/free/frozen, B2/LR2/H2 | sources/astra/ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md | no equivalence claim |
| L3a, gradients, losses, QAT, CTC, datasets | sources/astra/ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md | WAKE/SENSOR, coverage |
| Exact/semantic memory, P, checkpoint, recovery | sources/astra/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md | RetrieveExact semantics |
| Android trust, latency/MAC/peak/energy | sources/astra/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md | STOP/SAF/no blanket offline claim |
| NCR-EVO / statistical falsification | sources/astra/ASTRA_06_NCR_EVO_MATH_AND_FALSIFICATION.md | experimental only |
| Design obligations D01–D10 | sources/astra/ASTRA_07_PRECODE_ENGINEERING_D01_D10.md | OWNER_DECISIONS |
| Proof obligations, counterexamples | sources/astra/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md | W4 / known counterexamples |
| Legacy M01–M44 matrix | Source archive ASTRA_09 — NOT YET VERIFIED BYTE-MATCH in this branch | never mark all PASS |
| Historical independent redteam | Source archive ASTRA_10 — NOT YET VERIFIED BYTE-MATCH | separate from current gates |
| Future execution stages | sources/astra/ASTRA_11_CODEX_FUTURE_EXECUTION_BLUEPRINT.md | no code authorization |
| Unknowns and hardware requests | sources/astra/ASTRA_12_UNKNOWNS_DATA_AND_HARDWARE_REQUESTS.md | G5 tests |

Legacy JNO belongs in research/legacy-jno; it is NOT part of UNO trained runtime.
