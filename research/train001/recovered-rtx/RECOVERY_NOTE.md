# TRAIN-001 RTX port: exact restored bytes for six sources

The six original source files listed in `docs/recovery/LOCAL_PROVENANCE_20261119.json` were byte-for-byte recovered from the owner-supplied `UNO_CODEX_TRAIN001_HANDOFF_20261115.zip`. This folder intentionally omits all large exported TSV fixtures and numeric checkpoints. Use the original archive for exact `SHA256SUMS`, the five data TSVs, and all `parity*/` fixtures. Do not claim the missing Kotlin training source or its original Git commit is recovered. No model-training run was launched by this restoration.

## R5.4 Candidate — erratum 07 (local continuation)

`terminal_episode` is the supervised TRAIN001 boundary: a sequence of noise/WRITE followed by a single QUERY (-1 or -2), and an exact chronological bank of prior writes. The teacher is applied only in `loss` and scoring after forward; missing target is a miss, not an injected record. No change to the recurrent operator, training objective, or weights for valid original inputs. This is not a claim of Android semantic-memory Wk/Wv integration or of useful retrieval for arbitrary data.

Frozen CPU checks (no optimizer): `python causal_memory_regression_test.py <original CODEX handoff ZIP or exact parity fixture subset ZIP> <TRAIN001_INPUT directory>`; `python metrics_regression_test.py`. For frozen checkpoint evaluation use `replay_selected_metrics.py` with the original backend bytes (required for manifest validation), the original results ZIP and five TSVs. Existing CUDA receipts/checkpoints are tied to the original source digest; do not bypass resume/qualification checks for this changed backend.
