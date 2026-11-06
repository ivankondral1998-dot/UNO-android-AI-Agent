# UNO weight-family comparison — 2026-11-06 (evidence-bound)

Scope: B2, LR2, H2, factorized C256R32, dense C256, structural UNO-N0. This is a candidate comparison, NOT a measured head-to-head benchmark.

| Candidate | Storage/compute principle | Learning mechanism | Strength | Critical gap |
|---|---|---|---|---|
| B2 | Dense numeric shared recurrent F; adaptive masked blocks | Gradient-based learned parameters plus bounded plastic state | Explicit R5.3 equations, tensor ABI and counts | Untrained; A52 latency, quality and energy unknown |
| LR2 | Reduced-rank numeric alternative | Gradient-based | Candidate for smaller matrices | No matched quality or A52 results |
| H2 | Expanded attention variant | Gradient-based | Candidate for context-sensitive tasks | Extra compute, no matched quality data |
| C256 | Dense 256-width numeric baseline | Numeric parameter optimization | Simple reference | Does not establish full UNO capability |
| C256R32 | Factorized numeric matrices (rank 32) | Train factors; may support plastic updates | Lower matrix arithmetic/storage for selected layers | Low-rank bottleneck; cannot infer full-system quality |
| UNO-N0 | Structural composite-neuron graph, without per-synapse numeric coefficients | Add/modify connections based on experience; current growth rule developer-specified | Potentially cheap local incremental adaptation | Graph growth, search complexity, language/audio/vision scaling not proven |

Historical reported C256R32=1.589 ms/event vs C256=4.042 ms/event (~2.54x) is NOT independently re-run here; workload, hardware and parity of tasks require source/trace confirmation. It must not be generalized to B2 or N0.

UNO-N0-03 was reportedly built as an Android research APK. The 30/32 -> 32/32 improvement was an EXPECTATION in recovered context, NOT confirmed phone measurement. Virtual simulator results are not Android native action evidence.

No winner established. Inference: factorization may reduce numeric compute; structural learning may reduce gradient-update cost; neither guarantees better task quality or bounded long-term memory. Combining them inside one F is a research candidate, not an approved architecture change.

## Fair comparison to implement (not yet executed)
- Same licensed train/dev/locked-test tasks: RU text, audio, visual, sensor, action planning, continual adaptation, forgetting and robustness.
- Same device A52 / Android 14, runtime and input distributions; report p50/p95/p99 latency, peak PSS, energy joules/task, idle drain, thermal, graph size, training time, accuracy and forgetting.
- Separate full end-to-end quality from isolated microbenchmarks. Compare fixed numeric, factorized numeric, structural, and tabular baselines; account for model capacity and total train budget.
- No training until separate explicit authorization; implementation and benchmark harness are authorized.
- Decision rule: reject candidates that fail safety/quality floor, then compare measured energy and latency. Do not select on parameter count alone.

Evidence status: B2 mathematical layout SPECIFIED_UNTESTED; factorized performance historical claim REQUIRES_DATA; UNO-N0 structural growth research SPECIFIED_UNTESTED for full UNO; cross-family winner REQUIRES_DATA.
