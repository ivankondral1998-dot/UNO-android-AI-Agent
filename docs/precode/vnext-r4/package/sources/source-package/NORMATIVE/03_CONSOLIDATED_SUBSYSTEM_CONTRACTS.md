# R5.3 — маршрут по полным контрактам: не терять формулы Astra

**Использовать этот документ вместе с указанными файлами `SOURCES/ASTRA_CURRENT/` и R52.** В отличие от короткой R5.3 Grok, здесь не утверждается, что одной строкой заменены десятки формул. Если пункт неоднозначен — пометить `OPEN`, не «додумывать» код.

## A. Full system transition и causal time

- ASTRA_01 §1: `S1` весь `X=(w,tau,S,T,R)`, `S=(v,Theta,s,g,beta,P,MemStore,Q,Hctx,U)`, `T=(nu,e,stop,owner,cap,L,D)`. Resource queue bounds, replay/timer priorities, `K_race` (S2), `delta` (S3), outbox/linearization. Без этих предпосылок короткая R5.3 формула `K_race` неполна.
- ASTRA_01 §2: canonical TEXT/AUDIO/IMAGE/SENSOR/OS envelopes, padding, missing masks, full audio session serialization, bounded buffers.
- ASTRA_01 §3: `S4` z0→memory query→r→z→h0; `S5` recurrent shared F; `S6` resource-conditioned prefix selection + halting/admission; §5 goal DSL; §§6–7 readback and endpoint predicates.
- W4 claim заменён `NORMATIVE/02`; старый `c=.95^K` для sparse заменять запрещено.

## B. Weight geometry, ABI, variants

- ASTRA_02 §2 официальный список форм: `V32768`, `m128`, `chi4`, `J2`, `b64`, `A128`, `H902`, `n_b=d/64`. `ASTRA_SUPPORT/evidence/tensor_manifest_d1024.json` содержит **198 tensor descriptors**. Для d1024 allocated slow `55,451,639`, free `55,125,689`, frozen `325,950`; fast P allocated `128*d` отдельно, только `21*d` update-eligible.
- W2 analytical count: `V*d + 951*d + 2*d*d + 4*m*d + J*(2*chi*d*d+chi*b*d+(chi+1)*d) + H*(d+1)+V+(d/b)*(2*d+5)+33`. Frozen `318(d+1)`. Другие d см. ASTRA_02 §3.
- ASTRA_02 §4 альтернативы LR2/H2 — **кандидаты**, не эквивалентны B2. Разделы FP16/mixed INT8 ABI, quant/dequant certificate, decoded-norm и tensor padding сохранить целиком; quantized/export model не существует.

## C. Full training — L3a/L4/L5, а не один J_base

- ASTRA_03 §1 полный перечень supervised losses для text/goal/ASR/TTS/vision/action/obs/outcome/online memory/belief/risk/value/conf/wake metadata/halt/retention.
- §1a conditional coverage + terminal loss L3a с denominators `pi_j`; запрет бесплатного отказа; для WAKE/SENSOR strata дополнение R52/03, всё ещё proposed until owner decision; 12→14 — **новая 14-row candidate battery**, не доказательство идентичности старым 13 V2.2.
- §2 full BPTT, CTC, keys/values, ∂z; §3 REINFORCE score estimator and frozen P0; §4 Adam projection, TBPTT bias, QAT/STE caveats; §§5–7 права на данные, split, curriculum, training compute.
- `L_wake` Astra metadata-only; acoustic path R52/03 требует будущих data labels/device test. Новое `L_sensor` только proposed.

## D. Memory + P

- ASTRA_04 §1 storage, replay, integrity; §2 projected P update, exact one-sample descent assumptions; §3 retention and interference; §4 transaction/migration; §5 distinguish file recovery vs known-event replay vs functional search.
- R52/02 precise deterministic retrieval replaces lossless interpretation S4; raw payload is never equivalent to neural aggregate. Full snapshot/revocation/ABA/TTL tests are mandatory during implementation.

## E. Controller, Android, DSP, resource ledger

- ASTRA_05 §1 threat model assumptions A_cap/A_tx/A_fs, §2 action catalogue + exact verb semantics, §3 DSP/CTC/TTS, §4 MAC ledger including non-F work, §5 RAM/IO, §6 latency/energy/peak memory and admission. Do not replace the ledger with a 53MiB weight-file claim.
- Legacy OwnerGate *name and implementation* are **not** a UNO requirement. Trust boundary itself must be verifiable and defined before coding; selected auth/enrollment protocol remains owner/security decision, not a proof of trained intelligence.
- SAF unknown network-backed provider violates strict whole-flow offline; local-only policy proposed R52/04.

## F. NCR-EVO

- ASTRA_06 §1–§7 complete bounded DSL, evaluator isolation, archive QD, generations and exact statistical conditions. Example generations are hand-derived, not an actual autonomous evolving model. Equal-budget independent holdout test not run; cannot call beneficial self-regeneration PASS.

## G. Engineering and traceability

- ASTRA_07 full D01–D10 and ABI/2, ASTRA_08 theorems and counterexamples, ASTRA_09 historical M01–M44; ASTRA_10 critic and ASTM R1–R3; ASTRA_11 implementation blueprint **for future approved coding**, ASTRA_12 data and hardware unknowns.
- `NORMATIVE/04` maps *individual* D/X/B/M, not grouped rows. `NORMATIVE/05` separates owner decisions required for G4 from tests executed during G5/G6. Verified code, validated weights, A52 energy, license data acquisition and locked test cannot be faked by the pre-code package.
