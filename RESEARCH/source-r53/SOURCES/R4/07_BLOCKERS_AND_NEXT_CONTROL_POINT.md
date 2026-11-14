# 07. B01–B14 and next control point

## Updated blocker register

| ID | Status after ASTRA | Exact remaining closure |
|---|---|---|
|B01 Owner acceptance|OPEN|Owner-approved q/c/f and quality, coverage, false-action, RAM, latency and energy thresholds.|
|B02 Legal data|OPEN|Signed rights/consent manifests for dialogue, ASR, TTS, screen, actions, memory, wake and sensors.|
|B03 Trained Θ|OPEN|Actual new B2 or chosen alternative weights, run logs, tensor gradient coverage, locked evaluation and retention tests.|
|B04 Quant ABI|CONTRACT RESOLVED FOR B2|Still requires chosen model ABI, real export/dequant norm and backend parity; LR2/H2 need their own manifests if retained.|
|B05 Model selection|OPEN|Same locked task battery and quality/resource comparison B2 vs LR2/H2 across feasible d.|
|B06 A52 resources|OPEN|Physical inventory and sustained p95/p99, PSS, battery energy, DSP, thermals and offline traces.|
|B07 Android verbs|SPECIFIED / UNTESTED|Per-verb native API, permission, endpoint and failure traces on target API/device.|
|B08 Trust/storage|OPEN|Owner identity/authentication, STOP/dispatch serialization, durable WAL, anti-replay/freshness and crash/rollback fault injection.|
|B09 Memory/retention|PARTIAL|Conflict-aware retrieval, payload access, compatibility rules, quotas, expiry and migration tests.|
|B10 NCR-EVO|SPECIFIED / UNTESTED|Sandbox audit, preregistered equal-budget experiment, fresh holdout and independent replication.|
|B11 External review|PARTIAL|ASTRA R1/R2/R3 model-review evidence is present and hash-bound; not human/external certification; IR findings require resolution.|
|B12 Astra registry|RESOLVED AS ARTIFACT|Final archive found, hashes checked, arithmetic rerun and integrated.|
|B13 ASR/TTS/screen success|OPEN|Licensed corpora and independent language/UI ground truth, measured results.|
|B14 Toolchain/release|NOT ATTEMPTED / NOT AUTHORIZED|No code/build/release until separate owner decision and prior gates.|

## Gate status

- G0 owner requirements: NOT PASSED.
- G1 formal subclaims: CONDITIONAL; not a universal or machine-certified proof.
- G2 pre-code specification: substantially specified, but IR01–IR07 and owner/data decisions remain.
- G3 trained full Θ and locked capability tests: NOT PASSED.
- G4 PRE-CODE BASELINE: NOT AUTHORIZED; owner decision reserved.
- G5/G6 APK and production integration: NOT ATTEMPTED.

## Next work, still paper-only

1. Correct W4 with `c_M` and explicit `b_B`; preserve full-mask and fair-sweep theorems separately.
2. Define memory compatibility/conflict semantics and raw-payload retrieval path.
3. Reconcile the 12 vs 13 task strata; explicitly decide WAKE/SENSOR required or optional and define data/metrics.
4. Specify owner enrollment/authentication and digest-bound secure confirmation.
5. Decide whether cyclic-prefix masks are acceptable or whether arbitrary PL/top-q masks are required.
6. If LR2/H2 remain candidates, freeze their own tensor/ABI manifests and decoded norm checks.
7. Keep B01–B03/B06–B13 empirical gates open until legal data, trained weights and A52 measurements exist.
8. Do not choose d or graph family from parameter/MAC savings alone.
9. Do not write production code, train, build APK, modify repositories, or run GitHub Actions under this checkpoint.

No final baseline is proposed by this document.
