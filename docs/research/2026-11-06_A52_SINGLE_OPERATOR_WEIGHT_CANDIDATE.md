# UNO A52 weight candidate — 2026-11-06

Owner requested actual new weight architecture and minimum A52 resource cost without sacrificing task competence. **Do not implement three always-on operators.** HSR's U(Vx)+Sx would compute both branches and pay sparse-index/cache overhead; its synthetic approximation test does not establish energy benefit.

Current prototype: single factorized shared operator F_r(x)=U(Vx), n=256, r=32, two matrices U[256,32] and V[32,256]. Only 16,384 int8 coefficient bytes versus 65,536 for an int8 dense 256x256 matrix; scales and float accumulators extra. 16,384 MAC per call vs 65,536 dense; hardware speed/energy not yet verified. This is one operator, NOT a complete model, and does not replace R5.3 without matched quality evidence.

Structural plasticity: **not run per inference**. Proposed occasional gated updates to graph/rank after verified outcomes; this is not yet implemented or tested. Selective block masks must prevent expensive kernels from executing, not zero results after computation. A52 available memory and background thermal budget demand real device measurements.

Local artifact: UNO_A52_FR32_INITIALIZED_UNTRAINED_20261106.zip contains reproducible Python builder, two 8,192-byte int8 factor tensors and manifest. Seed 20261106. Host test relative quantization error against unquantized factorized operator: 0.01215818 for a single random input. This is an INITIALIZED, UNTRAINED numeric prototype, NOT a learned intelligent model, language weights, an APK or device-verified result.

Historical Grok/DeepSeek: stress one shared trainable loop vs multi-module baseline at matched resources; masks/STOP/memory formal correctness do not establish intelligence or energy savings. Grok also identified adaptive-mask global-contraction gap and semantic-memory noninjectivity. Do not extrapolate earlier C256R32 isolated latency to whole organism.

Decision: **FR32 is a resource-oriented implementation candidate, not a final winner.** Before choosing weights for the actual product, demonstrate full-task accuracy and forgetting on equal licensed data against B2, LR2, H2, N0, HSR and tabular baseline; then A52 joules/verified-successful-task, latency p95/p99, RAM and thermals. No training permission has been inferred.
