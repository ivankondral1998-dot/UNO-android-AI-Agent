# Матрица D01–D10, X01–X12, B01–B14 после Grok Stage 2

Ровно 10 +12+14 obligations; не переносить статусы отчёта на тесты, которые не проводились.

## D01–D10
| ID | Состояние R5.1 | Что нужно для полного закрытия |
|---|---|---|
| D01 | CANDIDATE / OWNER_DECISION | утвердить 12→14 task strata WAKE/SENSOR и quality/coverage/error thresholds; независимые task oracles |
| D02 | B2 ARITHMETIC PASS, EXPORT OPEN | собственные обученные веса, официальный export, decoded norms, выбранная family ABI, backend parity |
| D03 | THEORY SPECIFIED / DATA OPEN | licensed corpus, source rights, training, optimizer/checkpoint and held-out eval |
| D04 | NONINJECTIVITY PROVEN; exact protocol DRAFT | normative raw retrieval ABI + conflict handling, quotas, authentication, fault-injection |
| D05 | CONDITIONAL ON A_cap | owner enrollment, consent, OS permissions and STOP/transaction runtime validation |
| D06 | THEORY ONLY | independent RU-ASR/TTS/screen/WAKE/SENSOR/planning quality evaluation |
| D07 | MAC ARITHMETIC ONLY | actual A52 RAM, p95/p99, energy, thermal and offline stability |
| D08 | NCR DSL SPECIFIED / UNTESTED | safety/sandbox audit, preregistered A/B/C/D study, fresh holdout |
| D09 | ABI/BUILD DRAFT | strict local-source policy, selected binary manifests and reproducible build evidence |
| D10 | THREAT/RISK SPECIFIED | owner thresholds, security test results, fail-closed release oracles |

## X01–X12
| ID | Состояние R5.1 | Недостающая гарантия |
|---|---|---|
| X01 | CONDITIONAL | same-law prefix training/runtime yes; PL parity and owner choice absent |
| X02 | LOCAL IDENTITY | score estimator exact with observed differentiated log-prob assumptions; trained policy absent |
| X03 | CONDITIONAL | stop-before-dispatch gate; late external effects cannot be undone, real trace absent |
| X04 | DESIGN CONDITIONAL | MAY_HAVE_EXECUTED/UNKNOWN no-blind-retry; OS failure injection absent |
| X05 | ATOMICITY CONTRACT | used + receipt + newP guarded txn depends A_tx/A_fs, not Android-tested |
| X06 | B2 ABI FORMULA | quantized export and decoded norm/parity not constructed |
| X07 | PROVEN NON-EQUIVALENCE | LR rank64 does not represent all B2 functions; quality undecided |
| X08 | PROVEN COUNT | W_R adds 128(d+1) allocated parameters, trained head absent |
| X09 | ACCOUNTING UPDATED | nominal text MAC valid; no device energy guarantee |
| X10 | STATISTICAL CONDITIONAL | positive inclusion + fresh holdout; no NCR study |
| X11 | CONTROLLER SPECIFIED | per-verb Android permission/API/effect proof untested |
| X12 | OPEN | actual full trained Θ and metrics absent |

## B01–B14
| ID | Состояние R5.1 |
|---|---|
| B01 | OPEN: owner acceptance thresholds/coverage/severity |
| B02 | OPEN: lawful labelled task-balanced corpora & consent |
| B03 | OPEN: trained full Θ, frozen-row checks and independent generalization |
| B04 | PARTIAL: B2 ABI specified; real export/parity absent; LR2/H2 official ABI absent |
| B05 | OPEN: compare B2/LR2/H2 on identical quality/energy distributions |
| B06 | OPEN: A52 device measurements |
| B07 | OPEN: native Android verbs, endpoint and safe failure |
| B08 | OPEN: owner authentication, storage transactions, rollback/freshness |
| B09 | PARTIAL: exact retrieval only candidate, conflict/quarantine/retention not tested |
| B10 | OPEN: NCR sandbox/mutation/quality controlled study |
| B11 | PARTIAL: Astra+Grok+R4 reports exist, independent machine/full proof not certified; R5 changes require audit |
| B12 | RESOLVED AS ARTIFACT: final ASTRA archive found and hashed, not global math proof |
| B13 | OPEN: language, audio, screen, WAKE/SENSOR performance |
| B14 | NOT AUTHORIZED: production implementation, APK, release, merge, PRE-CODE BASELINE |

**Gate summary:** G0 requirements NOT PASS; G1 local theorems CONDITIONAL; G2 design candidates OPEN at D01/D04/D05/D09; G3 empirical NOT PASS; G4 BASELINE NOT APPROVED; G5/G6 production NOT STARTED.
