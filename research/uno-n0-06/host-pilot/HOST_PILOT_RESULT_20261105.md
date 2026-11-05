# UNO-N0-06 — isolated synthetic host pilot, executed 2026-11-05

**Status:** HOST_TESTED_SYNTHETIC_ONLY. This is not a Samsung A52 replay, Android test, physical learning benefit, proof of one complete organism, or production UNO. Source of original N0-05 Java baseline: unchanged `NeuralGraph.java`, SHA-256 `ec4003a4c40d4fb5c1e98356f0339c98ee58173952188900f57bc26a8b60ebac`, copied byte-identically from the N0-05 source bundle. Synthetic fixture frozen in GitHub *before* the pilot at commit `8362c70ba1ff360821762a8a5ce4bf9a97746390`, file `research/uno-n0-06/PILOT_FIXTURE_FROZEN_BEFORE_RUN_20261105.md`. Canonical owner requirement at `docs/research/OWNER_TEACHING_AND_ANDROID_EVIDENCE_20261105.md`.

## Run environment and method

- Host Linux, OpenJDK 21, javac/java with N0-05 original Java graph and compile-only JSON stubs; no Android APIs, no internet, no action execution.
- Exact fixed xorshift32 seed `0x05EED006`, 160 synthetic categorical next-event predictions; first 80 train, second 80 frozen evaluation; source class changes 40 in 160.
- Comparators on the same synthetic sequence: original N0-05 fixed algorithm; persistence; original N0-05 numeric Markov; C1 candidate context ledger with per-label observation counts, threshold support>=3 and unique-majority lead>=2. The C1 counts are numeric and must NOT be described as absence of all numbers, only no learned numerical synaptic weights in this isolated approach.
- Two independent executions produced byte-identical stdout; portable self-contained run (bundled baseline code and stubs) also reproduced identical output. All assertions passed.

## Actual frozen results (80 prospective test events)

| Algorithm | Correct / 80 | Difference vs persistence |
| --- | ---: | ---: |
| N0-05 original graph | 62 | +1 |
| C1 counted categorical context candidate | 66 | +5 |
| Previous-label persistence | 61 | reference |
| N0-05 numeric Markov | **67** | +6 |

N0-05 graph: 5 predictions differ from persistence, 3 gains/2 losses; origins NEURON=5, CONTESTED=75, NO_MATCH=0. C1: 12 different predictions, 8 gains/3 losses. C1 improves N0-05 on this one artificial trace by 4, but is **worse than Markov by one** and cannot claim superior architecture or statistically generalizable learning. This negative comparator result is preserved.

## Contract tests

- **Counterexample reproduced against actual N0-05 Java:** same-context synthetic conflicting labels create a coarse node, then a more-specific node, then a contested specific node. Five subsequent label-matching training outcomes do **not** restore eligibility. N0-05 origin remains CONTESTED with 2 nodes / 1 contested rule. This is a *local exact-context behavior*, not a proof of universal permanent lockout.
- **Human corrections:** one physical observation plus two separate owner teaching assertions (one explicit correction) remain separate in a shared append-only evidence ledger. No owner label edits past sensor readings; permission grants = 0.
- **Android mock readback contract:** seven simulated invalid scenarios, including no capability, STOP before dispatch, stale, wrong operation, missing postcondition, MAY_HAVE_EXECUTED and dispatch-only, were rejected as positive experience. One fresh and matched simulated postcondition admitted. This tests code predicates only, **NOT** source authenticity or Android native readback on a phone.

## Evidence and scope

Test output SHA256 `1259251bcbeb2e5ae5135562b19346917097be75dc4112caeca48d4c739acb68` (identical across original two runs and portable replay). Pilot Java source SHA256 `ac59ca1916d125f48f3e2c60d17697952f95cc4c2eaaaa6120b3ce470fe48963`. Portable run.sh SHA256 `02f589ea60d88ba4614c9e734197594d97edd5df07cc53d5c2c74ca0903951ee`. Full 80-row evaluation lines, source and original baseline are bundled in this research artifact. No N0-05 original code or frozen prior results changed, no GitHub Actions, no production adoption, no licensed-data assertion, no device power/PSS measurement.

**Conclusion:** The old contested fallback path is reproduced as a failure mode; a quantitative alternative can affect predictions in a locked synthetic pilot, but Markov remains better on this stream. Owner feedback and OS receipts can be kept separate at the level of a small MOCK provenance contract. They are not yet full UNO learning and require stronger experiments and actual native readback before any success claim.
