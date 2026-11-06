> **УТОЧНЕНИЕ ПОСЛЕ СВЕРКИ SHA (2026-11-06):** исходный список 25+16=41 исключение содержал одну ложную запись: `UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW.md` уже был в Git под другим именем, Git blob SHA проверен. Исправленный индекс: **262 identical + 94 historical + 24 indexed-only + 16 research/private = 396**. Подробный [адресный реестр 41 исходной записи и 40 оставшихся](../precode/vnext-r4/UNMIRRORED_41_EXACT_LEDGER_20261106.md). Исторический счёт ниже сохранён как snapshot, не использовать как актуальный.\n\n# UNO — все доступные источники и реальные пробелы (06.11.2026)

**Ветка:** `docs/uno-vnext-r4-source-recovery-20261106` (основана на `docs/uno-lab-research-handoff-20261105`, не main). Для чтения сначала [00_START_HERE_CURRENT](00_START_HERE_CURRENT.md). Эта ведомость описывает **что реально существует и где**, а не повышает G4 или разрешает производство.

## Новейшие артефакты — прочесть по порядку

- [vNEXT-R4 full owner package (120 files)](../precode/vnext-r4/package/00_START_HERE.md) → [ERRATA_R4](../precode/vnext-r4/package/ERRATA_R4.md) → [R4 full candidate](../precode/vnext-r4/package/UNO_INTEGRATED_NEURAL_ORGANISM_PRECODE_CANDIDATE_vNEXT.md) → [R4 source audit](../precode/vnext-r4/package/SOURCE_AUDIT.md) → [R4 gates](../precode/vnext-r4/package/UNO_EVIDENCE_TRACEABILITY_AND_TEST_GATES.md). Содержит 20 оригиналов V01–V20 и вложенные original Astra/Grok/V22 ZIP.
- [R4.1 full inherited paper](../precode/vnext-r4/package/R4_1_INHERITED_BASE.md) и [independent engineering rechecks](../audit/r41-engineering-20261104/00_START_HERE.md).
- [vNEXT-R3 full package (13 files)](../precode/vnext-r3/package/00_READ_ME.md), включая его первоначальную формулу и ERRATA_R2/R3.
- [R5.3 source-package](../precode/r5.3/source-package/00_START_HERE.md) и NORMATIVE/01–06, Astra originals, R51/R52, individual D/X/B/M gates — **не изменены**. [Дополнительная история Astra red-team](../audit/astra-20261102/R3_FINAL_REVIEW.md).
- [Live lab journal](../../UNO_LAB_REPORTS.txt), [BENCH](../../research/uno-lab-001/BENCH.txt), [OWNER_TEACHING vs SENSOR vs ANDROID_OUTCOME](../research/OWNER_TEACHING_AND_ANDROID_EVIDENCE_20261105.md), [A52 owner review](../../research/uno-n0-07/results/OWNER_A52_FULL_400_REVIEW_20261106.md).
- [Complete 396-member owner archive inventory](../archive/OWNER_COMPLETE_WORK_ARCHIVE_INDEX_20261106.json) with exact names/bytes/SHA-256 and status for every member. [Historical owner R1–R3 Astra revisions, original math, V01–V20 combined trace, handoffs](../archive/owner-complete-work-20261106/) are preserved separately without claiming they supersede R4.

## Счёт по двум переданным ZIP (не складывать неверно)

- **R4 ZIP:** 120/120 byte-for-byte preserved under `docs/precode/vnext-r4/package/`.
- **Earlier entire Work ZIP:** 396 listed members, of which 261 exact-content duplicates of already preserved sources, 94 additional unique historical sources mirrored into Git, 25 indexed-but-not-copied items (mostly nested archive duplicates or unselected evidence) and 16 private / research-binary artifacts intentionally not mirrored. Additional 1 Git file = exhaustive inventory index.
- **New Git files total:** 180 in initial R4/R3/Astra/R4.1/agent pass + 95 in archive pass = **275**, with exact Git blob SHA verification at the corresponding integration checkpoint. Existing R5.3 and research branch files inherited unchanged.

## Почему файл может отсутствовать в дереве, но существует

The owner Work ZIP `UNO_ALL_WORK_AND_SOURCES_2026-11-06.zip` (SHA-256 `8c87ebec317f9acd8398a1ff239edfccb193c0e182e0f91ef447bcb3b26ac02b`) also contains PMB/chat history, archived APKs and duplicate nested ZIPs. A Git working tree is not a substitute for a private archive or device raw export. **Check the full 396-item index for the exact original archive path and hash before saying «missing».** Index classification `INDEXED_NOT_MIRRORED` requires explicit request for the owner bytes if needed; don't fabricate contents.

## Точные ограничения на 06.11.2026

- R5.3 G4 **PRECODE_CANDIDATE**, `OWNER_APPROVED_PRECODE=FALSE`, `PRODUCTION_CODE_AUTHORIZED=FALSE`; R4/R3 are candidate proposals, not approved baseline. O01–O08 only owner.
- No independently byte-verified full N0-07 400-row device raw capture has been established. Stage5 reconstructed CSV is present and is *not* the same as raw device export.
- A52 N0-03…N0-07 research reports exist; they do **not** establish product-quality UNO on A52. Novel tiny experimental weights existed; no validated production UNO checkpoint is established.
- R4's newly specified V14 cursor integrity, V19 post-boot outbox invalidation, and V20 one-ticket commit dedup remain `SPECIFIED_UNTESTED` in an integrated trusted Android implementation; counterexamples to historical fixtures are locally reproduced.
- No main merge, production code, GitHub Actions or destructive cleanup in this handoff. Source audits and local paper runs are not device hardware measurements.

## Mandatory agent check (before changing anything)

1. Confirm branch and commit SHA; read `AGENTS.md`, this document, all candidate originals and independent R5.3/source-package.
2. Check [per-file mirror SHA register](../precode/vnext-r4/MIRROR_SHA256.json), [original package verifier](../precode/vnext-r4/package/verify_package.py) and [independent witness](../precode/vnext-r4/package/evidence/recheck.py). Run locally; do not trigger CI.
3. For a claimed absence search both the inherited research tree and the 396-file archive index. Record `PRESENT_GIT / PRESENT_PRIVATE_ARCHIVE / UNKNOWN_RAW / NOT_IMPLEMENTED` rather than conflating them.
4. When finding conflicts, create versioned erratum with exact source path/section, evidence, counterexample and `PROVEN_LOCAL/CONDITIONAL/SPECIFIED_UNTESTED/REQUIRES_DATA/OWNER_DECISION/FAIL`; never rewrite originals.
