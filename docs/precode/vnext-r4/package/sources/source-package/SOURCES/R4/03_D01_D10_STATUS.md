# 03. D01–D10 crosswalk after ASTRA

Rule: distinguish mathematical/specification completion from empirical/product completion.

| ID | What ASTRA now specifies | What remains open |
|---|---|---|
|D01 Task battery|12 task strata, independent labels, coverage and false-action metrics, candidate thresholds|Owner has not approved thresholds; V2.2's 13-class map is not explicitly reconciled: WAKE and SENSOR have no separate acceptance rows.|
|D02 Weights/ABI|B2 shapes, tensor registry, free/frozen counts, tied embedding, quantization classes, decoded norm gates|No trained/decoded model; LR2/H2 manifests and quant certificates not official; architecture not selected.|
|D03 Training|Losses, L3a per-stratum coverage, BPTT, score-function gradient, optimizer, QAT and data manifest|No licensed corpus/consent manifests or trained Θ. Explicit sensor dataset/targets and wake-relevance dataset/targets are absent.|
|D04 Memory|M/L/U/P roles, provenance, TTL, quotas, migration, crash/retention and P update|Compatibility predicate, conflict-aware retrieval and raw-payload read path are underdefined; no real persistence/rollback/retention tests.|
|D05 Authority/STOP|Typed proposals, owner digest consent, STOP/epoch/ν, PREPARED/MAY_HAVE_EXECUTED, guarded commit|Owner identity/authentication method is not specified; A_cap/A_ui/A_tx/A_fs and OS behavior remain assumptions; no A52 traces.|
|D06 Perception/planning|Text, CTC, TTS DSP, image patches, sensor and OS shapes; goals and bounded plans|RU ASR/TTS, screen, sensor, wake and long-horizon planning quality are untested; no full data battery.|
|D07 Resources|MAC, packed weights, explicit memory, training memory and lower-bound latency arithmetic|No A52 PSS, p95/p99, battery joules, thermal or sustained throughput measurements.|
|D08 NCR-EVO|Bounded DSL, surrogate, QD archive, inclusion probabilities, HT estimator, holdout and power plan|No sandbox audit, no A/B/C/D experiment, no evidence of superiority or affordable compute.|
|D09 Build/ABI graph|Typed manifests, dependency DAG, toolchain and offline build constraints|No selected model ABI/build artifact; strict offline behavior of external SAF providers is not resolved.|
|D10 Risk/release|Threat model, denial conditions, failure and release stop criteria|Owner-approved threat/quality limits, independent security audit, per-verb Android validation and device tests absent.|

## D01 stratum crosswalk

V2.2 listed 13 explicit classes: RU-TEXT, RU-ASR, WAKE, RU-TTS, SCREEN, SENSOR, GOALS, PLANNING, ACTION, MEMORY, ADAPTATION, RESOURCE, OFFLINE-SECURITY. ASTRA's D01 uses 12 rows. Most map naturally, but WAKE and SENSOR are not explicitly traceable to independent acceptance rows or data sources. Do not assume they are covered merely because `W_wake` and `W_sensor` tensors exist.

The ASTRA data table lists no explicit sensor corpus/target and no separate ambient-wake relevance corpus. If those are optional, mark them optional and disable/freeze corresponding paths; if required, add strata, labels, false-wake/false-reject metrics, sensor prediction/grounding tasks and legal data.

**D01–D10 full verdict: NOT PASS.** The design contracts are much more complete, but quality, data, training, trust implementation and physical gates remain.
