# TRAIN-002 — diagnosis and minimal chronological S4

Same branch `research/uno-train-001-s4-20261115`. TRAIN001 code/results remain the control point. Main/production/Actions are unchanged. **Only short CPU diagnostics ran here. New task-quality training, CUDA and Windows execution remain pending.**

## Packet / Windows

Use the new TRAIN002 ZIP, extract into a new directory. Python3.12 x64, NVIDIA RTX4060Ti8GB and a driver supporting CUDA12.8. From the packet root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Check
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Plan
```

Check defaults to diagnostics; it never starts a task-quality training run. It checks byte hashes, CPU/CUDA numerical contracts, causal headers, balanced synthetic test fixtures, exact baseline parity and candidate gradients, then true process-kill/resume on CPU/CUDA. Only success creates `cuda-check.json`. No CPU fallback or claim of CUDA verification from CPU logs. OS/driver power-loss recovery and a whole long GPU run remain separately measurable.

After successful Check the owner explicitly chooses an execution command:

```powershell
# One predeclared run, from scratch:
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Train -Arm chrono_typed -Seed 260015
# Same run after interruption:
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Resume -Arm chrono_typed -Seed 260015
# Optional: progress through the declared matrix for at most1800 seconds per invocation.
# Repeat Suite to resume unfinished runs; completed checkpoints remain unchanged.
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Suite
# Only after ALL declared arms/seeds finish:
powershell -ExecutionPolicy Bypass -File .\Run.ps1 Evaluate
```

Never start Train/Suite automatically in the cloud. Do not run multiple copies/different packets concurrently on the same GPU. Resource guard checks GPU0 before updates, stops at≥78°C,≥6500MiB GPU usage or monitoring failure. One invocation has1800-second cap at optimizer boundaries; a current kernel/update/validation/checkpoint is not interrupted midway. Initialization publishes the run directory atomically only after checkpoint0 is complete; interrupted initialization folders remain preserved and do not block retry of an unpublished run. Source/data/plan/runtime/config mismatch, NaN/Inf, corruption or another writer causes refusal. Preserve `logs/`, `runs/`, check receipt and unchanged input/code files; no deletion/restart from scratch to conceal a failed run. SHA provides integrity, not authorship/signature.

## Fixed study and acceptance

Fresh data seed2026111502 is locked before training. Train864, validation144, test1152. Every family×length cell is label-balanced in paired complements; both members stay in one split. Independent hashed namespaces avoid the consecutive Java-seed correlation of the historic test. Exact raw/prefix train/validation/test overlaps are0. Training lengths12/24/32; eval lengths12/24/48/96. Test labels are not loaded by training. Final evaluation requires every declared run to finish and pins each checkpoint/selection before reading the test; crash retry uses the same pins, completed results are cached.

Families r1–r5 follow the earlier task meanings; r6_previous/r7_next/r8_last_value/r9_previous_version add explicit public request anchors/opcodes, equally visible to F and GRU. Anchors name the reference record, not the correct answer record. Neural relation tasks use existing neighbors only; the structural API returns None for missing links, but neural UNKNOWN/abstention is not trained. Oracle uses only raw observations. All writes/history remain in memory. No hand-selected gold read.

Nine arms × seeds260015/260016/260017 =27 runs,1000 updates each, batch4, identical train order, learning-rate schedule/clip/update budget. Main experiment is CUDA-only; no main cloud CPU training command. Initial F weights come from the unchanged Kotlin Ladder initializer, separately pinned per seed. State resets at episode start; memory is differentiable through the complete prefix≤96. No runtime self-learning or phone-memory persistence is claimed.

| Arm | Purpose |
|---|---|
| baseline_legacy | original S4 / original queried-record scalar target |
| baseline_typed | original S4 / all writes [raw scalar, public slot] |
| chrono_legacy | fixed chronological key feature / legacy target |
| chrono_typed | chronological key feature / typed target |
| f_no_memory | F trained without S4 computations/entries, state loss only |
| gru | GRU215 + tanh head, state loss; similar parameter allocation |
| frozen_write | Wk/Wv frozen at initialization, source F still differentiable |
| random_keys | nonlearned prefix-random keys, learned values/source F |
| permuted_values | reverse content association within eligible bank during training |

Chronology contrasts keep payload supervision identical. Typed-versus-legacy combines new fields with all-write coverage; it cannot alone attribute a gain to one of those changes. Inference controls memory_off, zero_values, erased, random keys, content reversal, clock shuffle and pair-order reversal are separately named, not passed off as trained baselines. New erased removes all written answer fields (r5 slot codes; others raw values), keeping labels/requests: this differs from the historic r1–r4 queried-slot-only erasure. Paired erasures become identical raw inputs with opposite labels: deterministic erased accuracy must therefore be exactly50%; evaluation rejects a violation.

F is the same d64/m128/b64/chi4/J2/K2 diagnostic geometry. Astra row caps remain. Fixed clock feature changes only k=tanh(Wk h+.5c), not F/S5 or parameter count; see MATH.md. This is a candidate extension to Astra04, not full equivalence/production approval. GRU is unconstrained; equal parameter count is not equal compute. Reports include allocated/trainable parameters, optimizer compute time, peak CUDA allocations; timings exclude validation/checkpoint and are not energy measurements. F_no_memory omits read/write computation; a read-disabled inference control is a distinct intervention. PyTorch/cuDNN execution differs by architecture.

Adam(.9,.999,eps1e-8), mean episode gradients, globalL2 clip1, warmup1000→2e-4, cosine schedule total2000/floor2e-5; no AMP/TF32. Euclidean L1 threshold uses FP64 then casts to FP32, cap tolerance2e-6. Fixed route, no full S6/halt/production heads. Validation every100 steps; select by aggregate state MSE only, not test.

Each future prediction export also includes true/predicted answer, actual read IDs/attention/logits, chosen record and causal/version headers with observed write fields and learned value coordinates0/1.

Evaluation reports per-run/per-family/per-length results and paired hierarchical seed+episode-pair bootstrap intervals. The same test-cluster draw is shared across seeds and stratified by family/length. Three seeds are few; intervals are pointwise/exploratory, without multiplicity correction. No pooled independent seed×episode count or general-language competence claim. There is no promised accuracy improvement before the actual matrix runs.

## Historic scientific result

`historical/audit.json` summarizes the old run. `historical/{full,memory_off,zero_values,erased}.jsonl.gz` contains complete record/key/value/source-state vectors. `historical/predictions-summary.jsonl.gz` covers all seven analyzed conditions with answers, read IDs, every attention distribution, headers and value coordinates0/1. Full extra-control vectors can be regenerated with the auditor and are hash-pinned in full_trace_manifest.json. The old test is already open and is never new acceptance data. Reproduced exactly:253/320 full;148/320 memory_off/zero_values;163/320 erased. groups.mse in the original report was an SSE; new analysis also gives normalized per-cell MSE.

Historic r5/96 has0 positive labels out of16 and0/16 correct key top1. There are64 reused write-prefix groups across r2/r5, with30 same-record incompatible legacy value targets. A train-only linear diagnostic probe of frozen key+value vectors distinguishes first/second write with86.72% accuracy on the historic test and decodes slot sign100%; this is not the UNO decoder or a new runtime head. Thus information about order is present; missing explicit chronology is not established as the sole cause. Routing, decoding and conflicting supervision are separately tested by the new matrix.

Historical bootstrap intervals are descriptive resampling only, not population coverage guarantees given correlated/imbalanced seed construction. Old RTX compute is source-reported; CPU re-evaluation and checkpoint/input/source hashes were independently verified here. No007 or old training reruns occurred.

## Source reproduction

Run `prepare.sh` from the repo with an absolute NEW output path. It compiles the existing Kotlin model plus only `PrepareInitial.kt`, creates the study/data, copies pinned source and audit artifacts and verifies the ZIP roundtrip. Kotlin is not needed to use the prepared Windows ZIP. Standalone historic audit: `audit_previous.py RESULTS DATA NEW_OUTPUT` using the unchanged TRAIN001 input files.

Return reports/logs plus per-arm checkpoint groups (three seeds per ZIP if attachment limits require). Keep old weights/history. A failed run is evidence; do not replace it with an undocumented seed or changed test.
