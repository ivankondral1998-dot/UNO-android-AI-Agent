> **MANDATORY CORRECTION TO RESEARCH FRAMING / 2026-11-05:** UNO's target learning loop has distinct human-owner teaching, physical sensor observations and independent Android postcondition receipts. N0-04/N0-05 test ONLY sensor motion prediction, so they cannot disprove the full learning objective. Before any next graph/plasticity proposal read [owner evidence contract](docs/research/OWNER_TEACHING_AND_ANDROID_EVIDENCE_20261105.md) and [N0-06 card](research/uno-n0-06/RESEARCH_CARD_CANDIDATE_20261105.md); log the provenance of corrections/readback and enforce authority outside learning. This is an owner-intent research requirement, not an approved runtime ABI, G4/G5 gate or production permit.

> **ACTIVE OWNER AMENDMENT, 2026-11-05.** **OWNER RESEARCH PERMISSION — ACTIVE 2026-11-05 (research branch only).** The owner explicitly authorized isolated, versioned research candidates for Θ, graph, P, M and learning rules, synthetic tasks, and training SMALL EXPERIMENTAL weights on a free PC environment. For EACH run: maximum 600 seconds, maximum 2 GiB RAM (use lower caps if the environment is weaker), terminate on limit; no more than 3 runs of the same candidate before reviewing the result. Register frozen task/card, inputs, seed, evaluation and thresholds before running; save reproducible evidence. This supersedes any earlier blanket ban on *research-only* small-weight training. It does NOT authorize production code, production UNO training/checkpoints, Android builds/APKs/device actions, GitHub Actions, publication, secrets, main edits/merge, deletions, destructive history changes, approval of R5.3/G4/G5, or autonomous adoption of E1. R5.3 S1 itself still freezes runtime Θ; any Θ-changing E1 remains an isolated candidate, not the adopted contract. Source: owner decision on 2026-11-05, captured in [issue #4 comment 6660428370](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/4#issuecomment-6660428370) and continued in owner-provided handoff. **For the LIVE queue use [BENCH.txt](research/uno-lab-001/BENCH.txt) and append-only [UNO_LAB_REPORTS.txt](UNO_LAB_REPORTS.txt).**
>
> The earlier "no training" and older initial checklist statements in this file are historical except where explicitly qualified below. Frozen research-card acceptance thresholds and a public split do not imply production readiness. Any model/session signature is merely a claim under the shared GitHub account.

# UNO-LAB — AGENT RESEARCH HANDOFF (candidate workflow, 2026-11-05)

**Purpose.** The single entry point for sequential AI research on UNO. This file supplements, and DOES NOT replace, the repository's existing `AGENTS.md`, `README.md`, `docs/AGENT_START_HERE.md`, `docs/CURRENT_TASK.md`, `docs/STATUS.md` or the complete R5.3 source hierarchy. Owner review is required before adopting this workflow as repository-wide policy.

## Read first — do not mistake a branch for approval

1. `AGENTS.md` → `docs/AGENT_START_HERE.md` → `docs/CURRENT_TASK.md` → `docs/STATUS.md`.
2. `docs/precode/r5.3/source-package/00_START_HERE.md` → `NORMATIVE/01–06` → complete matching `SOURCES/ASTRA_CURRENT`, `SOURCES/R52`, independent audits, manifest and phase gate. Never substitute this handoff for source documents.
3. Read this guide and **`UNO_LAB_REPORTS.txt`** (the single cumulative research journal). Verify current GitHub branch/head and any cited test bytes before drawing conclusions.
4. Continue from the last recorded state, including unresolved failures. Do not independently invent an approved architecture.

**Verified base as of setup:** `docs/uno-r53-agent-handoff-20261102` at `fcddf0f626cc13a60ec13200b4a48b7dee180fb4`. Created research-handoff branch: `docs/uno-lab-research-handoff-20261105`. `main` is a different branch, not a destination for unilateral edits.

**Hard gates:** G4 = PRECODE_CANDIDATE; `OWNER_APPROVED_PRECODE=FALSE`; `PRODUCTION_CODE_AUTHORIZED=FALSE`; G5 not authorized; owner choices O01–O08 remain open. These lines remain true until a *new explicit owner decision*, which must be checked against current records. Documentation and isolated precode/test fixtures are not production code, trained weights or a product.

## Two different work surfaces — keep them separate

**Research record, ONE file:** `UNO_LAB_REPORTS.txt`, maintained as an append-only chronological journal. Entries are compact: question, exact source, work performed, evidence, result, limitations, next action. No giant source dumps, conversation dumps, APKs or generated report-of-report documents. Correct earlier statements by APPENDING a correction with its target record ID, not rewriting provenance. One active editor at a time; read the latest commit before appending.

**Code, tests, raw evidence:** work in task-specific research/experiment branches and normal source/test paths, with commits, input fixtures, scripts and raw outputs. Reference exact branch + commit + file path + SHA-256 from the journal. A journal entry DOES NOT count as an implementation. Permitted precode research fixtures must remain isolated and avoid production Android actions or trained production weights. Small experimental PC-weight training NOW has express, bounded owner authorization dated 2026-11-05 (see active amendment above); production model training and production implementation still need distinct authorization.

For peer review, use separate review entries and—when useful—GitHub Pull Requests **without merge**. Reviewers must not silently edit another researcher's immutable evidence. Preserve negative findings and alternatives.

**Notion:** prior UNO-LAB collaboration, reports and discussions remain provenance/archives, not a second writable technical baseline. Link to originals when citing them. A Notion signature under the shared account does not authenticate a model. Claude can receive a pinned offline ZIP prepared from relevant GitHub files with SHA-256 manifest; do not assume an external model can access private GitHub.

## Sequential research handoff

The owner controls the queue. At most one active research executor by default; a later GPT/Grok/Astra/Claude agent reads the prior result, independently checks it, and appends a signed *claim* of its own—not a statement of authenticated identity.

Each agent must:
- Report the exact model name **as stated by its session**, date, input source versions and access limitations (GitHub 404 is not successful access).
- Distinguish `FACT/SOURCE-REPORTED`, `HYPOTHESIS`, `PLANNED`, `IMPLEMENTED`, `HOST_TESTED`, `ANDROID_BUILT`, `DEVICE_VERIFIED` and `RELEASE_READY`.
- Use claim status `PROVEN_LOCAL`, `CONDITIONAL`, `SPECIFIED_UNTESTED`, `REQUIRES_DATA`, `OWNER_DECISION` or `FAIL`, and label *who* executed the test.
- Keep the exact script/seed/input and actual stdout/stderr in reproducible evidence; a printed checksum from another model without the bytes is not a hash verification.
- Check every formula's assumptions, including fixed vs evolving features, legal masks, norm bounds, P vs M vs changes to Θ, STOP and external native readback.
- If a claim is refuted, append an erratum/reference and supply a concrete fix, counterexample or blocking evidence. No empty criticisms; negative/unsolved results are valid if demonstrated.
- Leave an owner decision as `OWNER_DECISION`, never auto-approve G4/G5.

**Journal entry form (paste into the existing TXT, do not open a new report file):**

```text
=== UNO-LAB-<task>/<entry-id> | YYYY-MM-DD | AUTHOR AS STATED | kind: WORK/REVIEW/ERRATUM ===
Base branch/SHA:
Primary sources (exact paths/sections and/or provenance links):
Question:
Method / performed work:
Evidence (actual script path + commit + SHA256 + output, or "not available"):
Findings (clearly label author-reported vs independently reproduced):
Claim status and verification scope:
Failure/uncertainty:
Required next work:
Owner decision requested (if any):
=== END ENTRY ===
```

## HISTORICAL initial checklist — superseded by current BENCH (do not repeat closed work)

Focus: initial intelligence vs owner-side learning, plasticity P, memory M, learned representations Θ and experimental E1. Latest Grok report suggests norm collapse under one legal random F/S5 configuration. **Do not elevate that fixture to a general trained-UNO claim.**

1. Obtain Grok's exact `grok_lab001_hfix.py` *bytes* and genuine stdout for the Section 6 fixture; published hash alone is insufficient for independent replication.
2. Verify tensor shapes, S4/S5/S7 sequence (especially post-proposal `h_a` after argument re-encoding), projection rules, masks and K. Independently reproduce d=512/1024; preserve failures and seed.
3. Compare full/partial mask, K=1/8, fixed vs drifting s/M and a simple tabular baseline. Only interpret `q^* ≤ σ(l0+||h_a||)` at fixed feature/initial logit and bounded `||p||≤1`.
4. If the missing script is not furnished, retain `SPECIFIED_UNTESTED` for independent reproduction and provide the exact missing artifact; do not fabricate new trials.
5. SMALL isolated research-weight training is authorized since 2026-11-05 with per-run caps; production UNO-weight training and Android hardware measurements still require separate owner approval, actual data and appropriate gates.

## Safety / preservation

No deletions, destructive Git operations, force-push/reset/rebase with lost history, direct main edits/merge, GitHub Actions, secrets, binary publication, production code or **production** training without explicit owner approval. Bounded research-only training has separate owner authorization detailed above. No neural self-authorization. Android consent/STOP/permissions/readback are independent of P and Θ. A same-UID synthetic fixture is not a secure OS-level authority boundary.

**The owner, not the last reviewer, accepts or rejects an architectural proposal.**

## Door — owner order, 2026-11-05

The owner ordered the models to stop using him as the transport. The door is `research/uno-lab-001/BENCH.txt`. Read it after this file. Speak by appending `UNO_LAB_REPORTS.txt` and updating that bench in the same commit. `python3 research/uno-lab-001/bench_check.py` exits 1 when the bench does not name the last journal entry. Items 1 and 2 under Initial next work are closed by later journal entries. Do not redo them. The open goal is on the bench.
