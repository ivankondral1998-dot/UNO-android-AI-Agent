# UNO first-use encrypted memory genesis / 2026-11-10 R1

**Source defect:** The Android adapter generated an AndroidKeyStore key but did
not write any encrypted vault file until a first observation arrived. A
process crash between these steps could leave an existing key with no
snapshot; further opens properly fail closed instead of risking data loss,
but this made first-use startup fragile.

**Fix:** Core UnoEncryptedExactMemory gains an opt-in parameter
initializeEmptyOnFirstOpen (default false). Only the Android adapter enables
it when neither base nor backup ciphertext exists and no old key exists.
The constructor commits an authenticated AES-GCM empty genesis snapshot
via existing AtomicFile before exposing the store. Existing ciphertext
is reopened as is, and corrupt ciphertext is never replaced.
Any key-only state is still rejected.

**Host test:** explicit first-open genesis, exact revision 0 reopen with
no rewrite, empty read, injected persist failure and invalid old snapshot.
No Android permissions or model weights were changed. No old files removed.

**Still open:** crash between key generation and genesis commit; key-only
recovery needs an owner-gated policy, not silent reset. Cross-boot
expiry and anti-rollback are unresolved. AndroidKeyStore/device behavior
is NOT verified by JVM tests. Foundation incomplete.

**Status:** IMPLEMENTED candidate, CI verification pending,
DEVICE_UNTESTED.

## Exact verification

**Verified source:** `cf36fa1b4fef2dfbf50421456b09cac00ae42877`.
[CI #42725873442](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42725873442)
SUCCESS: 305 host assertions (47 encrypted exact-memory assertions),
Android debug APK build and lint PASS; APK SHA-256
`08815ee393d839553846b2fbfa0b9972b9ba3c16c0d99abbd6fffe035b4bb4fa`.

**Negative history/provenance:** preceding run
[#42725562176](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42725562176)
FAIL: opt-in Boolean was placed after `clockElapsedNanos`, breaking existing
Kotlin trailing-lambda calls. Code fixed by restoring the clock as the
last constructor parameter, preserving older call sites; the exact
retest above passed. This FAIL is retained, not renamed as PASS.

**Not verified:** on-device AndroidKeyStore genesis, interrupted first
commit, missing-key recovery, cross-reboot exact memory, anti-rollback,
and production unified neural intelligence. **FOUNDATION_INCOMPLETE**.
