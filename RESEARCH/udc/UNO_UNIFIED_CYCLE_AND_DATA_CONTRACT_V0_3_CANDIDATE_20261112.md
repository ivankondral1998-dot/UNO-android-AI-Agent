# UNO-UDC-001 v0.3 — единый F, GOAL-mode и данные без утечек

**Статус:** SPECIFIED_UNTESTED / DESIGN_CANDIDATE / NOT_OWNER_APPROVED. 2026-11-12. Это новая, **не утверждённая** инженерная версия; v0.1 и v0.2 сохранены без изменений. Ни модель, ни веса, ни Android runtime, ни датасет не реализованы этим документом.

**Основание изменений:** Grok [review 6810936141](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/6#issuecomment-6810936141), GPT-6 [response 6811034763](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/6#issuecomment-6811034763), Grok [acceptance of qualifications 6822681915](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/6#issuecomment-6822681915); новая [v0.2 design-review 6822968541](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/6#issuecomment-6822968541).
**Android baseline:** `feat/uno-permanent-full-foundation-20261111` @ `178ac32f53d1e84d44ca27475279d35113c19719`. **Math baseline:** `docs/uno-r53-agent-handoff-20261102` @ `fb2b3f4c8ad299434fe555b6ccce728c58299e97`, original `SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` S1–S7, `ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` L3a–L5 and §§4–7, `NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md`, `NORMATIVE/03_CONSOLIDATED_SUBSYSTEM_CONTRACTS.md`. Не заменяет полные ASTRA_02/04/05/07/08 и адресные R52.

## 1. Реальный gap Android

- `UnoChatActivity → UnoTextCycle → UnoNativeEngine.generate`: отдельный CPU/GGUF-чат, сохраняющий transcript, не связанный с F/Android authority.
- `UnoActivity → UnoFoundationReferenceCycle`: reference `Percept → exact memory → NeuralPort → proposal → owner → TrustController → readback`, но Android использует `NoWeightsNeuralPort` и `DenyAllAndroidPort`, никакого исполненного Android effect.
- `UnoBoundedPlanner.bound/take` пропускает **только идентичный** parent proposal, один потраченный шаг. Это identity check, **не** настоящая композиция multi-step plan.
- `Contracts.kt` отдаёт `NeuralOutput(stateDigest, action?)`: недостаточно для состояния session/goal, разговорного ответа, typed terminal/clarification и долгой причинной последовательности. Простой parsing текста GGUF в действие — запрещённый shortcut.
- Host synthetic S4/S5 и LFM trial не являются обученной F или A52 evidence. Точная память на A52 имеет лишь ограниченный owner-observed сценарий. Не переносить статус за пределы источника.

## 2. Кандидат единого U0.3-цикла

```
UI text / future PCM, image, sensor, OS
  → bounded typed admission with provenance, boot/session epoch, causal time
  → independent owner-goal snapshot; check goal-version switch
       IF SWITCH: save exactly one working s; set g=0 and temporary s=0;
          encode raw canonical owner-intent in GOAL mode by SAME F, I=∅;
          finish bounded GOAL session → set g=h_final; restore saved working s;
          invalidate obsolete work by goal-version/epoch; no authority granted
       ELSE: keep current g, no redundant goal re-encoding
  → LIVE memory catalogue I_live, NO teacher answer keys
  → normal S4: z0(input, restored working s, current g, meta);
                q=tanh(Wq z0); attention over eligible I_live
         if I_live=∅: r=0; z=tanh(z0) [NOT z=z0]
         else: r=Σsoftmax(q·ki/(sqrt(m) TM))*vi; z=tanh(z0+Wr r)
         h0=ρs+(1−ρ)z
  → S6 feasible prefix block mask and K policy, real kernel skips
  → shared S5 F(h,z) → h_dec, model output
       ├─ internal verb=0/1/2 (ABSTAIN/CLARIFY/NOOP)
       │    → bounded UI + TERMINAL; NO S7, NO Ticket/consent/readback/P-update
       └─ external verb=3…23
            → canonical args re-encode with SAME F, s_start=h_dec,
              role=PROPOSAL and frozen g → h_a; NO trace-freeze before h_a
            → only NOW S7 q_R(a), q_Y(a), risk/conf and acceptance threshold
            → owner goal + capability/risk envelope validation
            → current planner: IDENTITY CHECK ONLY; decomposition CLOSED GATE
              [future caps: 64 nodes, 16 active-plan steps, ≤3 safe retries total;
               each child envelope ⊆ parent; no parent-deadline extension]
            → independent auth/consent/STOP/deadline, fresh trusted gate
            → durable ticket, allowed dispatch, independent native readback
            → audited outcome/UNKNOWN/MAY_HAVE_EXECUTED and next observation
  → one typed terminal/status/UI rendering, never inferred permission from text
```

**GOAL-mode and causal switch contract (ASTRA_01 §5, mandatory):** A *change of the active owner-goal* (selected by highest priority, then earliest deadline, then lowest ID) triggers a distinct bounded GOAL encoding. Snapshot exactly one working `s`, set temporary `g=0` and `s=0`, force `I=∅` (no memory-read), encode the **raw canonical owner intent** under role/mode GOAL through the same F, and only after its completion assign `g=h_final`; restore the saved working `s` before a normal observation path. During this GOAL sub-session, S4 uses `r=0; z=tanh(z0)` and must not read old semantic/exact memory to bias the goal vector. No independent language model or separate reasoning-state cache is introduced. Aborted/invalid/stale goal encoding must not publish partial `g`, `s`, proposals, or permissions: fail closed and revalidate goal-version and work cookie before publishing any result. The original ASTRA limit is **≤4096 additional events** for recoding up to 64 goals, charged to the admission/resource budget; this document does not assert that Android reference code implements it. This switch mechanism is **not** required on every ordinary frame or turn when the active goal is unchanged. Goal decoding by F still cannot expand the owner's trusted action envelope.

**S4 memory contract:** `I_live` selected using store snapshot, scope, consent epoch, TTL, representation compatibility, causal boundary and available budget, **not teacher-selected correct keys**. The memory query is computed from z0 by the network. Optional `teacher.target_memory_id` is for `L_retrieve` **only**, cannot influence `I_live` or F input. `RetrieveExact` and semantic `r` are different operations. Summary is not complete/exact. Empty I regression is mandatory.

**S7 contract:** Canonical re-encoding of external args is a separate procedure *before* S7, not S7 itself. It uses the **same F**, `h_dec` as starting `s`, explicit role `PROPOSAL`, and the **frozen current `g`**. Until the canonical `h_a` has been computed, never freeze a proposal trace or evaluate outcome/observability for that external proposal; generated prefix/temporary `h_a` are not automatically committed as trusted session state. `a∈E={3,…,23}` only. For `a∈{0,1,2}` S7 rows are frozen/ineligible, no outcome labels, ticket, consent, dispatch, native readback or P-update. NOOP ≠ NOOP_ALREADY_TRUE (which requires native target predicate). In Kotlin `Proposal.verb` currently permits `0..127`: this is a candidate-versus-current ABI mismatch, **not** proof of valid external effect. Design gate before any production ABI change.

**Single F/session contract:** One operator/Θ, one causal neural session holding s/g/belief/memory and goal snapshots; several Android UI/percept providers, not several reasoning brains. `Percept(TEXT, authenticatedSource=false)` from chat is an observation, not authentication. Model outputs *typed decision/proposal* plus separate bounded UI answer, NEVER a parseable authority token inside free text. Current `UnoFoundationReferenceCycle` is synchronous reference code and lacks production long-turn/session executor; a versioned session/executor contract and lifecycle/epoch/STOP gates are **new design and code work**. Do not claim hooking an Activity to `NeuralPort` alone completes it. `UnoNativeEngine.generate` may remain diagnostic, but cannot generate executable proposals. New session controller is coordination, not another neural brain.

**Planner gate:** Current code only identity check; `open_app→type_text→send` with different verbs rejected. True composition is a CLOSED DESIGN GATE and must preserve ASTRA_01 §5 bounds: **at most 64 decomposition nodes**, **16 steps in the active plan**, **at most 3 safe retries in total**, **each child effect envelope ⊆ parent capability** (same resource, field-wise subset), and **parent deadline cannot be extended**. Each node inherits the remaining parent budget. Additional requirements: explicit typed plan DAG/ordered steps, independent per-step owner/permission/gate checks, verified target-time predicates, idempotency classification, STOP, crash/replay safety, no blind retry of uncertain effects, and final goal verification rather than last-step self-report. If mandatory subgoal isn't itself final target, do **not** demand it already imply completed target (ASTRA_01 §5). Until approved and implemented: `MULTISTEP_NOT_IMPLEMENTED`.

**Outcome boundary:** `NativePort.dispatch` / `nativeReturn` ≠ independent OS result. Need ticket/source generation, observed timestamp and phase, scoped endpoint predicate, target-time mode, attribution (CONTROLLED/OBSERVATIONAL/UNKNOWN). R=0 ⇒ Y missing/censored, never automatically Y=0. Uncertain post-dispatch state ⇒ UNKNOWN/MAY_HAVE_EXECUTED, **no blind retry**. STOP blocks new work and stale commit, not already executed effect. For `CURRENT_ALL` require atomic joint snapshot or valid overlapping stability certificates; separate TRUE readings at different times are not simultaneous truth.

## 3. UNO_EPISODE/0.3-CANDIDATE: separate training, inference, audit

One sample is a **causal episode** with 1..N turns, not an isolated command label. Three distinct serialized views are required for future pipeline implementation:

**A. MODEL_VISIBLE:** current typed observation/ref; source/modality; session/boot/event time; masks; valid as-of-now owner task context; **goal-version and GOAL-mode transition marker, safely committed s/g only**; *eligible* memory catalogue and permitted memory query interface (except `I=∅` during goal switch); resource budget. **MUST NOT include** teacher target record, future action outcome, model error discovered later, later owner's response or posthoc labels.

**B. TEACHER_AUDIT (train-target and provenance only):** `episode_id, source_uri/hash, license, permitted_train, permitted_derive, permitted_distribute, commercial_rights, consent_scope, PII/voice`, independent owner target predicate, target action/args/ABSTAIN, optional correct memory ID, native readback from separate observer, temporal endpoint, censor/attribution, split-group IDs, annotation timeline, annotator allowed-information manifest, phase BLIND_GOLD/POSTHOC_ADJUDICATION/INDEPENDENT_REANNOTATION/UNVERIFIED. Before releasing gold, verify annotation created independently from evaluated model output of same turn. `TEACHER_SAW_MODEL_PROPOSAL` or `TEACHER_DERIVED_FROM_MODEL` ⇒ QUARANTINE pending genuinely independent reannotation. A software validator can audit declared workflow records, **not read an annotator's mind**.

**C. COMPUTED_TRACE (replay only):** model/Θ/ABI digest, seed/counter, sampled q/K, actual skipped block set, s/z/h digests, generated proposal, controller/consent/ticket/dispatch events, readback *references*, actual MAC/time/peak memory. None of these becomes independent OS ground truth by being logged.

`teacher` cannot see `model_proposal` to create blind labels in a same-turn evaluation. Releasing A+B+C together to F at training time would re-introduce the leak. Train loss may access B, while forward input can only read A; C is derived from forward.

**Corpus families and their state:**
| ID | Required measured/labelled episodes | Current data status |
|---|---|---|
| E01 | RU text, varied ambiguous goals and verified intent labels | REQUIRES_DATA |
| E02 | SENSOR/OS typed values, missing/stale/unit/time, observer provenance | REQUIRES_DATA |
| E03 | PCM/WAKE/ASR/TTS, negatives, voice rights, acoustic-device diversity | REQUIRES_DATA |
| E04 | UI tree/image, bbox, dynamic changes and injection/fault cases | REQUIRES_DATA |
| E05 | delayed exact vs summary memory, recall/revoke/conflict/truncation | REQUIRES_DATA |
| E06 | goal/verb/args/plans, independent teacher demonstrations | REQUIRES_DATA |
| E07 | trusted auth/permissions/STOP cases (authority is native, **not learned**) | REQUIRES_DATA |
| E08 | physical readback, R/Y/censor/UNKNOWN/interference | REQUIRES_DATA |
| E09 | selected q/K/halt cost-quality *train-only oracle*, real skips | REQUIRES_DATA |
| E10 | crash/recovery/MAY_HAVE_EXECUTED/no blind retry | REQUIRES_DATA |
| E11 | multi-turn/multimodal dependency, old/new retention and OOD | REQUIRES_DATA |

These are **eleven requirements**, not eleven existing datasets. Current synthetic host tests and one A52 memory scenario do not establish any full legally usable training corpus.

**Split:** train/dev/cal/locked-OOD with grouping by same speaker, session, device, app family, source, paraphrase and template ancestry. No duplicate scene trajectory or related source fragments crossing locked split. Store sealed test under independent custody; published synthetic split is **not** sealed. Real rights to commercial training and derived weights must be established separately from technical validity and runtime Android permissions.

## 4. Original mathematics and test obligations

Follow ASTRA_01 S1–S7, original ASTRA_03 **L3a**, L4, L5 rather than a new simplified training loss. L3a includes class-conditional coverage and genuine terminal/abort cost with π_j>0; absent task group ⇒ REQUIRES_DATA. Use independently labelled action/args, memory write→future-query, outcome R and Y with censored denominator, supervised speech/grounding/etc only where targets exist. q/K/halt oracle is derived on TRAIN from measured quality/cost; h/z are **not externally true labels**. Stochastic S6 sampling and PRNG counters tracked; changing inference to argmax requires a new evaluation.

Offline Θ training uses frozen P=0; runtime Θ frozen for UNO 1.0. STE/QAT/TBPTT limitations explicit; fixed-mask γ=.9 does not prove adaptive-selector stability. Wake metadata head alone is **not** acoustic wake; audio candidate goes through PCM→W_audio→shared F→CTC→keyword. New SENSOR loss/head/width/thresholds/tokenizer do not inherit original B2 counts automatically. No training starts without model, data/license, resources, sealed tests and owner decision.

### Versioned acceptance cards (NONE EXECUTED HERE)

| Card | Expected independent check |
|---|---|
| T01 EMPTY_I_S4 | with z0≠0 and I=∅, r=0, z=tanh(z0), never z=z0 |
| T02 MEMORY_KEY_LEAK | changing teacher key with identical A does not change model-visible F input or q |
| T03 INTERNAL_NO_TICKET | verbs 0/1/2 never invoke S7, consent, ticket, native dispatch |
| T04 EXTERNAL_REENCODE | external canonical args re-encoded before S7; no stale h_a |
| T05 BLIND_TEACHER | known post-model-view annotation quarantined; cannot enter locked gold |
| T06 PLANNER_IDENTITY | current planner rejects multi-verb decomposed path |
| T07 NATIVE_RETURN | returned TRUE without readback never VERIFIED_COMPLETION |
| T08 STOP_AFTER_DISPATCH | MAY_HAVE_EXECUTED respected; no blind retry |
| T09 CROSS_BOOT | stale monotonic deadlines/consent invalid |
| T10 HOLDOUT_LEAK | overlapping template/source/session ancestry rejects sealed split |
| T11 MASK_KERNEL_SKIP | masked S5 expensive kernels actually not invoked |
| T12 CURRENT_ALL | TRUE predicates at disjoint timestamps do not prove simultaneous completion |
| T13 EMPTY_CORPUS | no licensed train data ⇒ NO_TRAINING_DATA, never PASS |
| T14 SINGLE_SESSION | chat/OS share one s/g version; STOP closes all entry points (requires new implementation) |
| T15 GOAL_SWITCH_ISOLATION | switch two distinct goals with nonzero old s and planted memory bait; GOAL input uses g=0, s=0, I=∅; only after full GOAL F result g=h_final, original working s restored; incomplete/stale goal switch never publishes |
| T16 PROPOSAL_FROZEN_GOAL | during external args canonical re-encode, confirm role=PROPOSAL, s_start=h_dec, g matches frozen goal; no trace freeze or S7 evaluation before h_a |
| T17 DECOMPOSITION_BOUNDS | proposed 65th node, 17th active-plan step, 4th safe retry, out-of-envelope child, or extended parent deadline rejected at design gate; existing planner still identity-only |

**Status of all cards:** SPECIFIED_UNTESTED. A52/device readback and model quality require separate physical tests. No numeric quality thresholds fabricated.

## 5. Remaining decisions and execution boundary

**For GPT-6/Grok peer review:** check all 17 cards against full R5.3 (ASTRA_02/04/05/07/08, R52, NORMATIVE/04–06), particularly S1 scheduling/goal transitions, exact memory snapshot/time, S6 mask legality, S7 eligibility, post-dispatch reconciliation and licensing. Find counterexample to v0.3, propose versioned v0.4 rather than silently rewriting.

**For owner:** eventual choices of model/weights/ABI, actual multi-step action design, production training authorization, and permissible Android effects; no choice inferred from silence.

**For Work/Codex (only when explicitly tasked):** independent audit and executable validation/fault tests of this versioned design, with code changes isolated from production branch until reviewed. Never auto-create synthetic “verified” readback. Do not start training or Actions because this file exists.

**Modification log:** v0.1/v0.2 preserved; v0.2 corrected five Grok objections. v0.3 adds explicit safe GOAL-mode switch and state restore (ASTRA_01 §5), PROPOSAL role/frozen g and no premature h_a freeze, plus 64/16/3/parent-deadline/envelope constraints and tests T15–T17. All test cards remain SPECIFIED_UNTESTED; not a mathematical global PASS.