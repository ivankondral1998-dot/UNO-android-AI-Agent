# UNO C1–C4 — cross-source static checkpoint R5 (2026-11-14)

Status: STATIC_SOURCE_REVIEW_ONLY / HOST_UNTESTED / ANDROID_UNBUILT / DEVICE_UNTESTED.
This is an append-only review candidate, not a change to Astra/R5.3 or owner approval.

## Exact refs reviewed
- main AGENTS.md V4 at `1df9ee7cc592f606939c8f004e1b11edd916b56c`; 2026-11-06 feature-branch production code authorization, no new Actions/weight training/merge authorization.
- Android base `feat/uno-permanent-full-foundation-20261111@ec9764f03dcdca305b575b41514d0aa153d2aab7`.
- Repair branch `fix/uno-consent-freshness-20261114@3f7f5ae2162b2542e27811526f7f796107701b42` (read-only source snapshot before this record).
- R5.3 `docs/uno-r53-agent-handoff-20261102@7e94b717d73312f1bf3a926ea5f89586c9d23d7b`: NORMATIVE/03, ASTRA_CURRENT/ASTRA_04.
- Terra `audit/uno-terra-math-training-20261112@0af492ee7a8d15b371bf0de1c21d73ca1fd8b050`: IMPLEMENTATION_GATE_V1.
- UDC candidate branch `design/uno-unified-cycle-data-20261112@3b06b024199d9bfcf1362a6b48156dfa0c74c9dc`.
- Existing implementation records R1–R4 on repair branch; issue #6 (19 comments at review).

## Verified from source, not from executed tests
| Area | Present in repair branch | Open acceptance boundary |
|---|---|---|
| C1 consent | Controller.prepare limits ticket to min(deadline, consent expiry); dispatch re-samples after journal arm; readback re-samples before commit. | `trustedClockNanos == null` fallback remains host-only; OS privileged linearization, owner/permission revalidation and native readback not established. |
| C2 revocation | UnoMemoryPorts serializes gateway calls, blocks scope locally and writes semantic tombstone before exact revoke; R2–R4 describe additional Android source hardening. | Not an atomic exact+semantic+derived-state commit. Direct legacy paths, crash before tombstone, authenticated rollback, cross-process and Android Keystore/AtomicFile power-loss need independent verification. |
| C3 weights | admitWeights returns PAYLOAD_CHECKSUM_ONLY on self-declared checksum; WeightSlot.admitted() always false. | No authenticated shape/dtype/offset ABI/2 loader, approved Θ or running trained F. This is deliberately fail-closed, not inference readiness. |
| C4 goal/session | R1/R3 record host-only UnoFSession work cookies and result-binding; same synthetic UnoFReference. | No proven Android end-to-end single F, owner GOAL encoder, shared live memory state, real planner/action/outcome training path. |

## Mathematical dependency check
ASTRA_04 §1, §4 explicitly distinguishes exact payload from learned memory, requires generation/ABA, revocation, provenance and transactional persistence; §4 requires used+receipt+newP+newM references to publish together. Existing two-store barrier is a partial mitigation, not proof of that invariant.
NORMATIVE/03 points to ASTRA_01 S1/S4–S7, ASTRA_02 tensor ABI, ASTRA_03 training, ASTRA_04 memory, ASTRA_05 trust/resources and ASTRA_06 evolution. Do not infer integrated F or global stability from individual patches.
Terra IMPLEMENTATION_GATE §1 P1–P8 and §3 G01–G11 remain acceptance obligations; candidate tests are not PASS until run.

## Concrete next execution gate
1. Before further feature changes, obtain full repair-branch checkout and run Kotlin host suite from `AllHostTests.kt`, retaining exact commands, output, environment and exit codes. No APK is required for this step.
2. Review all Android call sites that read/write exact/semantic scopes or publish derived state against the revocation barrier. Write a failing deterministic crash/restart test before claiming C2 closed.
3. Cross-check UnoFSession and UnoFoundationReferenceCycle against UDC v0.3 GOAL/proposal causality; do not connect synthetic F as trained inference.
4. Only after static/host checks and owner device gate, do one Android build and A52 validation. No GitHub Actions, no training, no merge into main.

Limit: this checkpoint is a targeted C1–C4 static dependency review, NOT a complete independent re-proof of the entire R5.3 mathematical corpus. No source or tests were executed in this review.
