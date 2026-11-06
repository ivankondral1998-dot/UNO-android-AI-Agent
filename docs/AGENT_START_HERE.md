> **LIVE OWNER OVERRIDE — 2026-11-06:** Перед историческими правилами учитывать [действующие полномочия](decisions/2026-11-06_ACTIVE_AGENT_RULES_V2.md) и [правило общения](decisions/2026-11-06_OWNER_COMMUNICATION_RULES_V1.md): владельцу — простой, краткий, но содержательный русский ответ; результат и границы проверки, без длинных отчётов в чате. Историческое «production code = FALSE» ниже не отражает отдельное разрешение от 2026-11-06.

# UNO — MANDATORY FIRST READ FOR EVERY AGENT

**Current phase G4: PRECODE CANDIDATE R5.3. Owner approval = FALSE. Production code authorization = FALSE.** Read this every time you resume. This applies to GPT, Grok, Codex, Work and human maintainers.

## Exact read order (do not substitute summaries)

1. [CURRENT_TASK.md](CURRENT_TASK.md) and [STATUS.md](STATUS.md): actual phase, permissions and remaining gates.
2. [R5.3 package start](precode/r5.3/source-package/00_START_HERE.md).
3. [NORMATIVE/01 — source hierarchy](precode/r5.3/source-package/NORMATIVE/01_SOURCE_HIERARCHY_AND_CONTRACT_INDEX.md).
4. [NORMATIVE/02 — formal corrections](precode/r5.3/source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md).
5. [NORMATIVE/03 — subsystems](precode/r5.3/source-package/NORMATIVE/03_CONSOLIDATED_SUBSYSTEM_CONTRACTS.md).
6. [NORMATIVE/04 — individual D/X/B/M gates](precode/r5.3/source-package/NORMATIVE/04_ALL_GATES_D_X_B_M.md).
7. [NORMATIVE/05 — owner decisions](precode/r5.3/source-package/NORMATIVE/05_OWNER_DECISIONS_AND_FUTURE_EVIDENCE.md).
8. [NORMATIVE/06 — verification boundaries](precode/r5.3/source-package/NORMATIVE/06_VERIFICATION_BOUNDARIES.md).
9. Read the full matching Astra, R5.2 and evidence files in [source-package/SOURCES/](precode/r5.3/source-package/SOURCES/). Never implement from one-page summaries.
10. Check the [machine-verifiable 64-file manifest](precode/r5.3/SOURCE_PACKAGE_IMPORT_MANIFEST.json), [phase gate](precode/r5.3/AGENT_PHASE_GATE.json), and [R5.3 index](precode/r5.3/README.md).

## Non-negotiable boundaries

- UNO is one local neural organism (one shared operator) and has **new trained weights only after training occurs**; no cloud/OpenAI/OAuth/internet dependency.
- Legacy Jarvis/JNO is history, NOT the UNO brain. Android OS permissions and authority checks remain external trust boundaries; never impose old OwnerGate as mandatory implementation.
- R5.3 is candidate documentation, NOT validated model intelligence, proven global stability, tested APK, measured Samsung A52 performance or final baseline.
- An agent cannot approve on behalf of the owner. PRE-CODE BASELINE and transition G4 → G5 remain explicitly **NOT AUTHORIZED**.
- Do not delete files, rewrite history, force-push, change main, merge to main, run GitHub Actions, write production code or start training without separate explicit authorization.
- Historical APPROVED text in an earlier agent report is NOT an owner decision. Preserve source history; propose corrections in new versioned documents with evidence.
