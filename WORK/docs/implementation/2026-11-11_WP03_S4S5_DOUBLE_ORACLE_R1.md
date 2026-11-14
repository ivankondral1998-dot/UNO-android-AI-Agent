# WP-03 S4/S5 — double-precision CPU oracle R1 (2026-11-11)

**Scope:** Reference implementation and deterministic host checks only. This is NOT the trained/shared Android neural operator, not a weight-file ABI, and not a replacement for GGUF chat.

**Parent:** Grok permanent-package checkpoint `3710f4e14ffd0fa2ffe5a58ec024349a13b0d3ec` (no main merge, no key modifications). **Branch:** `feat/uno-wp03-s4s5-cpu-reference-20261111`.

## Implemented
- `android/core/src/main/kotlin/org/unovyra/uno/core/UnoFReference.kt`
- `android/core/src/test/kotlin/org/unovyra/uno/core/UnoFReferenceTest.kt`
- `AllHostTests.kt` includes the new suite.
- Literal S4: current modality projection, state/goal/meta and modality/bias; current-input memory query `q=tanh(Wq z0)`; stable softmax over semantic key/value entries; `z=tanh(z0+Wr r)` (including empty memory); `h0=rho*s+(1-rho)*z`.
- Literal S5 with synchronous `h^k` update: two shared branches, block width 64, expansion 4, `K=1..8`, direct skipping of inactive A/C/B block kernels; C z cached once per active block and branch. Trace reports executed matrix calls.
- Shapes, finite checks, row L1 caps for recurrence and input transforms, deterministic cyclic-prefix **geometry**.
- No model weight loading, no policy sampling, no Android permission or OS dispatch. `UnoRefMemoryVector` is semantic-only, not exact data.

## Evidence
- Locally compiled **only the two new Kotlin files**: Kotlin/JVM 1.9.0, OpenJDK 21.
- Executed `org.unovyra.uno.core.UnoFReferenceTestKt` → `UNO_F_REFERENCE_HOST_PASS=10` (10/10): zero state, second tanh, inactive block preserved, branch averaging, current-input retrieval, stable softmax, cyclic rotation, invalid inputs, forbidden A norm, deterministic replay.
- Source and test file Git blob hashes matched locally tested bytes (source `0473c72a962775880fd7972ac3063cd2df7ec1c6`, test `c87619d82c573b68a6a8a51f616480d0874b5f88`).
- Full repository host tests, Gradle/Android compilation, on-device benchmarking, and real weights: **NOT RUN** for this branch. Grok's earlier build pertains to parent `e90b5211`, not this change.

## Remaining gates
1. WP-03-T01: validate canonical TEXT/SENSOR/OS envelopes, provenance, bounded persistent state and temporal rules.
2. WP-03-T02: independent randomized tensor oracle, versioned weight load, larger dimension, FP32 parity and state snapshots. Here `d=128` is a **synthetic test dimension**, not a selected deployable B2 config.
3. WP-03-T03: S6 learned selector/hazard, bounded resource admission and complete MAC/buffer accounting; current prefix helper is geometry only.
4. WP-03-T04/T05: formal model manifest, quantized tensor validation, CPU↔Android parity and A52 resource measurements.
5. WP-04 and WP-06: approved/licensed fixed weights and integration with one organism. The existing `NoWeightsNeuralPort` must continue to fail closed until then.
6. Signing backup alert: private `UNO-owner-signing-backup` currently stores both PKCS12 and its password as separate git blobs; this is **not independent secret protection**. Do not read or redistribute those secrets. Address explicitly before declaring a permanent secure update channel; keep signing changes out of this mathematical feature branch.

**Status:** `IMPLEMENTED`, `HOST_TESTED` (isolated). Not `ANDROID_BUILT`, `DEVICE_VERIFIED`, `RELEASE_READY`. No owner decisions on architecture/weights/runtime are inferred.
