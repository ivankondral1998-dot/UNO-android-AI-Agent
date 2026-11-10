# UNO 1.0 — FOUNDATION ACCEPTANCE REGISTER R1 (2026-11-09)

**Actual source:** `feat/uno-foundation-hardening-20261107` commit `083e30c0f53921b87003c40f20c64fa1786dce3f`. **STATUS: FOUNDATION_INCOMPLETE.**
All checks are tied to source commits, NOT promises about a model or external Android actions.

**ROADMAP CORRECTION:** Original WP-03 is operator F; WP-04 is own weights; WP-05 is exact/semantic memory; WP-06 is end-to-end agent. The previous "WP-05 text cycle", "WP-05 STOP" and "WP-06 disk usage" rows were misleading labels for separate chat experiments, not evidence that original roadmap stages have been completed. See [corrective source](2026-11-09_ORIGINAL_WP06_REFERENCE_R1.md).

| Gate | Code / concrete evidence | Status | Exact missing proof |
|---|---|---|---|
| Environment/build | Android SDK35, NDK, 17 JDK; [CI #42686428239](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42686428239); 235 host checks, Gradle compile, lint, aapt | ANDROID_BUILT | No physical test of this exact SHA |
| WP-01 platform/diagnostics | battery/PSS/thermal/sensors sandbox, manual STOP | PARTIAL_DEVICE_OBSERVED historically | No full organism performance, quality or energy |
| WP-02 Android trust | DenyAllAndroidPort, NOOP credential/one-use, independent app-private byte-readback fixture | FAIL_CLOSED_PARTIAL | Trusted real Android dispatcher/permissions/owner binding/native OS readback, crash/UNKNOWN lifecycle |
| EXPERIMENTAL local GGUF (not original WP-04) | local GGUF/llama.cpp JNI, Qwen candidate | DEVICE_OBSERVED on old ci42670625565 only | Model quality, resource profiles, long context, new exact APK verification |
| EXPERIMENTAL text cycle (not original WP-05) | `UnoTextCycle` runs local UI event → bounded prompt → model → cancel/STOP check → `AtomicFile` persist → hash/revision; host 19 cases | HOST_TESTED + ANDROID_BUILT | Cross-app state, long term memory, restart causal identity, edge/device instrumentation |
| EXPERIMENTAL chat encryption (not original WP-05) | `UnoChatCipher` AES-GCM, `UnoSecureChatHistoryStore` AndroidKeyStore, fail-closed v2; host 10 cases | HOST_TESTED + ANDROID_BUILT | Device Keystore roundtrip, recovery/security review. Old plaintext v1 is preserved and NOT removed |
| EXPERIMENTAL process STOP (not original WP-05) | `UnoProcessStop` one-way same-process latch, both UI activities; host 3 cases | HOST_TESTED + ANDROID_BUILT | Persistent stop/re-arm, cross-process isolated service, force-stop/power-loss behavior |
| EXPERIMENTAL no-copy GGUF (not original WP-06) | direct SAF `/proc/self/fd/<fd>` GGUF path, separate explicit legacy copy-import option | ANDROID_BUILT / DEVICE_UNTESTED | On-device SELinux, seekability, actual mmap loads, no network provider |
| Original WP-05-T05 fresh reopen diagnostic | Owner-tapped readback from newly opened AES-GCM file, durable locator + SHA of immutable diagnostic, readonly no genesis/AtomicFile backup repair. [Implementation](2026-11-10_EXACT_REOPEN_DIAGNOSTIC_R1.md) | IMPLEMENTED / CI_PENDING / DEVICE_UNTESTED | A52 actual Keystore, same-boot process restart, rollback, cross-boot time semantics |
| Original WP-06-T01 neutral integrated reference | `UnoFoundationReferenceCycle`: one Percept, ExactMemory, NeuralPort, untrusted Proposal, separate consent, TrustController + fake readback; CI [#42698868434](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42698868434), 23 new host tests, 258 total | HOST_TESTED + ANDROID_BUILT (not wired to Android) | Real model memory/state, permission/consent, true readback, cross-process STOP, device tests |
| 10-Nov source audit of owner observations | Passive snapshots no longer write vault or depend on Keystore; separate consented memory capture, immutable full-report SHA binding and explicit revocation; static negative checks. [Audit](2026-11-10_CORRECTIVE_IMPLEMENTATION_AUDIT_R1.md) | IMPLEMENTED / HOST_TESTED / ANDROID_BUILT (CI #42715526164, 299 host checks); DEVICE_UNTESTED | Owner authentication, A52 Keystore, powercut, anti-rollback and semantic memory unresolved |
| Original WP-05 Android owner event integration | Existing owner-selected device metrics snapshot now routes through one UnoFoundationReferenceCycle, UnoAndroidMemoryOwner exclusive file lock and GCM vault; persistent event IDs and exact byte check; [source note](2026-11-10_ANDROID_EXACT_OBSERVATION_WIRING_R1.md) | IMPLEMENTED / HOST_TESTED / ANDROID_BUILT (CI #42708637287, 299 host checks); DEVICE_UNTESTED | Physical Samsung test, process restart, reboot, lock tests, full raw/semantic memory, anti-rollback |
| Original WP-05-T01/T02 encrypted exact-memory candidate | `UnoExactMemoryPort`, core `UnoEncryptedExactMemory` and Android `UnoAndroidExactMemory`, source/boot/epoch-bound raw records, GCM, AtomicFile, revocation; neutral reference cycle can inject the port | IMPLEMENTED / HOST_TESTED / ANDROID_BUILT (exact source 85be43e; CI #42704791187, 34 vault checks, 292 total); DEVICE_UNTESTED | Device AndroidKeyStore, boot ID, persistence on device, rollback protection, semantic search and owner UI missing |
| Product memory | bounded encrypted chat vs exact/semantic memory distinct | INCOMPLETE | Durable exact/semantic memory, provenance, forgetting, consent, recovery, isolation |
| Product perception/plan/effects | lab sensor inventory, no offline ASR/TTS; no dispatch catalogue | INCOMPLETE | WAKE/ASR/TTS, sensor contracts, planner, authority, native readback |
| Original WP-03 operator F (R5.3 research) | Research documents retained | NOT IN PRODUCTION | Owner approval and independent mathematics / new weights training gate |
| Commercial release | NO actions/publishing | NOT_AUTHORIZED | Owner decisions, licensing, threat model, full device tests, signing and distribution |

## Owner's existing Samsung A52 evidence (old WP04 source)
User supplied screenshots labelled `UNO TEST · ci42670625565`, which match built source `7990bc8af5cc58a6c195d42c957be6dc0e75f412`. They visibly show real Qwen generation inside UNO; examples include `111 токенов · 2,4 т/с (общая) · TTFT 24696 мс`, `<think>` leakage and poor context retention. The owner reports smooth Samsung UI. This is **DEVICE_OBSERVED_TEXT_GENERATION** only, not independently measured RAM/energy, offline network isolation, Android native effects or quality acceptance. Screenshots remain in the chat; do not claim stored in GitHub.

## Remaining owner-gated decisions
No silent approval of R5.3 G4/G5, new weight training, runtime weight updates, Android privileged action catalogue, publication, debug-to-release signature, or new permissions. Until authority is implemented, `DenyAllAndroidPort` remains. Do not confuse no native actions with a verified action agent.

## Next engineering work order (not yet implemented)
1. A unified durable exact/semantic memory boundary with explicit owner permissions, recovery, timestamps/boot identity and provenance; real chat read/write integration; no independent model authority.
2. Isolate neural execution from trusted Android boundary and implement typed decision/proposal → owner/OS permission → durable ticket → at-most-once dispatch → **independent native readback** → memory (safe app-owned effect first, OS effects only after owner-approved scope).
3. Local speech/microphone, safe sensor events, bounded planning, resource/thermal tests on A52; correct Qwen thinking template and long-turn TTFT, compare quality against fixed baseline.
4. Establish real-device integration gates and independent security review before any `FOUNDATION_COMPLETE` designation; later separate operator F research.

Do not ask owner to download build/test artifacts until a meaningful device experiment is required. Preserve historical APK/source artifacts and package identities; no deletion or GitHub Actions without scope.
