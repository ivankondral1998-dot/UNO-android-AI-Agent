# ASTRA 11 — точный будущий порядок реализации и оракулы

**Сейчас не исполнять.** Документ не разрешает новое ядро, production training, APK, CI, Git Hub Actions, push/merge или изменение репозиториев. Он задаёт следующий этап после закрытия G0–G4 и явного разрешения владельца. В этой работе выполнялись только чтение, документирование и независимая арифметика.

## 1. Модули без второго интеллекта

|Модуль / артефакт|Вход → выход|Формула / проверяемое обязательство|
|---|---|---|
|spec/schema-registry|versioned bounded records→typed values/error|S1, ABI07; lengths checked before allocation|
|data/canonicalizer|licensed raw→causal examples/splits|03 manifest, DSP05, no leakage|
|math/reference|Θ,state,event→bounded neural result|S4–S7,W2,L4; нет OScapability|
|training/joint|dataset+spec→newΘ/checkpoint|L3–L7, all tensor gradients, compute ledger|
|training/export|Θ→weightsABI+decoded norms/parity|W2/W3, quantization02; no hidden tensor|
|runtime/worker|immutable manifest+work snapshot→proposal/state|actual conditional kernel skips, finite quotas|
|runtime/controller|typed proposal+current owner/OS state→ticket/evidence|S2/S3, phases01, A_cap/A_tx|
|runtime/persistence|commit records→atomic snapshot/reconciliation|P1,04, freshν05|
|android/io|mic/screen/sensors/native queries→typed source observations|05 permissions/DSP/endpoint semantics|
|android/ui|owner input/confirmation/STOP→trusted controller requests|digest-bound scope, no neural consent|
|research/ncr|bounded AST pool→reviewable candidate evidence|E3–E6, capability-free, no auto-update|

Единый worker содержит общий F и Θ для всех modalities; controller и IO — системные границы, не автономные reasoning agents. Никаких Brain Port/Bridge/cloud dependencies добавлять нельзя.

## 2. Строгая последовательность стадий

1. **S0 — требования.** Утвердить task battery, quality/risk/resource thresholds07 до просмотра test. Получить source rights, точный device inventory и training budget. Результаты: task_contract, dataset_rights, device_inventory. Ни один обязательный класс функций не исключать молча.
2. **S1 — ограниченная калибровка.** После разрешения измерить shapes/DSP/IPC/storage primitives05 без организма и production weights. Результат: primitive cost table с uncertainty intervals, peakPSS, thermal/isolation/readback evidence. Если полной feasible configuration нет, вернуть конкретное нарушенное неравенство.
3. **S2 — constructor ABI.** Зафиксировать выбранное семействоW2/W3, tokenizer algorithm, DSP conventions, serialization и toolchain hashes. Дляd1024B2 перечислить198slow tensors, fastP отдельно. Проверить counts, offsets, roundtrip и ресурсный ledger.
4. **S3 — reference после разрешения.** Реализовать pure math01–04 безOS capabilities. Проверить exact logic, FP64 reference, gradients вне недифференцируемых границ. Для каждого свободного trainable tensor (с masks02; frozen rows и moments обязаны оставаться0) должен существовать валидный размеченный batch с соответствующим gradient path; отсутствие данных не маскировать формальным coverage.
5. **S4 — обучение новых весов.** Выполнить03T0–T4 в утверждённых пределах данных/compute. Сохранить все trials, отрицательные результаты и learning curves. Locked test открывается только после final freeze. Малый классификатор не заменяет12strata07.
6. **S5 — export/parity.** Проверить реальные decoded norms, погрешности FP32/FP16/INT8, argmax margins и фактический пропуск kernels. INT8 failure требует reproject/retrain либо feasible FP16; без этого export отклоняется.
7. **S6 — trusted controller.** Fault injection для STOP/replay/crash сначала с test adapters, затем наA52. Требования: нет unauthorized dispatch/stale learning, сохранены state invariants. Exactly-once физического эффекта не обещать. Вредоносные worker messages не должны обходитьgate.
8. **S7 — полный Android цикл.** Проверить RU voice/text/screen/plans/TTS/M/P, offline operation, heat/idle/process death. Все quality/resource/license/security gates обязательны; неопределённые результаты остаютсяUNKNOWN.
9. **S8 — отдельный NCR-EVO.** Только разрешённый эксперимент06A/B/C/D при равных полных расходах. Продвижение кандидата возвращает его наS2/S5/S6/S7 и независимый review.
10. **S9 — решение о выпуске.** Владелец рассматривает evidence/SBOM/reproducible local build и manual rollout. Подпись/установка после разрешения; GitHub Actions не использовать.

## 3. Mathematical and engineering oracles

Исходные O1–O14 сохраняются в неизменённом корпусе `sources/02_ORIGINAL_WORK_V1_1/09_CODEX_IMPLEMENTATION_CONTRACT_LATER.md`. O4 относится к своим ε=.01,η=.2 и остаётся вернымfixture; defaultsB2ε1,η.01другие. Новые oracle не запускались, это точные specification tests.

|ID|Вход / процедура|Ожидаемый результат|
|---|---|---|
|B01 tensor sum|суммировать 198shape products d1024|55,451,639; Pfast131,072 отдельно|
|B02 causal clock|deadline вτ+1, external arrival вτ+2|deadline обработан первым; поздний receipt STALE|
|B03 same timestamp|STOP,READBACK одинаковоеτ|STOP имеет приоритет; P unchanged|
|B04 snapshot tick|COMPUTING наMversion3; передtick2 commit создаётM4|tick2 читает прежнююM3; old work cookie cannot publish after goal change|
|B05 args trace|одинаковый verb, different canonical args|trace frozen **after** кодирования всех args; no assertion that h is necessarily different|
|B06 censoring|100eligible attempts,10known TRUE,90UNKNOWN|observability labels:10ones/90zeros; outcome:10ones/90masked; нет ложных90FALSE|
|B07 CTC order|path[a,blank,a] /[a,a]|aa /a respectively|
|B08 framecount|N=0,1,160,161,160000samples|NO_AUDIO;F1,1,2,1000|
|B09 TTS feedback|257magnitudes→fixed mel transform|80values; W_audio input width80|
|B10 normalizedOLA|waveform,STFT→ISTFT without magnitude alteration|reconstruct valid support within FFT error bound; crop/padding05|
|B11 P default|h=1,p=l0=0,y1,ε1,η.01,λ.001|q=.5,p′=.0025; row cap не активен|
|B12 no-label update|B11 сUNKNOWN/STOP/replay|exactP unchanged|
|B13 P counterexample|h1,oldy0,newy1|новая BCE уменьшается, старая растёт; never zero-forgetting PASS|
|B14 norm export|decoded A row-L1=1.02,B=.90|product.918; нарушает γdeploy=.9→reject even если FP32 certificate ранее прошёл|
|B15 quant argmax|topgap≤2ε_l|no guaranteed parityclaim; report/measure disagreement|
|B16 cached recurrence|samez,Θ,mask; comparecached Czvsuncached|same ideal mathematics; bounded floating difference; MAC79,691,776atd1024K8|
|B17 sparse execution|q=nb/4|число вызовов inactive A/C/B kernels=0, not just zero final outputs|
|B18 bounded queues|1024headers+new ordinary input|BACKPRESSURE; STOP latch обслуживается|
|B19 durable crash|crash after PREPARED and after OS send|оба восстанавливаются MAY_HAVE_EXECUTED, без silent nonidempotent retry|
|B20 auth vsfreshness|old authentic snapshot currentνnew|старый ticket отклонён; old knowledge freshness not certified|
|B21 reference expiry|payload slot reused with new generation|old Mrefunavailable,not a new record by accident|
|B22 IPW|N2,π(.25,.75),b2|p(7/16,15/16), fixed-loss IPW expectation equals mean|
|B23 adaptive holdout|all-zero + single-bit label queries|can reconstruct labels;alpha spending alone FAIL|
|B24 repair|c3: authentic4, но current max7|expanddamagedset/recompute7;neverpreserve4as current correct|
|B25 energy denominator|issued tasks10,verified success0,totalJ3|utilitysuccess0;energy/success=+∞ по конвенции|
|B26 math counts old/new|M01…M44|все44IDs/claims сохранены;false universal claims remain FAIL|

Численные сравнения: logical ids/statuses/grammar limits совпадают точно. Вещественные primitives сравниваются сFP64 reference по выведенному forward-error bound для dtype/accumulator и объявленной libm error. Для tanh approximation нужен max-error bound на ограниченном входном диапазоне. Tolerance фиксируется до проверки; произвольный1e-3 без conditioning analysis недопустим. Stochastic parity использует тот же PRNG seed/counter и categorical inverse-CDF rule из07; иначе воспроизводимость только распределительная, не побитовая.

## 4. Traceability: требование → математика → данные → артефакт → gate

|Requirement|Equations/tensors|Data|Artifact|Gate/oracle|
|---|---|---|---|---|
|Unified multimodal state|S1,S4,S5,Eτ,F|RUtext/audio/UI/sensorsequences|architecture+tensor+Dsp|B01,B07–10,12strata|
|Conditional compute|S6,W_M,w_halt,w_wake|quality/costoraclecatalog|schedule/training manifest|B17,resource/coveragebounds|
|Action/outcome|S7,W_a,W_p,W_R,P|demonstrations+complete attempts/readbacks|schema/trace/evidenceABI|B05,B06,B11–13|
|Memory/goals|S4,Wqkv/r,U_g,P1|write-querypairs+DSLintentlabels|M/Q/Pstateformats|B04,B21,retention test|
|Authority/STOP|S2,S3,gatephases|faultinjection/nativeAPIbehavior|controller capability manifest|B02,B03,B19,B20|
|Resources|R5,R6,L6,L7|A52primitive/thermal/power|costtables/PSS/training budget|devicefull-pathgate|
|Regeneration|T8,c2/c3|independent records/certificates|repaircontract/test fixtures|B24|
|NCR-EVOvalue|E3–E6,φ99|independent evaluator A/B/C/D|labmanifest+results|B22,B23,equal-costCI|
|Commercialoffline|D09/D10|license/SBOM/API/networkevidence|signed local build/evidencebundle|manualownerrelease|

Отсутствующий вход нельзя заменять догадкой об архитектуре: результат BLOCKED с символом и методом12. Изменение предпосылки требует новой версии и повторного review. Более быстрый kernel допустим лишь при сохранении shape/numeric/skip/capability contracts и повторной калибровке стоимости.
