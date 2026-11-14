# 04. X01–X12 crosswalk

| ID | V2.2 obligation | ASTRA integration status |
|---|---|---|
|X01|Training/runtime mask support and budget selection|**Conditional / design changed.** ASTRA uses nonempty cyclic-prefix masks with one law in training/runtime. This closes the old support mismatch for that narrower policy, but it is not equivalent to arbitrary `BudgetTop` subsets. Owner acceptance and quality/efficiency comparison remain.|
|X02|Exact gradient for discrete selector, K and wake|**Formula conditional PASS.** General score-function identity covers categorical prefix q and Bernoulli K/wake. A new toy finite-difference check for prefix+halt gives absolute error 2.70e-12. Old Plackett–Luce finite-difference result is not reused as proof of this different policy.|
|X03|Late physical effect after STOP|**Conditional.** Physical state and decision status are separated; late readback may be recorded but cannot update P after stale epoch/STOP. Depends on durable L/D and A_tx/A_fs.|
|X04|Crash ambiguity and no blind retry|**Conditional PASS.** PREPARED/MAY_HAVE_EXECUTED and UNKNOWN prohibit silent automatic replay; operation-specific idempotency remains external.|
|X05|Atomic P/evidence/used-ticket commit|**Conditional.** Single guarded transaction is specified; actual filesystem/database atomicity and crash fault injection absent.|
|X06|Quantization class and decoded norms|**Specification resolved for B2.** `e_modality` FP32 vector class; `W_wake` INT8_ROW; row scales/alignment and post-dequant norm checks specified. No trained export/parity test.|
|X07|LR64 expressivity counterexample|**Resolved mathematically.** Rank64 is not equivalent to B2; span-129 counterexample retained. Actual quality impact unknown.|
|X08|Identity of extra 128(d+1) parameters|**Resolved.** B2 tensor registry contains `W_R[128,d]` and `b_R[128]`; only rows 3–23 trainable.|
|X09|Full text and multimodal compute|**Updated.** Full event accounting includes encoder, memory, selector and heads. V2.2 22.012B is only F+vocabulary lower bound; ASTRA full 128-token event total is 22.457B MAC.|
|X10|Adaptive holdout bias|**Conditional PASS.** Fixed-pool inclusion probabilities/HT identity and fresh locked holdout are specified. No NCR experiment.|
|X11|Android API/verb constraints|**Specified, not tested.** 24 verbs and per-verb endpoint constraints exist; A52 and target OS tests absent.|
|X12|Actual full weights/training|**OPEN.** No licensed full corpus, trained Θ, locked metrics or device results.|

## Prefix-mask count at d=1024

With `n_b=16`, ASTRA's cyclic-prefix family has `16*15+1=241` distinct nonempty masks across rotations (q=1…15 gives 16 cyclic intervals each; q=16 gives one full mask). For q=3 it permits 16 cyclic triples, versus `C(16,3)=560` arbitrary three-block subsets in a general permutation/top-q builder. The new law is simpler and fairer to analyze, but has a narrower selection family.
