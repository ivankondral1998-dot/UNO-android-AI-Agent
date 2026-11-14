# R5.3 errata quick index (NOT the normative source)

Use complete [NORMATIVE/02](source-package/NORMATIVE/02_FORMAL_CORRECTIONS_AND_LIMITS.md) as the exact statement and [NORMATIVE/01](source-package/NORMATIVE/01_SOURCE_HIERARCHY_AND_CONTRACT_INDEX.md) for source hierarchy. This quick index does not replace their assumptions.

- W4: fixed shared mask bound c_M, full mask conditional 0.95, sparse mask c=1; adaptive threshold selector may be discontinuous. No global contraction claim.
- Memory: weighted semantic aggregate noninjective; exact recall requires [R52/02](source-package/SOURCES/R52/02_MEMORY_CONTRACT.md), with complete snapshot/provenance/consent and COMPLETE/CONFLICT/TRUNCATED/UNKNOWN/DENIED semantics.
- WAKE: metadata-only w_wake not acoustic KWS; SENSOR requires typed units, TTL, trusted oracles. Required/Optional choice belongs to owner.
- STOP: can block dispatch before linearization but not revoke external in-flight OS effects. No blind retry. Receipt/readback does not prove causal effect.
- Strict offline: Android app INTERNET permission alone insufficient if SAF third-party provider fetches remote content.
- Masks: 241 cyclic-prefix vs 65535 arbitrary nonempty at d=1024, not equivalent. Real device energy and trained model quality are unmeasured.
- Quality: locked test, pre-registered thresholds and licensed data required. NCR-EVO is research, not proven self-regeneration.

Before implementation read full Astra_01–12, R52/01–05, all 80 individual gates. Current G4 is not owner-approved, G5 production code not authorized.
