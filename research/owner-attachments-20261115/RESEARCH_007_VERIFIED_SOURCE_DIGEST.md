# 007 S4 Working Memory — digest from owner's original ZIP

**Source of this digest:** `UNO_S4_WM_007.zip`, 4,022,100 bytes, SHA-256 `d9ac20652576b788d60cf951e708ad22d7fae00fca35c9c7ae008149cc5bf2d8`. The ZIP is a conversation attachment, **not yet an independent Git blob**. This digest is a navigational aid and is **not** a substitute for the source, `.pt` files, or tests.

## Implementation and limits

`uno_s4_wm_007.py` (18,990 bytes, SHA-256 prefix `b0d50bfa270bf742`), `test_007.py` (6,199 bytes, SHA-256 prefix `b4ad0cbe6d1603c9`), `README_RU.md` (8,275 bytes), `CPU_VERIFIED/RESULTS_SUMMARY.json` (10,946 bytes), seed F-006 and three CPU checkpoint weights are present in the original.

F processes **all** events including noise. A separate addressable bank stores observed `WRITE(value,slot)` and overwrites by slot. At query time, the original F/S4 reads 2 or 3 entries via q, softmax and r. Public requested slot is provided as g. The F core is frozen; only `Ug/Wq/Wr` and a head are trained. Keys are **fixed** orthogonal ±0.99 and values fixed encodings. Thus 007 **does not** demonstrate learned `Wk/Wv`, autonomous write decisions, durable memory, Android execution, or full Astra04.

## Original reported CPU results (length 96; 512 fresh synthetic episodes per cell)

| Task | F no memory | F+S4/g/route loss | erase needed record |
|---|---:|---:|---:|
| 2 slots | 46.88% | 99.41% | 54.30% |
| 3 slots | 51.37% | 98.63% | 49.22% |
| 3 slots, overwrite | 48.24% | 98.44% | 51.95% |

Seed 47, 200 steps/task, batch32, key gain0.99. Original README reports CPU `test_007.py` 14/14 PASS and interruption/resume exact weights/Adam/RNG/history for a short diagnostic. **These are source-reported historical checks, not re-run by this Git digest.** No RTX execution of 007 was reported.

**Important confounder:** no-memory updates only 129 parameters vs 49,281 for S4, so this is not a capacity-matched F-only comparison. 007's near-99% cannot be compared as if it were the learned S4 TRAIN-001 result.

## Relation to later work

- 006: CPU diagnostic, frozen or prior F state.
- 007: fixed slot keys, frozen core F, learned reader/head, near-perfect *simpler* synthetic slot lookup.
- TRAIN-001: jointly trained F+S4 learned key/value writer; 253/320 vs inference-disabled memory 148/320 on a different test, one seed.
- TRAIN-002: CPU reproduction, conflicting auxiliary targets, chronology candidates, 27-run matrix **not yet executed**.

## Preservation decision

The owner's current requirement is **usable research material**, not unconditional retention of a 252 MB ZIP or every historical optimizer checkpoint. Keep the raw-archive audit as an *optional, separate* archival metric. Required for agent usability: source code, protocol/configuration, result records, necessary final weights and limitations. Do not claim these items uploaded just because they are described here.
