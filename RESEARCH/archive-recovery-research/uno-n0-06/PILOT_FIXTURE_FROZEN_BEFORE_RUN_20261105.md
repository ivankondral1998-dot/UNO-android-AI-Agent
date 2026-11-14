# UNO-N0-06 / HOST PILOT FIXTURE — frozen BEFORE execution (2026-11-05)

Research-only; no Android actions; no production runtime. Parent: `research/uno-n0-06/RESEARCH_CARD_CANDIDATE_20261105.md`. Owner teaching / sensor observation / Android receipts are distinct source types in one shared ledger. This fixture is **synthetic** and is NOT the physical N0-05 400-row trace.

## Baseline and policies (all implemented as auditable code)

- **N0-05 original Java `NeuralGraph`**: read from unchanged `research/uno-n0-05` source, compile same Java file with compile-only `org.json` stubs; update on every TRAIN mistake only; freeze during TEST. Do not claim reimplementation equivalence unless compiling the original file.
- **Persistence**: predict previous sensor label; **Markov**: use the unchanged `NeuralGraph.MarkovBaseline` with mode/previous and learned train counts.
- **Candidate C1**: one event-sourced, categorical context ledger keyed by (mode, older, previous), with per-label observation counts (NOT numerical synaptic weights). Record every training observation, even when it matches prediction. At inference use a unique majority only if support >=3 and winning count - second count >=2, otherwise fall back to previous. Keep conflicting observations instead of permanent rule suppression. These numeric count thresholds are an experimental hypothesis only.
- **Owner-teaching contract**: owner correction is recorded as an assertion about meaning/intention, tied to a cue and revision. It MUST NOT change the factual physical event or grant OS permission. Conflicts are kept for review, not overwritten without provenance.
- **Android readback contract**: all inputs are MOCK. Dispatch-only, unknown, may-have-executed, old receipt, unrelated operation, missing owner capability or STOP-before-dispatch MUST NOT admit positive outcome learning; a fresh matching independent postcondition with valid authority may admit. Do not interpret mock success as actual Android validation.

## Deterministic sensor fixture (locked)

Sequence length 160 valid *prospective* physical-label windows, MODE=B throughout; first 80 TRAIN, next 80 TEST (unseen to train). Initial older=STILL, previous=STILL. 32-bit xorshift state starts `0x05EED006`; per window apply `x ^= (x << 13) & 0xffffffff; x ^= x >> 17; x ^= (x << 5) & 0xffffffff; x &= 0xffffffff`. Let `k=x % 97` (unsigned). Generate actual NEXT label as follows, in this priority order:

- If previous=STILL: target MOVE for k<14, else STILL.
- If previous=MOVE: target JOLT for k<4; else STILL for k<72; else MOVE.
- If previous=JOLT: target STILL.

After scoring prediction, advance older=previous, previous=actual. The N0-05 and C1 models get exactly the same input/actual sequence, no label leakage. Persistence and Markov use same stream. Report class transitions, error counts, context coverage, C1 prediction differences, and actual `CONTESTED` sources (for N0-05 only). No metric retuning after run. These generated distributions are not validated as realistic phone movements; physical energy / PSS are not measured.

## Locked assertions

1. Program compiles untouched N0-05 Java graph and a newly isolated pilot; only research paths are written, with SHA256 of code and output.
2. For each candidate 80 frozen tests: predictions are prospective, counts and gain/loss algebra consistent. Deterministic repeat runs must produce byte-identical stdout.
3. A separate exact-context contradiction must show the original N0-05 `CONTESTED` behaviour and inability to recover automatically from repeated same-class matching events after demotion (if the actual algorithm does so; otherwise explicitly record failure of premise).
4. Owner corrections have no power to alter sensor outcome logs or authorization. Unknown/mismatched receipts cannot enter verified outcome memory. Explicit `STOP` prevents mock dispatch.
5. Any accuracy difference is LOCAL_SYNTHETIC only. If candidate is worse than baselines it is a negative result, not grounds for unregistered modification.

Environment: host Java 21 (local); no device, no internet, no GitHub Actions; script/test executed once within <=600 s and <=2 GiB; no production code.