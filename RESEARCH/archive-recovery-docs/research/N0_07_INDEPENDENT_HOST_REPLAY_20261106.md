# UNO N0-07 — independent host replay (2026-11-06)

**Status:** HOST_TESTED_SYNTHETIC_ONLY. Tiny F does not beat the fixed baselines. This is not production approval or device validation.

## Reproducibility

- Input source package `UNO_N0_GIT_READY_VERIFIED_20261106.zip`, SHA-256 `f7bc26a718bea2ad905253fad44aa48e219328994deafd5c8de61de1ac96ba0c`.
- Independently verified 83/83 manifest paths, byte lengths and SHA-256; ZIP CRC PASS; 4 Python files AST parsed (not executed).
- N0-07 `run_host.sh` SHA-256 `79439005f4a2c02ea5fdd25222f97c6b60ac5ab19dca468f282b7ad0a091d2d1`. Executed on Linux OpenJDK 21.0.12.1, exit 0.
- Captured complete stdout: `N007_HOST_REPLAY_STDOUT.txt`, 1122 bytes, SHA-256 `f484513b08b7914ce7b83415c03422962ddaca4baf996fd193cd0c3bf36cbb4f`. Saved as local owner artifact, not in this Git tree.
- Host reported `UNIT_CONTRACT_PASS checks=28`, `SYNTHETIC_RESTORE_PASS`, `CHECKS_TOTAL=8434`.

## Synthetic observations

| Stage | Tiny F | N0-05 graph | Persistence | Markov | STILL |
|---|---:|---:|---:|---:|---:|
| 1 | 42/80 | 49/80 | 54/80 | 52/80 | 44/80 |
| 2 | 39/80 | 56/80 | 56/80 | 60/80 | 39/80 |
| 3 | 30/80 | 36/80 | 43/80 | 38/80 | 22/80 |
| 4 | 41/80 | 41/80 | 41/80 | 41/80 | 20/80 |
| 5 | 19/80 | 47/80 | 46/80 | 49/80 | 55/80 |

Frozen aggregate (stages 3–5): **Tiny F 99/240 (41.25%)**, N0-05 144/240 (60%), persistence 143/240 (59.58%), Markov 150/240 (62.5%). Tiny F trails Markov by 51/240 predictions. This is a deterministic synthetic comparison, not population-level significance.

## Gates

- **PROVEN_LOCAL:** source compiles, host checks execute, synthetic restore passes in this replay.
- **FAIL (candidate comparison):** Tiny F is worse than all three declared baselines on frozen aggregate.
- **SPECIFIED_UNTESTED:** Android native action/readback, actual A52 energy and thermal, full R5.3, owner teaching effectiveness, offline authority, real-world learning.
- **OWNER_DECISION:** G4 PRECODE_CANDIDATE; OWNER_APPROVED_PRECODE=FALSE; PRODUCTION_CODE_AUTHORIZED=FALSE. No G5.

**Next bounded research candidate:** pre-register seed-controlled ablations for selector, state update and label separation; compare to the same baselines on a locked holdout. Do not overwrite the original N0-07 frozen baseline. Original research source archive and separate source-only extraction are indexed in [N0 handoff](N0_SOURCE_ONLY_RECOVERY_HANDOFF_20261106.md).
