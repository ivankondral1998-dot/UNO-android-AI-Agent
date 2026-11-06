# 05. Additional independent integration findings IR01–IR08

These findings do not erase the ASTRA R1/R2/R3 record. They are additional cross-version checks against V2.2 obligations and the complete B2 text.

## IR01 — W4 masked Lipschitz bound needs a mask-dependent coefficient

ASTRA defines a full-mask leaky contraction `c=1-α(1-γ)=0.95` for α=0.5, γ=0.9. But S6 normally permits sparse prefix masks. For an inactive block `M_j=0`, the recurrence is `h'_j=h_j` exactly. Therefore the global infinity-norm Lipschitz coefficient of a sparse masked step is at least 1; it cannot be 0.95.

Counterexample: choose two states differing only in one inactive coordinate. After the step, that coordinate difference is unchanged. Thus a bound using c=0.95 for every fixed M is false.

Corrected coefficient:
\[
c_M=\max_j\{1-\alpha M_j(1-\gamma)\}.
\]
Full mask gives c_M=0.95; any mask with at least one inactive block gives c_M=1. W4 should use c_M in both `c_M^K` and the geometric sum. The symbol `b_0` in the z-sensitivity term also needs an explicit definition, e.g. `b_B=max_{l,j}||B_{lj}||∞≤0.9`. This is a local correctable proof-bound defect; it does not refute the fixed-z full-mask contraction theorem or fair-sweep theorem.

## IR02 — Memory aggregation can erase contradictory records; raw payload retrieval is not in S4

S4 defines `r=Σ_i ω_i v_i` over all live representation-compatible entries. The compatibility predicate is not formalized. The worker receives the weighted latent aggregate, not record IDs/raw payload bytes in the written equation. `L_memory_use` trains an autoregressive answer from key/value embeddings; no bounded raw-payload retrieval interface is specified.

Counterexample: two records have identical key and equal score, values `v` and `-v`; then `ω_1=ω_2=1/2` and `r=0`, identical to an empty/zero-valued memory context. Contradictory evidence can be cancelled by aggregation. This does not prove typical trained memory will fail, but it refutes any guarantee that the current aggregate preserves every conflicting record.

D04 needs an explicit deterministic compatibility filter, conflict representation, retrieval result semantics (top-k record refs or equivalent), and a bounded route for raw payload/provenance when exact recall is required. If only latent summary is promised, D01 memory metrics must say so and test contradictions/expiry separately. Until then memory semantics are partial.

## IR03 — WAKE and SENSOR are not traceable to the 12-row D01 battery/data manifest

V2.2 had separate WAKE and SENSOR strata. ASTRA's 12-row battery does not name either. The model still has `W_wake`/`L_wake` and `W_sensor`, but the data-source table has no explicit wake-relevance or sensor corpus/targets. These weights may receive indirect gradients in some tasks, but that is not a defined coverage contract.

Either explicitly map and test them, or mark them optional/unavailable and do not claim their functionality in the product battery. This is a D01/D03 scope/data blocker, not a tensor-count error.

## IR04 — Owner identity/authentication remains an assumption

The gate requires digest-bound owner consent and an `owner` field, but no concrete owner enrollment/authentication protocol is defined: how the app establishes the owner, how confirmation is bound to the real user session, how lock state/multi-user profiles/overlay or tapjacking are handled, and what expires the consent. R3's authority proof is conditional on trusted owner/controller inputs; it does not manufacture that trust root.

D05/B08 remain open until the owner-authentication and secure-confirmation contract is chosen and later tested. No neural head may create or modify owner identity/consent.

## IR05 — Prefix selector is a narrower policy than the prior PL/RuntimeBudgetBuilder

ASTRA's `σ_rot` fixes cyclic block order and samples q; it does not sample arbitrary permutations/top-q subsets. At n_b=16, only 241 cyclic-prefix masks occur across rotations, versus 65 535 possible nonempty masks. The old X01/PL proposal allowed arbitrary top-q subsets. The new family fixes train/runtime support mismatch but reduces learned per-block allocation flexibility. This is a design substitution requiring explicit owner acceptance and a same-task/quality/resource comparison, not an automatic equivalence.

## IR06 — Strict offline boundary and external SAF providers

The app itself has no INTERNET permission, but `READ_DOCUMENT` uses a user-selected Android document provider. A provider app can itself fetch remote content. This does not mean UNO has a cloud model, but it can violate a strict whole-workflow zero-network claim. D09 must specify local-provider-only behavior or a clearly separate, explicit user opt-in that is outside the offline product guarantee. No silent cloud provider fallback.

## IR07 — LR2/H2 alternatives have derived counts, not official manifests/certificates

Independent counts and packed-byte estimates are included in `02`. The official ASTRA tensor manifest is for B2 d=1024. LR2/H2 remain alternatives; before either is selected, generate its own ordered tensor manifest, ABI descriptors, quantized/dequantized norm certificate, memory/traffic ledger and backend parity oracle. Do not infer feasibility from the table alone.

## IR08 — Full B2 text-event cost supersedes the V2.2 lower bound

V2.2 explicitly counted F+vocabulary only as a lower bound. ASTRA adds per-event encoder, memory scan, selector and wake terms. At d=1024, 128 tokens rise from 22 011 707 392 lower-bound MAC to 22 457 364 480 full event MAC. This is a correction in accounting, not a contradiction in parameter counts. Full task cost still adds proposal, turn-end belief, DSP/IPC and any memory writes.
