# R5.3 — 80 индивидуальных obligations, без группового скрытия

**Основание:** `SOURCES/R51/05_D_X_B_GATE_MATRIX.md`, полная `ASTRA_07` и `ASTRA_08`, исходные M01–M44 из `ASTRA_09`. Ни один неподтверждённый аппаратный, обучающий или владелецкий пункт не превращён в PASS. Для D/X/B индивидуальные статусы здесь являются сохранённой оценкой R5.1 с уточнениями R5.2/R5.3, а не результатами нового полного автоматизированного теста.

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


## Адресные уточнения R5.2/R5.3 к этой таблице

- D01: предлагаемая четырнадцатистратная battery добавляет отдельно acoustic WAKE и SENSOR к двенадцати Astra; исходная 13-row battery V2.2 не автоматически равна новой 14-row. `OWNER_DECISION` остаётся.
- D04/B09: contract R52/02 более точный, чем R51: `CONFLICT` только после полного snapshot scan и без exceeding k; иначе `TRUNCATED`/`UNKNOWN`. Бумажная семантика `CANDIDATE`, не Android-tested.
- D05/B08: owner identity/enrollment, source-auth, consent expiry — внешний Android security stage. Перенос Jarvis OwnerGate не предписан.
- D07/B06: отсутствие измерений A52 не является логической ошибкой W2 MAC; device viability не подтверждена.
- X01: 241 vs 65535 — **не эквивалентность**; принять политику/сравнить качество, не обещать convergence adaptive.
- X06/B04: реального quant export или parity не было; Astra B2 tensor manifest даёт shape/count only.
- X09: 128-token full event MAC ≠ F+vocabulary lower subtotal; ни один MAC не является Joules.
- X12/B03: trained full Theta absent, поэтому качество и ability не доказаны.
- B11: ограниченные self/audit calculations, не формальный сертификат всех доказательств.
- B12: source artifact exists and source hashes verified; это не mathematical signoff.
- B14: `OWNER_APPROVED_PRECODE=FALSE`, production unauthorized.

## M01–M44 — исходный полный индивидуальный реестр (история, не blanket PASS)

Все строки сохранены **без изменения статуса исторического утверждения**. Особенно M14, M16, M18, M25, M27, M32, M36, M43 имеют исторический FAIL/REJECTED. Исправления новых контрактов не превращают ложные старые универсальные утверждения в истинные.

| ID | Историческое утверждение | Класс доказательности | Статус в исходной матрице | Источник |
|---|---|---|---|---|
| M01 | Развести граф, геном, trusted contracts, Θ/Φ_R/Φ_S/Θ_M | PROVEN | PASS | 01/02: S1 и W2 |
| M02 | Полностью прочитать NCR-EVO оригинал, сохранить provenance | PROVEN | PASS | 00 и SOURCE_HASHES, полный original |
| M03 | Определить наблюдения, цели, missing/unknown | PROVEN | PASS | 01 §2/5, 04 |
| M04 | Определить частично наблюдаемый мир и kernel | CONDITIONAL | PASS | 01 S2/S3 race/outbox; T1 |
| M05 | Все веса имеют формы, counts и роль | PROVEN | PASS | 02 полный реестр H902; allocated/free и frozen rows |
| M06 | Параметры d=512/1024/1536/2048 посчитаны | PROVEN | PASS | 02 W2 и arithmetic_v2.json |
| M07 | Выбранный d=1024 достаточен для полноценных задач | REQUIRES_DATA | NOT_TESTABLE | 12: нет обученной модели/holdout |
| M08 | Минимально жизнеспособный размер установлен | UNDETERMINED | FAIL | 02 feasible-set; 12 non-identification |
| M09 | Новые веса фактически обучены | REQUIRES_DATA | NOT_TESTABLE | 03: обучение не запускалось |
| M10 | Никакие старые веса не обязательны в Θ | PROVEN | PASS | 02: новые Θ, без JNO |
| M11 | δ тотальна для success/failure/unknown/cancel/stale/STOP/denied/timeout/restart | CONDITIONAL | PASS | 01 фазы/producers, T1; A_progress |
| M12 | Типовая корректность всех матричных произведений | PROVEN | PASS | 01–04: все формы и L4 |
| M13 | h,s,β и P bounded | PROVEN | PASS | 08 T2; идеальная арифметика |
| M14 | Исходный residual с clip всегда сходится | REJECTED | FAIL | 08 T2: двухточечный цикл |
| M15 | Fixed F contractive при norm bounds | CONDITIONAL | PASS | 02/08 T2: фиксированный z |
| M16 | Sparse inner-loop сходится при любом выборе масок | REJECTED | FAIL | 08 T2: всегда inactive coordinate |
| M17 | Fair common schedule сходится при фиксированном z | CONDITIONAL | PASS | 08 T2: common fair sweep |
| M18 | Полный агент стабилен/сходится при любой среде | REJECTED | FAIL | 02 W4; меняющаяся среда |
| M19 | Стоимость selector, masks, heads, DSP отделена | PROVEN | PASS | 05 R5/DSP/traffic, 03 L6/L7 |
| M20 | Алгоритмический work-budget соблюдается | CONDITIONAL | PASS | 05 admission; 08 T5, calibrated upper costs |
| M21 | Реальные RAM/PSS, joules, latency A52 подтверждены | REQUIRES_DATA | NOT_TESTABLE | 05/12: нет measurements A52 |
| M22 | Idle не означает нулевую энергию ОС | PROVEN | PASS | 05 R6: P_idle/controller |
| M23 | Права не зависят от Θ,P | CONDITIONAL | PASS | 05/08 T6: A_cap |
| M24 | STOP запрещает ещё не linearized dispatch | CONDITIONAL | PASS | 01/05 linearization; A_cap |
| M25 | STOP отменяет уже возникший физический эффект | REJECTED | FAIL | 08 T6: already dispatched effects |
| M26 | Stale/replay не меняют P/verified knowledge | CONDITIONAL | PASS | 04/05: A_tx; P128 условно no collision, COUNTER при A_gen |
| M27 | PR #3 уже обеспечивает safe snapshot rollback | REJECTED | FAIL | исходный PR3/source; 08 T6 trace |
| M28 | Crash-safe persistence определена | CONDITIONAL | PASS | 04 PREPARED/atomic commit/reconciliation; A_fs/A_tx |
| M29 | Android storage/trust-boundary реализуют A_fs/A_cap | REQUIRES_DATA | NOT_TESTABLE | 05/12: будущие device fault tests |
| M30 | Unknown/denied/timeout не превращаются в y=0/1 | PROVEN | PASS | 01/03/04: R и Y различаются |
| M31 | Текст success не является receipt | PROVEN | PASS | 01/05: native source/token |
| M32 | Verified completion доказывает причинный effect | REJECTED | FAIL | 08 T7: interference counterexample |
| M33 | Offline objectives покрывают все Θ | CONDITIONAL | PASS | 03 L3a–L5, Θ_free, paired memory; при наличии targets |
| M34 | Градиенты smooth-path и discrete-selector разведены | PROVEN | PASS | 03 exact estimator vs TBPTT/STE explicitly biased |
| M35 | Online L2 — projected gradient с локальным descent | CONDITIONAL | PASS | 04 P1/P2 при frozen h/current P |
| M36 | Online learning улучшает все будущие задачи без forgetting | REJECTED | FAIL | 04/08 T4 conflicting labels |
| M37 | Контрольная монотонность возможна на finite deterministic set | CONDITIONAL | PASS | 04 fixed deterministic fixtures only |
| M38 | Energy/success определена при нуле успехов и без отказного exploit | PROVEN | PASS | 05/07 issued tasks, coverage; B25 |
| M39 | NCR-EVO меняет алгоритмы; 3 поколения вручную | PROVEN | PASS | 06 c0–c3, induction и current reference |
| M40 | IPW unbiased finite-pool risk при E1 | CONDITIONAL | PASS | 06 E4; fixed loss, observed labels; audit sample separately |
| M41 | NCR-EVO статистически превосходит A/B | REQUIRES_DATA | NOT_TESTABLE | 06 E6: эксперимент не запускался |
| M42 | Генератор не может изменить trusted contracts | CONDITIONAL | PASS | 06 capability-free lab; A_cap |
| M43 | Regeneration восстановит любую стёртую функцию | REJECTED | FAIL | 04/08 T8 erasure non-identification |
| M44 | Future implementation contracts и математические oracle заданы | PROVEN | PASS | 07/11 contracts and preserved O1–O14 plus B01–B26 |

