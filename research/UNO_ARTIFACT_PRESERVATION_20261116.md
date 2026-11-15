# UNO research artifacts: preservation and gap register (2026-11-16)

Status: PARTIAL INVENTORY; NOT A COMPLETE BACKUP. Existing branch only: `research/uno-train-001-s4-20261115`. Do not create another branch, rewrite history, delete originals, alter main/production, or run GitHub Actions without explicit owner authorization. Read main/AGENTS.md first. The owner requires all historical artifacts preserved in the existing repository and branch.

## Verified remote state
- TRAIN-001 sources/tests: `research/train001/`, `research/f-gradients/`.
- TRAIN-002 sources/tests/audit: `research/train002/`.
- TRAIN-002 Windows ZIP: `research/train002/delivery/UNO_TRAIN002_RTX_20261115.zip` (21,140,290 bytes, Git tree).
- TRAIN-001 baseline remains an ancestor; TRAIN-002 implementation commit `1427053ce92fc8479550520a4f90ab2f5366851b`; delivery commit `e3bbcdee7d00c2b1962ce30de7da8094064b8d8a`.
- These paths establish presence, NOT equality to every historical chat attachment.

## User-supplied conversation attachment inventory, NOT verified present in Git
The following file names were enumerated in the UNO conversation file surface. They are source artifacts, not authorization to replace current code:
- `UNO_F_PILOT_001.zip`
- `UNO_GPU_SAFE_002.zip`
- `UNO_F_MEMORY_003.zip`
- `UNO_F_WORKING_MEMORY_004.zip`
- `UNO_F_DIAG_FIX_005.zip` (multiple uploaded copies)
- `UNO_F_LADDER_005.zip`
- `UNO_F_LADDER_005_SAFE.zip` (multiple copies)
- `UNO_F_LADDER_005B.zip`
- `uno_ladder_005b_gpu.zip` (one attachment ~252,091,601 bytes)
- `UNO_005B_FINAL_WEIGHTS_AND_RESULTS_20261115.zip`
- `UNO_F_CAUSE_006.py`, `UNO_F_CAUSE_006_REPORT.txt` (multiple copies)
- `UNO_S4_WM_007.zip`
- `UNO_CODEX_TRAIN001_HANDOFF_20261115.zip`, `UNO_CODEX_TRAIN001_HANDOFF_20261115(1).zip` (latter ~37,766,879 bytes)
- `CODEX_TRAIN001_TASK_20261115.txt`
- `UNO_TRAIN001_RESULTS_20261115.zip` (multiple copies, one ~2,089,975 bytes)
- `README_RU.md`, `README_AUDIT_RU.md`, `README_RTX.md`, `CONTINUATION_RESULT.md`, `SUMMARY.txt`, `SUMMARY(1).txt`, other chat text/screenshots.

**Open gap:** A remote Git tree path/byte-level SHA256 match for each listed historical original has NOT been established. Do not mark complete based on similar source files or a written summary. Large ZIPs may require Git LFS; do not silently drop weights or upload GitHub-size-incompatible blobs.

## Completion procedure for any agent with file-upload and Git write access
1. Stay on the above existing branch, inspect current HEAD and main/AGENTS.md. Never create a branch.
2. Enumerate all conversation/library UNO attachments; materialize originals; compute SHA256, size and internal ZIP manifest; distinguish duplicate bytes from different versions.
3. Compare against all Git tree blobs and Git LFS objects; retain original ZIPs and reproducible training results. Preserve source provenance; no overwrites/deletes.
4. Upload only missing bytes in an appropriate `research/artifacts/` subdirectory, subject to repository limits, or record a concrete storage blocker. Never store a pointer-only placeholder as if it were the original archive.
5. Commit an updated hash/path/status inventory and independently fetch/verify the uploaded bytes. Mark COMPLETE only after all known originals have matching verified storage.
6. Do not infer that a past attachment exists in Git merely because a ChatGPT memory summary mentions it.
