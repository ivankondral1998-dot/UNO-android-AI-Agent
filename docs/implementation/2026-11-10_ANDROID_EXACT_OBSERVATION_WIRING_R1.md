# Original UNO foundation — Android observation to encrypted exact memory (2026-11-10)

## Scope and actual function
Continuation of original WP-05 (exact memory) and original WP-06-T01 (neutral end-to-end reference), NOT more work on Qwen text chat.

- UnoAndroidMemoryOwner holds one process-wide UnoAndroidExactMemory instance and a lifetime-long OS file lock. A second Android process cannot open a writer while that lock is held. Lock failure is fail-closed. No existing files, weights, histories or research artifacts are deleted.
- UnoFoundationReferenceCycle now allocates event:<persistent generation+1> inside the same mutex as the memory commit. A new Activity or a concurrent second cycle cannot reuse the earlier local event:1 identifier. Its returned observedEventKey identifies the exact committed observation, instead of relying on a potentially advanced global generation.
- An existing owner-initiated Android diagnostic ("Снимок состояния: RAM / CPU / батарея / тепло") now captures real metrics and feeds a bounded selected-fields observation into the same reference path. These are actual reported battery percent, thermal status, available memory, SDK, and SHA-256 of the full diagnostic report. The complete previous diagnostic JSON continues in its original location. Only selected fields are encrypted and committed to exact memory.
- After commit the app retrieves the exact event by its returned key and checks byte identity. The UI report distinguishes local persistence from neural status MODEL_UNAVAILABLE and never records a verified Android effect or fake training signal.
- Android action trust remains DENY_ALL; injected Owner UI rejects all action proposals; NoWeightsNeuralPort remains explicit about the absent accepted neural brain. Lifecycle pause and explicit process STOP prevent beginning new observation work. Already committed app-private writes cannot be rolled back. No new permissions.

## Limits and acceptance
- No semantic approximate search, owner deletion UI, anti-rollback anchor, secure flash erasure, action/memory atomic cross-resource transaction, real Android operations, or device-proven crash/powercut recovery.
- Actual AndroidKeyStore, boot token, single-writer admission, exact same-boot process restart still need physical device testing.
- Kotlin/JVM suite includes encryption/recovery/consent scopes, wrong key/tamper, failed-write behavior, rejection of VERIFIED_COMPLETION and concurrent distinct persistent event keys. Android build/lint must be checked separately.
- FOUNDATION_INCOMPLETE; no F, new weights, runtime plasticity, training, or release.
- Earlier experimental WP-05 text-cycle and WP-06 no-copy GGUF patch files remain as historical changes, not original roadmap stages.