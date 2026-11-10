# UNO 1.0 implementation audit — November 10 2026 / corrective patch R1

## Exact scope and verification status
Independent source-level re-evaluation of recent feature-branch changes made in
November 9–10: experimental Qwen text chat, chat encryption, foundation reference
cycle, exact-memory vault, Android adapter/single-writer lock, UI diagnostic flow.
NOT an exhaustive audit of every historical R5.3/LAB dataset or a Samsung device trial.
Actual code from GitHub was read and corrected; CI result is recorded separately.
Status: IMPLEMENTED / HOST_TESTED / ANDROID_BUILT, not DEVICE_VERIFIED.

## Found defects and corrective disposition

1. HIGH — **Unannounced durable memory write**: the previously passive
   "Снимок состояния" button called observeDeviceSnapshot, which wrote
   selected device data into the new vault. **FIXED**: passive diagnostic
   performs no vault operations. Separate explicitly titled button shows an
   Android app confirmation dialog before each persistent observation.
   The confirmation is UI consent for memory recording, NOT authenticated
   owner credentials or permission for OS actions.
2. HIGH — **Diagnostic coupled to fragile memory setup**: Keystore, boot
   identity or vault failure could prevent an ordinary metrics snapshot
   from completing. **FIXED for passive path**: passive snapshot works
   independently of the exact-memory vault. A failed optional memory
   action is reported separately; no automatic retries.
3. HIGH — **Incorrect provenance SHA / overwritable source**: earlier
   observation digested json.toString() while DeviceProbe.persist() wrote
   json.toString(2). Consequently file bytes did NOT match digest.
   Further diagnostics overwrote probe_latest.json, invalidating evidence.
   **FIXED for new owner-confirmed observations**: digest now uses the
   exact pretty-printed bytes, stored first in a distinct content-addressed
   immutable diagnostic file (observation-<sha256>.json), before
   encrypted memory commit; no later disk write is needed to claim it.
   Existing probe_latest behavior for passive diagnostics is preserved.
   Disk fsync/rename is NOT power-cut attestation.
4. MEDIUM — **Misleading chat deletion language**: a "new chat" clears
   only current encrypted transcript, NOT the old plaintext v1 copy.
   **FIXED IN UI DISCLOSURE**, not deleted or silently migrated.
5. MEDIUM — **Memory revocation had no owner-facing control**:
   added an explicit second confirmation. It revokes the scoped current
   vault and blocks future writes into this scope, without touching
   existing JSON diagnostic files, old snapshots, or raw flash blocks.
   No data is revoked or deleted automatically by this code update.
6. MEDIUM — **Negative regressions missing**: static checker and tests
   now reject accidental memory writes from passive read-only diagnostics,
   removed consent/revoke UI, inconsistent hash formatting and replacing
   immutable evidence with a mutable latest file.

## Open fail-closed blockers (do not mark PASS)
- HIGH: the vault stores boot-scoped monotonic expiry, so records from
  a previous reboot return UNKNOWN. This is NOT completed cross-reboot
  long-term memory. Need a reviewed causal/wall-time restoration contract.
- HIGH: if AndroidKeyStore contains a key but the snapshot is missing,
  current adapter intentionally fails closed. A crash during initial key
  enrollment before the first committed snapshot can create this state.
  **No automatic key deletion or reset** is permitted. Needs owner-approved
  recovery policy and physical fault injection on Android.
- HIGH: AES-GCM authenticates a snapshot but does NOT protect against
  replay of an older valid ciphertext, which can undo a revocation.
  Revocation is not secure erasure. Separate anti-rollback design and
  device proof remain required.
- HIGH: OS file lock / KeyStore / Android boot UUID / AtomicFile recovery
  need real Samsung A52 verification. Host-only tests do not prove these.
- HIGH: original UNO 1.0's intelligent unified planning/action loop is
  NOT operational. Android lab uses NoWeightsNeuralPort and deny-all OS
  action bridge. Qwen text chat is a separate experimental path, NOT F.
  No production model, owner-bound Android action catalogue or native
  independent OS readback has been authorized/accepted.
- MEDIUM: a revoked device-observation scope intentionally cannot be
  reused; memory capacity is bounded and old expired ciphertext is not
  garbage-collected. No owner-controlled re-enrolment contract.
- MEDIUM: selected metrics are plain app diagnostics before consented
  memory commit; no direct OS security attestation is asserted. A UI
  confirmation alone is NOT verified Android owner identity.

## Work process correction
Read AGENTS.md + actual branch HEAD + original roadmap before edits.
Treat a passing compiler as ANDROID_BUILT, never DEVICE_VERIFIED; isolate
experimental chat patches from original WP-03/F, WP-05 memory and WP-06
agent gates. One necessary private feature-branch CI run checks this
corrective patch; do not issue another APK to owner absent a meaningful
physical test. Do not change main, delete prior files, retrain weights,
publish release, or spend Work/Codex resources unnecessarily.


## Exact verification and provenance

**CI VERIFIED:** [exact-source run #42715526164](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42715526164), commit `d9a0791ffe80fb3e3d32b1cd449282d8ac1ff230`: SUCCESS. Static-negative UI/permission checks, 299 core host checks (41 encrypted-exact-memory checks), Android arm64 debug build, Android Lint, APK package and manifest checks PASS. APK SHA-256 `f205056752516d07315d91fec0d994a87cd8234463233c7db8c01d04d0fbf6bf`. **No Samsung device verification or accepted neural F/model/authority**; only the source was built.

New consent/revoke flows and immutable evidence paths have not yet been
physically exercised on Samsung A52. A successful Gradle build does not
establish screen behavior, KeyStore persistence, readback across reboot,
or flash-level resistance to rollback. The only licensed candidate model
seen in UNO is a separate Qwen text experiment; this audit does not certify
any production neural intelligence.


## Follow-up: initial key/snapshot mismatch (R1)

An optional empty encrypted genesis is now persisted on first new key use,
before returning a memory instance. The existing key without ciphertext
continues to fail closed and requires explicit recovery policy; old
snapshots are preserved. See
[genesis implementation note](2026-11-10_EXACT_MEMORY_GENESIS_R1.md).
