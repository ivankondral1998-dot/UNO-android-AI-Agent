# WP-05 hardening: local transcript protection + same-process STOP — 2026-11-09

## Preserved state and authority
Feature branch only, no history deletion. Existing `uno_chat_experiment_v1.json` remains untouched as fallback for *first* v2 load (and a recoverable rollback original); it may still contain plaintext until separately reviewed deletion. This implementation therefore does **not** guarantee removal of older plaintext from device storage. New commits use `uno_chat_experiment_v2.aes`, AES-256-GCM randomized nonce and AAD, AndroidKeyStore device-bound key; failures to open/decrypt an existing v2 are fail-closed, with no fallback to stale v1. `AtomicFile` is the file transaction primitive. Owner can explicitly empty current chat via existing confirmation; this does not delete the original v1 copy or other project files.

`UnoProcessStop` is one-way `AtomicBoolean` scoped to the *current app process*. Root laboratory STOP sets it; chat now also exposes owner-tapped process STOP. It rejects future text sends/model imports/load and transcript-clearing writes; neural generation checks latch at token callback. It is not persistent, not cross-process, not Android native permission and does not cancel already-completed OS effects. Old `DenyAllAndroidPort` remains.

## Tests/gates
- Core host tests: AES envelope round-trip, tampering, wrong key, truncation, size, nonce diversity; process STOP one-way.
- Android Gradle build/lint required to verify integration and API26 compatibility.
- DEVICE_VERIFIED not claimed until new exact APK installed and behavior observed.
- Still missing protected exact/semantic long-term memory, append-only WAL, full unified organism state, isolated neural process and trust-safe dispatch/readback, speech/plan, owner secure rearm. **FOUNDATION_INCOMPLETE**. No operator F, no weight training, no commercial release.
