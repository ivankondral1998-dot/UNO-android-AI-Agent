# 06. End-to-end consistency audit

## Coherent parts

1. **Input and state:** modality-specific front ends feed one shared state and one time-shared recurrent F. Modality heads do not constitute independent brains.
2. **Weights:** B2 tensor shapes, allocated/free/frozen distinction, tied text embedding/output and new W_R observability head are internally consistent with the parameter totals.
3. **Conditional computation:** nonempty masks only; q and K are stochastic decisions; the same declared law is used in training/runtime. STOP/resource abort is terminal and remains in the issued-task denominator.
4. **Learning:** offline Θ objective fixes P=0; online P update is a separate projected update on a fresh verified binary endpoint. No meta-gradient through historical P adaptation is claimed. Causal attribution is distinct from observed completion.
5. **Memory:** M is untrusted episodic context; L is trusted outcome/physical-obligation ledger; U holds hypotheses/diagnostics; P is not authority. Model-version migration requires raw source and re-encoding; otherwise quarantine/UNKNOWN.
6. **Goals:** CURRENT_ALL and OBSERVED_ALL have different temporal semantics; asynchronous TRUE samples do not prove a current conjunction.
7. **Android actions:** neural output is a typed proposal only. Owner/permission/STOP/epoch/nonce/confirmation and native endpoint gate are external. A sent request is not a completed action.
8. **STOP/recovery:** new dispatch is serialized with STOP; already-dispatched physical effects may still complete. Crash ambiguity yields MAY_HAVE_EXECUTED/UNKNOWN and no silent retry. Stale receipts cannot update P.
9. **NCR-EVO:** isolated bounded DSL/QD experiment; G_const and authority remain immutable; no automatic promotion or core-runtime dependence.

## Conditional assumptions, not proofs

A_cap (trusted controller/verifier and OS permission semantics), A_ui (registered surface effect containment), A_tx/A_fs (atomic durable transaction and storage), A_gen/fresh nonce (rollback/replay boundary), native readback validity, measurable environment/progress, legal data and independent labels remain assumptions. The proofs are only as strong as these premises.

## Non-equivalences to preserve

- B2/LR2/H2 are different graph families.
- Fixed-z full-mask contraction is not whole-event contraction.
- Bounded state is not convergence.
- Native readback is not causal attribution.
- Memory embedding is not an authority record or lossless archive.
- File hash is not authenticity/freshness.
- STOP blocks new dispatch after its linearization point but cannot undo an effect already sent to the OS.
- A correct manual c0→c3 repair trace is not evidence of general self-regeneration or a successful NCR experiment.
- NCR-EVO is not the core neural recurrence and has no measured superiority.
