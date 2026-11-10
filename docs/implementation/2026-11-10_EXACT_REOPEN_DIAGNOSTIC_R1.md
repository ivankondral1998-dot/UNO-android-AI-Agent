# UNO 1.0 — independent disk-backed exact observation re-open (R1, 2026-11-10)

## Scope

Feature branch `feat/uno-foundation-hardening-20261107`.
This implements an owner-invoked, isolated Android diagnostic for **WP-05-T05**
(same-boot process-restart recovery); it is not completion of WP-05, original
unified neural operator F, new own weights, planning, Android effect readback
or commercial release. Baseline was checked at commit `9bf75b0e01d34d0b5f5540ba679b3b3845cee385`.
No old file, model, branch, data or owner decision is deleted.

## Actual defect

The owner-confirmed observation was immediately read back from the same
in-process singleton `UnoAndroidMemoryOwner`. Such a check proves that
current process state can be read; it cannot alone show that a newly opened
reader will decrypt the committed ciphertext from the filesystem.

## Implementation

- Consent remains mandatory for recording a new device snapshot.
- After successful encrypted write and immediate readback, the app commits a
  non-sensitive *locator* (`event_key`, immutable diagnostic SHA-256) into
  app-private SharedPreferences. Locator is not a permission, a trusted
  receipt, or a source of facts. Failure to commit is explicitly reported
  while the already committed memory write is **not** claimed rolled back.
- A separate button reads the locator and opens `UnoAndroidExactMemory`
  **afresh** with `readOnly=true`; it never reuses cached in-memory vault
  state. The no-create reader cannot generate a keystore key, initialize
  genesis, write a record or revoke any scope.
- A strict read-only open reads the base file using `FileInputStream`;
  unlike `AtomicFile.openRead()` it cannot mutate the vault to resolve a
  legacy backup. If a backup requires recovery, it refuses and reports
  unavailable, not a fabricated `COMPLETE`.
- The recovered exact payload must be `COMPLETE` for scope
  `device-observation`, epoch 0, same boot and non-expired time. It must
  retain the expected entry source/type/schema and its stored raw SHA.
  The payload's recorded source SHA must equal both the locator and the
  SHA-256 of the independent immutable diagnostic file. **Only then**
  `SAME_BOOT_EXACT_AND_SOURCE_MATCH` is reported.
- Missing locator, bad digest/key, missing/corrupt vault, scope revocation,
  TTL expiry, old-boot identity and missing source file return distinct
  non-PASS outcomes. A local diagnostic JSON is saved, but the reader
  does NOT mutate exact memory.
- Negative Python static regressions forbid removing the button, using the
  cached writer instead of fresh disk open, using the mutable latest probe
  as provenance, dropping durable pointer, or silently creating a vault.

## Manual device-gate (not executed by CI)

On one private debug installation on Samsung A52 / Android 14:
1. Tap explicit owner consent and record an observation.
2. Tap the readback button immediately: expect
   `SAME_BOOT_EXACT_AND_SOURCE_MATCH`.
3. Force-stop the **same installed package** without clearing app data, open
   it and repeat within 10 minutes. Require the same result.
4. Reboot Android and repeat: `EXACT_UNKNOWN` is the currently designed
   conservative answer. **Do not report cross-boot memory verified**.
5. With a valid same-boot sample, revoke the scope from the explicit UI,
   then read again: expect `EXACT_DENIED`; this is not physical flash
   erasure. For negative failures do not reset data or silently regenerate
   keys.

## Residual gates

AndroidKeyStore / `AtomicFile` under powercut and interrupted bootstrap
remain device-untested; key-only recovery needs an owner policy, not reset.
Authenticated AES-GCM ciphertext can still be rolled back to an older valid
snapshot by a sufficiently powerful local attacker; no anti-rollback anchor.
Cross-reboot semantic validity needs explicit owner-approved temporal
contract, not a wall-clock guess. Observation memory is still limited
to 256 entries with no garbage collection; a completed old boot record
returns UNKNOWN. No real unified neural intelligence, native Android
operations or independent OS effect readback is asserted.

## Build evidence

**CI VERIFIED:** source `a095ae796b236db71fd0fc2d534f86a0d4107daf`; private [run #42729419491](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42729419491) SUCCESS. 305 core host checks (47 encrypted memory), static negative regressions, Android SDK35 build, lint, APK/badging/manifest gates PASS. APK SHA-256 `f50b26425f310b493adb4c8bd6e1a8202650bd42e5bc8f35eeb7de3cc1824f57`. **DEVICE_UNTESTED**.

Status: IMPLEMENTED / HOST_TESTED / ANDROID_BUILT; **not** DEVICE_VERIFIED.
