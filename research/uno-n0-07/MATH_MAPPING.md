# Traceability — Grok corrected paper / UNO math -> N0-07 code

This is a deliberately *tiny* executable analogy of the user's mathematical contract, **not a conformant subset of the official R5.3 ABI**. The Grok document is a paper candidate, not a delivered working weight checkpoint. Original R5.3 normative source package is unchanged.

| Source contract | Source / equation | Tiny implementation | Status / missing assumptions |
|---|---|---|---|
| One intelligent organism | Grok paper §1; owner minimum-organism §3 | `TinyOrganism` owns one `state`, one θ and shared `predict` for sensor and intention | `IMPLEMENTED_RESEARCH`, no separate reasoning agents |
| Event encoder | Minimum-organism §4 `z0=tanh(E_mod f + U_s s + ...)` | `features(Context)` and `encoder`, `us`, bounded tanh | `PARTIAL`: sensor features only; no text/audio/goal; semantic summary is lossy |
| Memory | Grok §2 IR02; minimum-organism §6 | 96-entry exact typed ledger, lossy recent mean, explicit `COMPLETE/TRUNCATED/UNKNOWN` | `PARTIAL`: no consent/TTL/concurrent exact retrieval/cryptographic owner auth |
| Shared recurrent F | Minimum-organism §4; formal S5 equation | `J=2`, d16, b4, χ2, K2, tanh A,C,B and convex state update, backprop through executed passes | `HOST_TESTED`: not full B2 or official runtime ABI |
| Conditional compute | Grok §2 IR01; minimum-organism §4 mask semantics | deterministic 2-of-4 cyclic prefix per recurrent step, skip inactive kernels; `executedBlocks=4`, `skippedBlocks=4` | `HOST_TESTED`; *not* stochastic mask distribution or dynamic halting; no global Lipschitz claim |
| New learning | Minimum-organism §6 full L3a and supervisory formula | Sensor supervised cross-entropy, event-local BPTT through F, owner intent classification head | `EXPERIMENTAL_ALTERNATIVE`: no L3a dual/coverage, no licensed datasets; Θ-edit differs from frozen production S1 |
| Fast P | Minimum-organism §6 P1, η=.01 λ=.001 ε=1, unit-ball projection | `learnMockVerifiedOutcome` P with Wp=0 and synthetic binary y | `HOST_MOCK_ONLY`; no trusted native R, authentic tickets, or OS effect. Never use as production authority |
| Owner corrections | Owner 2026-11-05 learning requirement | `teachOwnerIntent` only updates owner-intent head, typed memory event; cannot rewrite sensor fact | `HOST_TESTED_CONTRACT`, Android UI not phone-tested; no general language understanding |
| Android authority / STOP | Grok §4; R5.3 trust/readback | `stopEpoch`, stop latch and receipt validity in mock; Android UI no external actions | `MOCK_ONLY`: no real owner enrollment, consent, native readback, dispatch, no independent causal effect |
| Resource limits | Grok §5; minimum-organism §5 | d16 2,917 Θ scalars; no background service, mask counts measured in host tests | `HOST_ESTIMATE_ONLY`; actual A52 latency, peak PSS, energy, thermals REQUIRES_DATA |
| Structural graph growth | Grok §1 'physical rewiring lab, not approved runtime' | topology static with changing numeric Θ and stored experience; NOT N0-05's 11 created conjunction neurons | **INTENTIONALLY OMITTED**: research version focuses on F/P; topology mutation remains separate lab alternative |

Do not compare this product scope to a classifier-only baseline and claim full UNO success or failure. N0-07's actual current predictive score is **worse** than both historical graph and simple baselines on this one artificial sequence, and requires a new independent protocol before any claim of advantage.
