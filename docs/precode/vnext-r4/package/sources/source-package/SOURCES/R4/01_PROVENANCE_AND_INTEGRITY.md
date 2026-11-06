# 01. Provenance and integrity

## ASTRA artifact

- File: `ASTRA_UNO_MATH_DESIGN_AND_AUDIT_2026-11-02.zip`
- Size: 681 255 bytes
- SHA-256: `3420edf9cb7b2170b5c5e0938d43fc3ab896061a5c5fb16229d9587c2ea27987`
- ZIP `testzip()`: no corrupt member.
- Final package manifest: 116 entries, 116 exact byte/hash matches.
- Final author manifest: 18 entries, 18 exact byte/hash matches.
- R3 audited manifest: 18 entries, 18 exact byte/hash matches.
- Source hashes: 30 original files, 30 exact byte/hash matches.
- `ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` is byte-identical to the separately frozen R3 patch; SHA-256 `52b1eab23c977d253625b98de20bee6e5802c652973cf96403037118b5fbe4be`; no disallowed control characters.
- Four post-R3 files were diffed: matrix, red-team report, final README, revision log. Diffs are status/format-only; no normative equation, tensor, cost, probability, trust assumption or threshold changed.
- Fourteen of eighteen final author files are byte-identical to the effective R3 audited scope.

## V2.2 source

- File: `UNO_V2_2_INDEPENDENT_MATH_AND_PRECODE_CHECKPOINT_2026-11-02.zip`
- SHA-256: `639708aff644f562c98564b20311262c96105345637e5f3a6566d55c418ca50d`
- The archive was re-opened and its CRC check passed. It is included unchanged.

## Reproduction

ASTRA's `evidence/recompute.py` was copied into a separate working directory and run there. The resulting `arithmetic_v2.json` and `tensor_manifest_d1024.json` were byte-semantically identical to the committed JSON structures. The source archive was not modified.

An additional independent shape enumerator was authored for B2, LR2 and H2. It uses the documented tensor shapes and the declared INT8 packing policy: 4096-byte header, 128-byte descriptors, 64-byte alignment, matrix row stride rounded to 16 bytes, FP32 row scales, FP32 vectors (including `e_modality`), and INT8 matrices (including `W_wake`). LR2/H2 packed sizes below are independent derived estimates, not ASTRA-authored manifests or decoded-weight certificates.

## Scope of independent review

The archive's R1/R2/R3 reviewer reports are separate model-review artifacts with frozen inputs and hashes. They are not a human certification, formal proof assistant certificate, trained-model evaluation, Android security audit, or device measurement. Their conditional verdict is preserved exactly, not upgraded.
