# WP-05 / product foundation: bounded text cycle integration — 2026-11-09

**Scope:** existing feature branch, release-first UNO 1.0. This is an integration step, NOT F, general planning, Android authority or full foundation acceptance.

`UnoTextCycle` owns the bounded transcript snapshot and creates a typed receipt through
local UI event -> bounded prompt with fixed system instructions -> local model callback ->
owner cancellation / one-way STOP check -> atomic app-private transcript persist ->
revision + digest. No native Android action can be called through this API.
Neural text is untrusted and cannot create `VERIFIED_COMPLETION`.

The existing `UnoChatActivity` now uses the same cycle for inference and explicit user clearing instead of directly writing the transcript in several UI paths.
The previous `UNO_CHAT_EXPERIMENT/1` AtomicFile remains readable and unchanged, preserving existing data; no destructive migration. The current stored chat is **plaintext**, bounded and **not** the required encrypted semantic/exact memory. Hash is only a local transcript integrity identifier, not an OS result. Revision only counts successes **within the Activity instance** and resets on process recreation.

STOP in this step is a *local text-cycle latch* on Activity destruction; manual stop of a single generation is request cancellation only, NOT global Android STOP. The already existing Android trust controller remains deny-all; unrelated modules and state are not made privileged. The model JNI still executes in application process, not isolated NeuralWorkerService.

**Acceptance:** host tests must demonstrate one successful cycle, invalid input without inference, model exception no write, cancellation no write, storage failure no commit, concurrent request denied, STOP cancels in-flight, owner clear with persist, digest length and unchanged Android effects. Android compilation/lint and real-device check remain separate.

**Unresolved for foundation:** protected durable exact/semantic memory & revocation, conversation/boot identity across restart, coherent process-wide STOP for inference and trust, isolated neural process, safe OS action admission and native readback, voice, sensor event fusion, UX/metrics, locked holdout, performance. Do not label FOUNDATION_COMPLETE from this step. Full F and new weights require separate authorization and evidence.
