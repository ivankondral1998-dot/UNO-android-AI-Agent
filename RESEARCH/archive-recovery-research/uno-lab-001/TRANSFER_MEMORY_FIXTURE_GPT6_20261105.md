# UNO-LAB-001 — verified peer transfer manifest (2026-11-05)

Read BENCH.txt and the latest UNO_LAB_REPORTS.txt first. This is a source/evidence index, NOT a second queue.

All five files below exist in the research handoff branch. GitHub blob SHA-1 of each fetched file was checked against the Git blob of the actual local file, proving byte identity. SHA-256 is of those same original local bytes.

| File (relative to research/uno-lab-001/) | SHA-256 | Git blob SHA-1 |
|---|---|---|
| UNO_LAB_001_MEMORY_FIXTURE_AUDIT_GPT6_20261105.md | 4bd19a55040c92d64c2f9ba4185634214b19586f41f897e1243280a56fa4d4b7 | b6f8be217f1731f72cba557a288a4dafb64bd778 |
| uno_r53_memory_finite_bound_audit_gpt6.py | 0f16580dee7ba25c618dfd69d40b656062b7a2f74f61a207fc8abe7a1cf80b93 | 6a8c48920fdc4f378c0795d6a9558acbb48d7c21 |
| uno_r53_memory_finite_bound_audit_gpt6_run.json | 53be06d958de4ad4654c89d1df24c8b62b82cda5ac50781a5578acaa75a3d03b | 19347b931a4a14ecf7b921df481536e2dd485b4a |
| uno_memory_flip_ambiguity_gpt6.py | 4bac52f4038093f691c2451170e0c678fd92ae5d6731efd185b7be39466fc7a2 | 4e2f37468af255d2063b752e30491af90771e60f |
| uno_memory_flip_ambiguity_gpt6_run.json | 27fd07515e20c25d6a3c0592d27f2abb01d821085990f352059bb3e0d3995a4d | 76452c5d55182f5ff728c49ab8d3ce75700f6f26 |

Locally run: Python -m py_compile for both scripts, both executables rerun; stdout identical byte-for-byte to both JSON files.

Read the complete Markdown audit for qualifications:
- Half-flip 32/64 collision is **unidentifiable**, not a failed generalization measurement.
- Synthetic unit-value keys exceed legal tanh key bound under row-L1 2: abs(key_i) <= tanh(2) < 1.
- Conditional four-item toy q>=0.9 upper flip count 25 for unit keys, 24 for optimistic capped query/key amplitude.
- At 4096 memory slots, dilution can lower old toy q from ~0.982 to ~0.565 even without changing stored old keys.
- Full ASTRA F, trained weights and Android are NOT validated; no owner-approved learning design.

Suggested independent peer actions: replay both scripts and compare SHA-256; challenge tanh/key bound, row caps and retrieval assumptions; run a nonambiguous prelocked test distribution and an old/new retention test across memory loads, with no weight training.
G4 PRECODE CANDIDATE; G5 not approved; OWNER_APPROVED_PRECODE=FALSE; PRODUCTION_CODE_AUTHORIZED=FALSE.
