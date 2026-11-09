# Original WP-05-T01/T02 candidate — encrypted exact memory, 2026-11-10

## Scope: actual roadmap, not the experimental Qwen/chat patch names

A new `UnoExactMemoryPort` links the existing in-memory oracle and the neutral end-to-end
`UnoFoundationReferenceCycle` to a durable implementation without replacing a single
`NeuralPort` with an orchestrator or another brain.

New core `UnoEncryptedExactMemory` stores typed exact raw observations with a versioned
authenticated snapshot: scope, fact key, origin/source, explicit kind, raw byte SHA256,
consent epoch, monotonic expiration, boot identity, generation/unique ID and owner-scope
revocation tombstone. Full snapshot AES-256-GCM integrity (schema-bound AAD; fresh nonce
per write); failed persistence never advances visible in-memory generation. A semantic
summary is excluded from RetrieveExact and model-written VERIFIED_COMPLETION is always
rejected; memory text is never authorization.

The Android-only adapter `UnoAndroidExactMemory` uses a separate AndroidKeyStore
AES key and `AtomicFile` in the app-private directory. It gets Linux boot UUID, or
Android `boot_count` if the kernel UUID is inaccessible, and fails closed if neither
is available. Exact records from another boot return UNKNOWN, not a false COMPLETE
using elapsed clock. Local clock is a floor even if a caller supplies an earlier time.
After reopening, stored exact bytes remain available only in the same boot and epoch.

**No deletion of legacy files or migration.** The encrypted vault is distinct from the
experimental chat transcript, the SQLite readback-claim store and `ActionIntentJournal`.
A scope revoke removes its live records from the next authenticated snapshot and persists
a tombstone, but does not guarantee secure deletion of old physical flash blocks,
copies, old atomic backups or external screenshots.

## Tests, statuses and unclosed gates

- A standalone Kotlin/JVM pass tested encryption/round trip, exact byte copies, distinct
  scopes, conflicts/truncation, same-boot recovery, stale-boot UNKNOWN, consent epoch,
  semantic/non-fact separation, failure atomicity, owner revoke, non-reused IDs, wrong
  key, truncated/tampered GCM ciphertext. Integration with the neutral foundation reference
  confirms observed bytes persist even when the model fails; no verified OS outcome.
- GitHub Actions must still pass exact-source host suite, Android APK compilation and lint.
- No Android device trial of this vault yet: AndroidKeyStore compatibility, boot identity
  support, same-boot restart, flash-pressure behavior and crash-persistence gates remain
  **DEVICE_UNTESTED**.
- App has a compilable adapter but product screens do not yet consume it. The original
  WP-05 memory stage is only PARTIAL, not complete. No semantic approximate retrieval,
  controlled retention/compaction, durable verified action receipt, cross-process transaction
  or user-facing memory management yet.
- All records can be rolled back by replacing a valid authenticated ciphertext with
  an older valid ciphertext. AES-GCM detects tampering, not rollback. A durable anti-rollback
  monotonic anchor is future work. Likewise no independent owner authentication or trusted
  Android dispatcher has been introduced by this port; `DenyAllAndroidPort` stays active.
- Bounded engineering limits are 256 exact rows, 4096 bytes/row, 1.5 MB serialized
  snapshot. These are initial bounded-store limits, **not** a choice of model weights or F.

**Status:** IMPLEMENTED candidate / HOST_TESTED locally in Kotlin / Android verification
pending until CI result. `FOUNDATION_INCOMPLETE`; no training or release authorization.
