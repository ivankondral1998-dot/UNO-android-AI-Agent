> **COMMUNICATION OVERRIDE — 2026-11-06:** [Владелец потребовал простых, коротких и содержательных ответов](decisions/2026-11-06_OWNER_COMMUNICATION_RULES_V1.md). Первым сообщать результат; не раздувать переписку; факты, ограничения и проверяемость сохранять.

# ACTIVE TASK OVERRIDE — 2026-11-06

**Current instruction:** [2026-11-06_ACTIVE_AGENT_RULES_V2.md](decisions/2026-11-06_ACTIVE_AGENT_RULES_V2.md) and [weight comparison](research/2026-11-06_WEIGHT_FAMILY_COMPARISON.md) supersede the old G4-only next-task instructions below. Production code authorized; do not block on O01–O08. Implement and test, compare candidates fairly; do not train weights without separate authorization.

---

# CURRENT_TASK — UNO G4, 2026-11-02

## Current verified result
The immutable 64-file R5.3 composite source package is mirrored verbatim under [precode/r5.3/source-package/](precode/r5.3/source-package/): 61 text files with post-upload Git blob SHA verification and 3 binary ZIP archives whose Git blobs matched their original SHA; check [SOURCE_PACKAGE_IMPORT_MANIFEST.json](precode/r5.3/SOURCE_PACKAGE_IMPORT_MANIFEST.json).

Main branch untouched. This is a **documentation preparation** milestone, NOT an owner-approved specification.

## Next proper task (no invented implementation)
1. Evaluate architecture decisions O01–O08 based on full NORMATIVE/05, with explanation of implications to the owner; do not choose for them.
2. Review any remaining paper consistency issues: full learning and memory contracts, mask/adaptive restrictions, WAKE/SENSOR acceptance criteria, offline SAF, authority.
3. Freeze test definitions/quality floors before future experimentation; label missing data or hardware as REQUIRES_DATA.
4. Prepare an explicit owner G4 approval record only *if* the owner gives approval; G5 code authorization is separate and remains absent.
5. If agent notices a conflict, open candidate erratum with exact source path/section, counterexample and gate status. Do not quietly edit historical source-package.

Disallowed without owner permission: production code, model training, repo cleanup/deletion, GitHub Actions, main merge, implied approval. Repository docs and read-only checks are permissible.
