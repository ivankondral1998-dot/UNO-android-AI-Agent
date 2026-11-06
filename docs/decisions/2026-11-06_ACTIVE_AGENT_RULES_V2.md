# Active owner overrides and agent execution rules — 2026-11-06

This document is the current additive override to historical R5.3 handoff instructions. Read it BEFORE docs/CURRENT_TASK.md and the immutable source package. Historical documents are provenance, not current permission state.

## Owner decisions now effective
1. Owner explicitly authorized **production code** on 2026-11-06. PRODUCTION_CODE_AUTHORIZED=TRUE. Continue actual implementation on a separate feature branch. This is NOT permission to train weights, publish APK, run GitHub Actions, merge main, delete, or rewrite history.
2. O01–O08 are **revisitable design decisions**, not eight blockers or an approval questionnaire. Implement using current R5.3 contracts and documented safe defaults; revisit only when a real failure, evidence or explicit new owner decision requires it. Do not silently decide unbounded authority or bypass Android trust/STOP/readback.
3. Rules may change dynamically through explicit owner instructions. Record date, superseded rule and scope in an additive versioned decision file. Do not retroactively edit R5.3 originals or pretend old handoff text is current.
4. Do not repeatedly restart full paper audits, request re-approval of settled permission, or invent new lab series. Prioritize source code, reproducible tests and real device evidence.
5. Owner requests direct comparison of weight representations, including **B2/LR2/H2, factorized C256R32 and structural UNO-N0**, not merely parameter counts. Read docs/research/2026-11-06_WEIGHT_FAMILY_COMPARISON.md. Do not announce a winning family before matched tests. Structural plasticity is not a license to replace the single shared organism with separate brains.
6. Communicate concisely; provide full audit detail in artifacts, not long chat explanations.

## Continuing hard constraints
Single local organism; no Jarvis weights as core; no cloud dependency; licensed data; external Android authority; consent, STOP and independent native readback; no blind retries on UNKNOWN/MAY_HAVE_EXECUTED. No GitHub Actions, main merge, deletion, force-push, training, or release without explicit additional authorization.

## Current evidence
A small Kotlin event-queue/STOP primitive exists on feat/uno-production-foundation-20261106 and passed a host Kotlin test. It is NOT a complete Android trust boundary, neural F, trained model, Android build or device verification.

7. Owner explicitly instructs agents to DESIGN and TEST NEW weight representations, not merely choose among existing B2/LR2/H2/C256R32/N0. UNO-HSR v1 is one experimental proposal: see docs/research/2026-11-06_UNO_HSR_WEIGHT_ARCHITECTURE_V1.md. No family is selected by default; prioritize measured task quality per joule on A52. Preserve R5.3 as historical baseline, and do not treat synthetic approximation error as intelligence.
