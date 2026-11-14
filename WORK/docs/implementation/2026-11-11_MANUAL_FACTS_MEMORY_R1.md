# UNO 1.0 — explicit manual facts into the existing exact-memory vault (2026-11-11)

Source feature branch: `feat/uno-foundation-hardening-20261107`, base `031b01f29966258a9291e0bc0595dfaf33d89ae0`. Root `AGENTS.md` V3 remains authority. Original code and research history are preserved.

## Implemented
- A new `UnoFactsActivity` opened from the existing local-chat activity, without new launcher icon, Android permissions, network access, neural weights, or OS actions.
- A person manually enters a key and value, confirms encryption-backed storage, and retrieves the **exact bytes** by key. Duplicate conflicting values are displayed as conflicting; they are not silently resolved or summarized.
- The existing `UnoAndroidMemoryOwner` / `UnoAndroidExactMemory` / `UnoEncryptedExactMemory` AES-GCM vault is reused. Key generation/AtomicFile failure is not silently repaired by overwriting existing data.
- `UnoManualFacts` allows cross-reboot retrieval **only** for explicitly timeless `USER_DECLARATION` entries in `manual-note:<revision>` scopes with the exact `OWNER_TYPED_LOCAL` source label and `Long.MAX_VALUE` expiry. Observation timestamps and action outcomes do **not** inherit the exception; their boot mismatch still produces UNKNOWN. The provenance source string is NOT authentication.
- A separate, explicit, confirmed **forget all** revokes just the active manual-fact scope atomically in the vault, then moves the non-authoritative scope locator to a new generation. Crash between operations is detected on the next user action. This is logical revocation, **not** verified flash secure erase.
- STOP refuses new manual writes; an already started disk operation may still finish. User-facing errors do not claim rollback or no-effect.

## Tests and limits
- New `UnoManualFactsTest.kt` covers AES-GCM restarts, same/new boot, conflicts, wrong source, revocation, persistence failure, tampering and defensive copies; wired into `AllHostTests.kt`.
- The facade compiled under Kotlin JVM 1.9 with compatible interface stubs and eight local fake-port checks passed. SHA of GitHub core/test/UI blobs was matched against local byte-exact files.
- **Actual encrypted-vault integration tests and Android APK build have NOT been run for this commit.** `HOST_TESTED` applies only to the small facade/stub checks; `ANDROID_BUILT=FALSE` for this revision; `DEVICE_VERIFIED=FALSE`, `RELEASE_READY=FALSE`.
- This is not product semantic memory, owner identity authentication, neural context integration, autonomous planning, Android permissions/dispatch, or a claim that the full organism works.
- Manual records remain bounded by the existing vault capacity (256 rows) and 16 returned versions per key; overflow/concurrent effects fail closed. Permanent deletion and rollback resistance require further Android evaluation.
