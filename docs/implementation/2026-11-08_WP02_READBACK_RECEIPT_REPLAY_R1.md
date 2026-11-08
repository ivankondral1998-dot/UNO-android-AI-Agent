# UNO WP-02 — readback causality and append-only receipt replay, R1

**Date:** 2026-11-08. **Scope:** feature branch `feat/uno-foundation-hardening-20261107`. **Normative owner rules:** repository root `/AGENTS.md`; this is an implementation/evidence record, not an owner decision or substitute for the research sources.

**Status:** `IMPLEMENTED + HOST_TESTED` for the **reference JVM controller and fake native port only**. `FOUNDATION_INCOMPLETE`, `ANDROID_BUILT=FALSE` for these commits, `DEVICE_VERIFIED=FALSE`. Nothing is connected to Android permissions or privileged effects. UNO's neural F, model, weights, memory/learning algorithm, Neural-Language and external projects were not modified.

## 1. Mathematical and safety obligations

Primary sources, **not superseded** by this document:

- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` §§1,6–7 — causal time, `T=(ν,e,stop,owner,cap,L,D)`, STOP/REVOKE priority, dispatch linearization, separate native evidence and endpoint time, `CURRENT_ALL` vs `OBSERVED_ALL`.
- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` §§1,4–5 — `M` is not `L`, `L` not `P`; `used + receipt + memory references` must be atomic for trusted completion; recovery after crash cannot reconstruct unobserved OS causality.
- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` §§1–2 — `A_cap/A_tx/A_fs`, exact owner consent, native permission check, trust boundary, independent readback, STOP before dispatch.
- `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md` T6/T7 — partial proof is conditional; event receipt ≠ causal attribution/exactly-once physical OS effect.
- `docs/precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md`, `03_CONSOLIDATED_SUBSYSTEM_CONTRACTS.md` — fixed common mask conditional bound, non-injective semantic memory, resource and trust requirements. None of the obsolete unconditional convergence/device claims are revived.
- `docs/implementation/2026-11-08_WP02_CAUSAL_MATH_BRIDGE_R1.md` and `2026-11-08_WP02_TYPED_DISPATCH_OUTCOME_R1.md` — earlier reference journal binding and typed dispatch results, intentionally retained.

**Local temporal invariant (CONDITIONAL):** let `t_d` be the monotonic `now` passed at reference native-admission, `t_o` be the readback's claimed native observation timestamp, and `t_v` the verifier's `now`. The controller now **rejects** positive readback unless `0 ≤ t_d ≤ t_o ≤ t_v < ticket.deadline`, together with ticket ID, trusted source-tag equality, positive native generation and current ticket/epoch/nonce checks. This excludes the specific counterexample `dispatch(t_d=5), stale TRUE sampled at t_o=4, verify(t_v=8)`. It **does not prove** valid OS readback when an untrusted caller can supply `now`, falsify native timestamps, reuse boot-local clocks, or forge `trustedSourceTag`. Native monotonic clock and boot/session-binding remain **SPECIFIED_UNTESTED**.

## 2. Implemented flow

`ActionIntentJournal.kt` retains the existing v1 append-only record framing and SHA-256 hash chain, and adds a third **host-reference** record `RECEIPT_RECORDED`:

```
J:PREPARED
    → J:MAY_HAVE_EXECUTED  [fsync before fake-native callback]
    → NativePort.dispatch  [NOT evidence of success]
    → NativePort.readback  [independently checked only within fake reference port]
    → reference ledger.commit(TRUE)
    → J:RECEIPT_RECORDED   [source-tag, nativeGeneration, observedAtNanos, ticket/digest]
    → Ticket COMMITTED      [only if journal sync also succeeded]
```

The receipt record is written and synchronized **in the same file/chain as PREPARED and MAY_HAVE_EXECUTED**. Older v1 files containing only phases 1 and 2 still replay. All receipt payloads are length/version/sequence/transition validated on replay; corrupted hashes or truncated tails fail closed without truncation or retry. Duplicate receipt, re-arm after replay, receipt before arm and unsupported status are rejected.

`TrustController.kt` now tracks `nativeAdmittedAtNanos` internally for each issued ticket. A stale readback timestamp is rejected before a false success/commit. When `ledger.commit` succeeds but receipt journal append/sync fails (e.g., journal STOP/disk failure), this invocation **does not return COMMITTED**: the ticket becomes `MAY_HAVE_EXECUTED` and is not redispatched. Conversely, when a positive receipt is durably added, the **host** returns COMMITTED.

**Critical non-atomicity:** reference `DurableLedger` and `ActionIntentJournal` are still **two stores**. There is no single `A_tx` domain for `used + receipt + P-version + M-ref`. On a crash between those two commits they can disagree. This iteration deliberately chooses **conservative unresolved** rather than claiming exactly-once completion or reissuing a possibly executed OS action. `RECEIPT_RECORDED` is a persistently stored **claim** from the reference callback, *not a verified Android-native fact*. The journal has no secret MAC/encryption, trusted native identity, Keystore, secure rollback protection, or tested sudden-power-loss guarantee.

`ActionIntentJournal.recordReadbackClaim` is `internal` to the Kotlin module, not an Android security boundary. It cannot defend against malicious code within that module or corrupted/compromised trusted OS. Presence of a stored claim **must never** automatically authorize another action or upgrade semantic memory to verified current state.

## 3. Exact files and independent local host checks

Changed:
- `android/core/src/main/kotlin/org/unovyra/uno/core/ActionIntentJournal.kt` — Git blob `2b1d4867d09957185eee53fb89148645fc789ddb`.
- `android/core/src/main/kotlin/org/unovyra/uno/core/Controller.kt` — Git blob `2573b118e8523c84829371c9f90ed21806601d26`.
- `android/core/src/test/kotlin/org/unovyra/uno/core/ActionReceiptRecoveryTest.kt` — Git blob `bbdb2658a36db76b7ffbcb5e324a96ee471b29ca`, **11 new regression scenarios**.
- `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt` — register new regression suite.

Unchanged and independently byte-matched against existing GitHub baseline for this local compile: `Contracts.kt`, `ActionIntentJournalTest.kt`, `ActionJournalControllerIntegrationTest.kt`.

**Execution:** local `kotlinc-jvm 1.9.0`, OpenJDK 21, six exact source/test files: `ActionReceiptRecoveryTest` **11/11 PASS**, `ActionJournalControllerIntegrationTest` **23/23 PASS**, `ActionIntentJournalTest` **12/12 PASS**, aggregate **46/46 PASS**. Three additional identical-process invocations of each suite returned **46/46 PASS per repeat**. 12 Kotlin compile warnings remain from intentionally deprecated legacy `dispatch()` usages in old integration tests; zero compile errors.

Negative cases include stale timestamp before native admission, future-dated sample, same-timestamp boundary, post-dispatch journal STOP, malformed receipt ID/digest/source/generation/status, duplicate receipt, recovery from `RECEIPT_RECORDED`, corrupted hash, torn receipt tail, no redispatch after reboot, and receipt before `MAY_HAVE_EXECUTED`.

**Not run at this HEAD:** `cd android && bash scripts/run_all_preflight.sh`, Android Gradle assembly/lint, permission/native readback tests on A52, power-cut/kill tests of the actual Android FS, multi-process fault injection or combined transaction proof. No GitHub Actions were run, no APK was released.

## 4. Next acceptance gate, still open

- Single trusted Android storage transaction for `L,D,used,receipt,M-ref` / crash recovery with fault injection at each fsync boundary; encrypted/authenticated state as needed and explicit disk-full/quota handling.
- Android trust-controlled clock/boot/session, app owner authentication, exact effect & permission checks; independent native readback with time and attribution semantics.
- STOP linearization guarantee must be implemented in **real** Android trusted dispatch; synchronous JVM `NativePort` + lock cannot prove it.
- Real model/weights/runtime, Android UI/UX, speech, device thermal/PSS and all end-to-end product acceptance remain separate open gates.

**No transfer into Neural-Language and no automatic adoption of historical B2 model/weight ABI.** The permanent goal stays full UNO 1.0; this is one reference safety/recovery increment only.
