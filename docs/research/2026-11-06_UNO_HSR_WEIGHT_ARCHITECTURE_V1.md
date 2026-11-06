# UNO-HSR v1 — candidate weight representation (2026-11-06)

Status: EXPERIMENTAL, NOT an approved replacement for R5.3 F. Novel proposal in this project; no claim of novelty against all scientific literature.

Single-operator layer: y = U(Vx) + Sx, optionally with a learned bounded gate on the sparse correction. U in R^(n x r), V in R^(r x n), S row-sparse with at most k nonzero entries per row. The operator is shared inside one UNO organism. Structural plasticity may propose adding/removing S edges under bounded memory, provenance, rollback and independent evaluation; it cannot alter Android authority.

Complexity per layer: dense n^2 parameters/MAC, factorized 2nr, HSR 2nr+nk plus index storage (k integer column indices per row). Example n=256, r=32, k=4: 65,536 vs 17,408 numeric coefficients; 1,024 integer indices additionally. Sparse indirection may negate theoretical speedup on real CPUs/NPUs; energy is UNKNOWN.

Reproducible synthetic comparison: research/weight-kernels/hsr_synthetic_comparison.py (NumPy, deterministic seed 20261106). Target = low-rank random matrix plus four random corrections per row. Fit truncated SVD rank32, then choose four largest residual entries per row. Output errors on common random inputs: dense 0.0; rank32 ~0.678723; HSR ~0.382501. This is a biased synthetic construction, not language/vision/reasoning quality. Dense is exact by definition; SVD fit is not trained neural inference.

Potential refinements: per-block rank selection, sparse residual budgets, skip unselected blocks before execution, integer quantization with calibrated scales, selective local plasticity, structured sparse layout to avoid cache misses. All remain untested.

Acceptance: same licensed dataset, same train budget and locked holdout; compare B2, LR2, H2, dense, factorized, N0 and HSR on task quality, catastrophic forgetting, p95/p99, peak RAM, energy joules/task and thermal behavior on A52. If HSR fails quality, do not select it regardless of coefficient savings. No model training authorization inferred.
