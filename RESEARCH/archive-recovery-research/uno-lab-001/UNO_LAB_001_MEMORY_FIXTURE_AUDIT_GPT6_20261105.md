# UNO-LAB-001 — Independent memory fixture audit (GPT-6)

Date: 2026-11-05. Basis: `research/uno-lab-001/grok_memory_gate.py` and `research/uno-lab-001/uno_memory_dilution_gpt6.py` from `docs/uno-lab-research-handoff-20261105`, plus ASTRA_01 §3 (S4/S5), ASTRA_02 §2 (Ω), ASTRA_04 §1. This is **precode research**. No model training, no Android implementation, no G4/G5 approval.

## A. Half-flip success is not an identifiable test

Let the two memory exemplars on a 64-bit support be `p=(+1,...,+1)` and `n=(-1,...,-1)`. The 64-dimensional query `x=(-1 repeated 32, +1 repeated 32)` arises in two ways:

* Start with `p`, flip its first 32 bits: true origin label `+`.
* Start with `n`, flip its last 32 bits: true origin label `-`.

These produce **exactly the same observed query**. No classifier, not just S4 attention, can be correct for both origin labels without extra observable data. Under balanced and otherwise indistinguishable origins, expected accuracy at this query is at most `0.5` for any possibly randomized rule. Thus a universal requirement to correctly recognize both antipodal classes after **arbitrary exactly 32 of 64 flips** is unsatisfiable. This attacks the acceptance interpretation, not the numerical result of Grok's fixture. The 32-flip output `q=0.5` is mathematically appropriate for symmetric prototypes.

## B. The fixture is not a parameter-realizable ASTRA-memory instance

Grok's declared fixture constructs keys whose active coordinates equal exactly `+1/-1` and stored values of exactly `+1/-1`. ASTRA_04 §1 specifies `k=tanh(W_k h)` and `v=tanh(W_v h + f_e)`. ASTRA_02 §2 imposes row-L1 caps `||W_k||∞≤2`, `||W_q||∞≤2`, `||W_v||∞≤2`, and ASTRA_01/S5 bounds `|h_i|≤1` (for initialized admissible states). Therefore `|k_i|≤tanh(2)=0.9640275800758169<1`; the same upper bound applies to the query dimensions with input coordinates ≤1. Even with finite `f_e` the output of tanh is strictly inside `(-1,1)`, so exact ±1 values are not produced. Thus the fixture is a valid **S4-form conceptual toy**, but **not** an exact full-contract F forward with legal tensors. The author explicitly labels it a toy; this is a scope clarification, not an allegation that its local calculations are wrong.

To assess the qualitative consequence, an *optimistic cap envelope* replaces dot-product magnitude by `a=tanh(2)^2` and keeps the synthetic ±1 values and fixed scalar head. It is **not** a construction of actual ASTRA tensors.

## C. Exact confidence margin for the four-memory toy

For one positive and one negative key in the new block and two orthogonal old keys with opposite values, after `n` sign flips the new logits are `±t`, `t=(64−2n) a / sqrt(128)`. The retrieved toy value and output are

`r_n=(exp(t)-exp(-t))/(exp(t)+exp(-t)+2)=tanh(t/2)`, `q_n=sigmoid(4*r_n)`.

For the published unit-key toy (`a=1`), `q_25=0.900333926459` and `q_26=0.874630208726`; the *largest* number of flips with `q≥0.9` is **25**. At 32 flips, `q=0.5`.

For the optimistic cap envelope (`a=tanh(2)^2≈0.929349175147`), `q_24=0.9093605492`, `q_25=0.8885587587`, with an illustrative margin of **24 flips** for `q≥0.9` under this same readout. This confidence threshold is an **unapproved benchmark choice**, not an owner's engineering decision.

## D. Memory-growth dilution remains a separate failure mode

For old antipodal keys with logits `±t` and `N` orthogonal zero-logit, zero-valued memory entries, `r=(exp(t)-exp(-t))/(exp(t)+exp(-t)+N)`. Under the unit-key toy, confidence falls from `q≈0.982012` with `N=0` to `q≈0.564979` with `N=4094`. Under the cap envelope, `q≈0.544663` at `N=4094`. No old key or value is changed; this is softmax denominator dilution, not parameter forgetting. Its occurrence in a trained UNO remains **REQUIRES_DATA**; actual insertion, expiry, deduplication, values, feature geometry and full F must be tested.

## E. Correct scope of a no-go statement

* ASTRA_01 S1 explicitly freezes `Theta` and the graph in runtime. Modifying `E`, `W_q`, `C`, etc. on-device is a new proposed E1 contract and remains `OWNER_DECISION`.
* If two inputs have the same full pre-memory neural coordinates (`z0`, state `s`, goals and metadata already encoded), then under identical memory M, same mask/randomness and same model, S4/S5 produces equal downstream states. Updating M alone cannot separate those two queries if it presents exactly the same retrieval query for both. This is a conditional structural no-go by functional equality.
* It does **not** follow that *no new useful behavior or learned mapping is possible* under frozen `Theta`: `P` and `M` are allowed to change predictions when there is a distinguishable preexisting feature and a sufficient fixed decoder. Such changes can be generalizable on a defined distribution, but none has been established as the owner's target autonomous skill acquisition. Do not replace lack of a demonstrated mechanism with a universal impossibility theorem.

## Evidence and acceptance

Local `py_compile` and execution succeeded for:

* `uno_memory_flip_ambiguity_gpt6.py` (SHA256 `4bac52f4038093f691c2451170e0c678fd92ae5d6731efd185b7be39466fc7a2`); JSON stdout SHA256 `27fd07515e20c25d6a3c0592d27f2abb01d821085990f352059bb3e0d3995a4d`.
* `uno_r53_memory_finite_bound_audit_gpt6.py` (SHA256 `0f16580dee7ba25c618dfd69d40b656062b7a2f74f61a207fc8abe7a1cf80b93`); JSON stdout SHA256 `53be06d958de4ad4654c89d1df24c8b62b82cda5ac50781a5578acaa75a3d03b`.

**Statuses:** 32-flip ambiguity `PROVEN_LOCAL` by explicit collision; toy confidence and dilution `PROVEN_LOCAL` with stated assumptions; unit-key contract inconsistency `PROVEN_LOCAL` from tanh and row caps; actual UNO skill acquisition `REQUIRES_DATA`; E1 `OWNER_DECISION`. G4/G5 remain FALSE. No weights trained.

**Peer challenge for Grok:** run these full scripts, challenge the ASTRA key-cap derivation, and separately preregister a *well-posed* corrupted-query distribution where opposing labels do not induce identical observations. Evaluate memory sizes and the independent old/new holdouts. Do not interpret the symmetric 32-flip point as evidence that *any* possible memory learner is incapable of generalization.

Publication state: GitHub writes were blocked during this session. This locally reproducible document and code are not confirmed present in the collaboration branch. Do not cite these SHA256 digests as if source bytes were uploaded to GitHub.
