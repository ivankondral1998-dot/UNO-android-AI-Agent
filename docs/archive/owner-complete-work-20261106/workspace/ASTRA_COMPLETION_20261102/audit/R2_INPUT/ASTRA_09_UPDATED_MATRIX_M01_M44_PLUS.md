# ASTRA 09 — исходные M01–M44 и новые обязательства

Формулировки и исходные статусы всех 44 строк сохранены. Новое evidence относится к исправленному B2 и не объявляет исходную B1 безошибочной. PASS — только конкретное доказанное/условное формальное свойство; SPECIFIED в новых строках не заменяет эмпирический PASS. NOT_TESTABLE означает «не проверено данной работой», а не невозможность будущего опыта.

| ID | Исходное утверждение (сохранено) | Статус знания | Вердикт | Закрывающее evidence / предел B2 |
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

## Новые математические и инженерные обязанности

|ID|Обязанность|Статус|Вердикт|Evidence / закрытие|
|---|---|---|---|---|
| N45 | Причинный clock не перескакивает очередь/deadline | CONDITIONAL | PASS | 01 S2/S3, поддержка race; A_progress |
| N46 | Compute snapshot/version не смешивается между ticks | SPECIFIED | PASS (контракт) | 01 workCookie/COW; device implementation pending |
| N47 | h_issue определяется после полных args | PROVEN | PASS | 01 canonical re-encoding; 11 B05; не injectivity |
| N48 | Наблюдаемость R отделена от Y | PROVEN | PASS | S7,08 T7 probability factorization |
| N49 | q_R/q_Y откалиброваны на всех будущих задачах | REQUIRES_DATA | NOT_TESTABLE | 03/12; shift и MNAR не устранены |
| N50 | Один закон mask/depth train/runtime | SPECIFIED | PASS (контракт) | S6 sampled prefixes/hazards; no silent argmax switch |
| N51 | Global event contraction следует из inner F | REJECTED | FAIL | W4,08 T2; требует других bounds |
| N52 | B2 и альтернативы имеют точные counts | PROVEN | PASS | W2/W3 allocated/free; arithmetic_v2 и shape inventory |
| N53 | Actual INT8 artifact сохраняет нормы/quality | REQUIRES_DATA | NOT_TESTABLE | 02 export protocol; weights absent |
| N54 | Все loss/target/gradient paths заданы | CONDITIONAL | PASS | 03; availability of labels, P=0 offline objective, terminal task loss |
| N55 | TBPTT/STE точны для полной истории/rounding | REJECTED | FAIL | 03 §3/4, отсутствует нужная event contraction |
| N56 | CTC/STFT/TTS feedback и размеры согласованы | SPECIFIED | PASS (контракт) | 03/05; B07–B10, no speech quality claim |
| N57 | P local descent и realized-loss regret выведены | PROVEN | PASS | 04 P2/P3 при указанных assumptions |
| N58 | Memory insertion/expiry/eviction/migration определены | SPECIFIED | PASS (контракт) | 04/07; finite refs, raw replay or quarantine |
| N59 | Crash unresolved effect не теряется при reset | CONDITIONAL | PASS | 04 durable PREPARED/reconciliation; A_fs |
| N60 | P128 гарантирует нулевую вероятность collision | REJECTED | FAIL | 05 birthday bound; exact counter only separate assumption |
| N61 | Полный resource formula включает все paths | SPECIFIED | PASS (контракт) | 05 +03; named unknown backend terms, not numeric PSS |
| N62 | Capacities гарантируют отсутствие queue overload | REJECTED | FAIL | 05 service/arrival inequality; finitequeue alone insufficient |
| N63 | Android capability/endpoint/threat matrix задана | SPECIFIED | PASS (контракт) | 05 closed24verbs/restDENY, API-specific UNKNOWN |
| N64 | На A52 доступно всё задуманное API/readback | DEVICE_BLOCKED | NOT_TESTABLE | 12 device probes; OS restrictions explicit |
| N65 | NCR typed DSL/surrogate/fidelities/quotas завершены | SPECIFIED | PASS (контракт) | 06 E3–E5; hard validity != correctness |
| N66 | IPW исправляет arbitrary censoring/holdout leakage | REJECTED | FAIL | 06/08 T9; only fixed observed-label risk |
| N67 | Equal-total-cost A/B/C/D power/stop заданы | PROVEN/SPECIFIED | PASS | 06 E5/E6:9457 для δ0;26268 для practical δ.02; additive/peak раздельно |
| N68 | D01–D10 имеют связанный precode contract | SPECIFIED | PASS (документ) | 07,11,12; independent audit may limit verdict |
| N69 | G2 engineering inputs фактически готовы | REQUIRES_DATA/DEVICE_BLOCKED | FAIL (gate) | нет licensed corpus, coefficients, hashes, approved thresholds |
| N70 | Полный build/training/release DAG и ABI определены | SPECIFIED | PASS (контракт) | 07/11; version/data-dependent artifacts pending |
| N71 | Права на datasets/voice/third-party assets подтверждены | REQUIRES_DATA | NOT_TESTABLE | 03 manifest; no license grants inferred |
| N72 | Frozen final files прошли независимый reread | REVIEW_REQUIRED | PENDING | ASTRA_10 and audit/FINAL_REVIEW.md, fill only after review |
| N73 | Новый production code/Actions/repo changes не сделаны | OBSERVED_SCOPE | PASS | 00 actual operations log; arithmetic/doc scripts only |
| N74 | Полный интеллектуальный/коммерческий UNO доказан | REQUIRES_DATA | FAIL (admission) | G0/G2/G4/G5/G6 не закрыты; не трактовать как impossibility |

В исходной матрице по-прежнему 30 PASS, 9 FAIL, 5 NOT_TESTABLE. Это не вероятность правильности и не процент готовности продукта. Новые строки намеренно добавляют реальные FAIL и открытые инженерные gates. Итог независимого аудита может понизить статус исправимой обязанности; тогда исправление и повторное чтение обязательны.

## Исправления R1, подлежащие финальному перечитыванию

|ID|Утверждение|Статус|Вердикт|Evidence|
|---|---|---|---|---|
|N75|Внутренний mask sampler не содержит terminal q0|SPECIFIED|PASS (контракт)|01 S6: только q≥1, один admission; не гарантия качества|
|N76|Отказ/неполный output имеет terminal loss|SPECIFIED|PASS (контракт)|03 L3a; UNKNOWN не получает fake Y0|
|N77|Allocated/free/frozen параметры разделены|PROVEN/SPECIFIED|PASS|02; P_free=P_alloc−318(d+1), E3–23|
|N78|Exact-gradient claim ограничен fixed-P objective|CONDITIONAL|PASS|03 P=0; TBPTT/STE biased; adaptive runtime отдельно|
|N79|Practical power использует Δ−δ=.03|CONDITIONAL|PASS|06 E6;26268 при α_each.025,β_each.1|
|N80|Peak RAM/disk не суммируются как work|PROVEN/SPECIFIED|PASS|05/06/08: live allocation sup; hardware отсутствует|

Исторические R1 FAIL не удалены: audit/R1_REVIEW.md и frozen R1_INPUT. Эти строки оценивают конкретные исправления, а не отменяют предыдущие контрпримеры.
