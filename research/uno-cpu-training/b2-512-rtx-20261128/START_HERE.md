# UNO B2-512 — RTX training handoff, 2026-11-28

Research only. Current branch: research/uno-train-001-s4-20261115. Read [main/AGENTS.md](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/main/AGENTS.md) before changing anything. Base HEAD before preservation: 6aaeded909f6d137456d3005a433a3e9aace27d7. R5.4 Candidate remains CONDITIONAL; no production approval.

## Start here
- trainer/: original CUDA bridge + AUDIT01 + AUDIT02 + FAST03, exact source files co-located as installed on owner's PC. Read README_FAST03.txt first. FAST03 is the last released trainer, not a validated final trainer.
- corpus/: original FIX03 and active FIX04 preparation script. Source-only checkout; private input ZIPs and held-out prompts are NOT included. Do not restart the owner's active process. Expected completed corpus D:\UNO\corpus_prepared_v4, never .building.
- math/: original verdict, mathematical candidate, errata and gates extracted without edits; full audit archive remains in authorized Library.
- reference/: original B2-512 step50 source and previous CPU FIX03/UNO_FAST source; historical comparators, not drop-in replacements.
- experiments/: vocabulary extension, LR study, paired-prompt study; experimental only, not integrated. In particular study_answer.py contains historical host paths. Preserve unsuccessful results. Review actual result JSON; no quality or CUDA claim.
- SOURCE_MANIFEST.json: exact source provenance, byte length, SHA-256 and Git blob SHA. Original archived manifests may reference excluded inputs; do not treat source-only checkout as a complete archive.

## Missing inputs (authorized owner Library; NOT committed here)
Original binary checkpoints and raw corpora must be retrieved separately from owner-approved storage. Never reconstruct them from this source export.
| File | Library ID | SHA-256 |
|---|---|---|
| UNO_B2_512_CUDA_BRIDGE_20261128.zip | libfile_f4bf86045a8c8191b1d1446b5d673ba0 | bf9411bb68db523b585691d8ffc440c1aa702560eb5b99727142ba4231748343 |
| UNO_B2_512_AUDIT01_PATCH.zip | libfile_73fd9d1fd8a481919e3afd61feaa5270 | e691329077a16b4d556c747438dd608bc2c74de5fea271b44bdec49cad00a90c |
| train_cuda_audit02.py | libfile_5895d16f95a881918480e691e2066dc3 | 512b454c3434865c2fa94d858795e1fe4c0f0116e91c6242f73919fd22769e99 |
| UNO_B2_512_FAST03_PATCH.zip | libfile_9fd9b1ace87481919e446f4dd5497898 | 2dd3039d24ae0686a76b2cc2fd8ff3048f9f3df77cad4f07aa9469499cd398a4 |
| UNO_CORPUS_PREP_FIX03_20261128.zip | libfile_bd4a166241248191a7ef49234986929e | 2895631d4307090e7570f8e0cf95102c6a779e7d6558d681e7215748cabbbb1e |
| prepare_uno_fix04.py | libfile_addc3c4694508191bf19eb3baf077935 | 499d0b1b18a8d0ce381fa2eab0efdd1a8aab74a1edc24c04043a80cd62e2acf1 |
| UNO_ASTRA_MATH_AUDIT_RETURN_20261124.zip | libfile_ae456f1facd08191b8a59a13ec1fe561 | ea2b07e658a925e7f703637c2cfa4713d7247e6a995b2429566314b7f48b5c41 |
| UNO_CPU_TRAINING_20261126_FIX03.zip | libfile_896a6716ef7c819187c340e3da63f474 | 03c281dbc074610aa2efc94800158d8335ce74bdac89f5c1f108c40f7d2b6304 |
| UNO_CPU_RESEARCH_2000_BACKUP_20261127.zip | libfile_396ca2940f6c81918efc9b9689807d0c | e84aeaeddecc7104ef48fb3bf5e17092a8a1174acab7661f5dbb2cbfb9e40ff4 |
| UNO_B2_512_LANGUAGE_STEP000050_RESUME.zip | libfile_5f899193938c819183c08b7817dd9f73 | 2deffde3d01fe6f9a7a5e426add3b1406232e32ef3f09b802aa779649e64fe98 |

Eight original ZIPs checked with ZIP CRC and SHA-256 during preservation; two Python files hashed. The repository is public: no private logs, private corpora, held-out prompts, or large checkpoints are copied. Git binary archive preservation is PARTIAL, not complete.

## Next task
Deliver one coherent trainer. Audit data split, tokenizer coverage, causal state and answer conditioning, assistant-only masks, gradient/projection correctness, full-context windows, validation/free generation, LR and equal-budget comparisons; use existing F, do not replace with GRU/Transformer. Baseline FAST03 has 23,015,887 allocated and about 5,007,362 participating parameters with 514 IDs, fixed K1, S4/S6 inactive. Experiments suggest context truncation and very weak prompt conditioning; tiny tests do not establish cause or fix. Do not treat lower NLL as proof of understanding. No CUDA or full-real-corpus acceptance yet. Owner PC Ryzen 7 5700X, RTX 4060 Ti 8 GiB, 32 GB RAM; existing Python D:\UNO\env\Scripts\python.exe. All PC work stays within D:\UNO; no system/Gizmo changes, no new branch, no Actions, no merge. Use short GPU preflight and measured budget with atomic save/resume and reserve time for export.
