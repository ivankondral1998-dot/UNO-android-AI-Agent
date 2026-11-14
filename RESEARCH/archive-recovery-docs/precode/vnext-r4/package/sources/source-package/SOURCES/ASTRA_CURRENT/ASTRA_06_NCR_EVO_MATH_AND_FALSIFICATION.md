# ASTRA 06 — завершённая модель лабораторного NCR-EVO

Полный оригинальный brief (21 841 bytes, SHA25660bb31db6c663b4c78ea3182c1593b94ceb2b3259f690edc6ccc1792b28c6547) прочитан. Исторический потребитель Jarvis заменён в текущем задании на UNO; Jarvis не изменяется. Ниже реальное проектирование эволюции алгоритмов, но примеры вручную, не журнал запущенного поиска.

## 1. Архитектура и типы

Лабораторное состояние Z_n=(G_const,g_n,A_n,φ_n,θ_n,D_n,B_n,RNG_n). G_const — grammar typing, reference oracle, capability policy, resource caps и promotion gate; они immutable. g_n — mutable structural algorithm description. Θ — neural weights UNO, θ — mutator (может отсутствовать), φ — cheap selector; три разных пространства. Runtime APK не имеет доступа к executable archive и не запускает лабораторию постоянно.

Минимальный обоснованный состав: typed grammar-guided mutation+малый QD archive+независимый evaluator; surrogate добавляется как проверяемая абляция, не обязательная истина. GP даёт structural mutation; QD сохраняет ниши/ступени; active sampling распределяет expensive budget; multi-fidelity отсекает очевидные дефекты. Отдельный Bayesian optimizer/large LLM не нужен для определения метода. Biological regeneration — метафора восстановления функции по достаточному reference, не источник новых фактов.

Candidate c=(canonicalAST,hash,parents≤2,grammar Version,resource Certificate). Pure bounded DSL: Bool,Int32 с checked arithmetic,Enum,Option<Record>,fixed arrays; expressions literals/fields/equality/less/and/or/max Tuple; statements bounded FOR over input length≤Nmax, IF, ASSIGN array[i], FOLD, FILTER, MAP; вызовы только immutable total primitives. AST≤1024nodes,depth≤32, loops bounds≤4096; no recursion, dynamic allocation, filesystem,network,Android API,native/eval. Resource type system считает worst-case steps multiplicatively для nested loops, memory как maximum live fixed arrays; overflow arithmetic→INVALID_OUTPUT. H=1 требует parser,type,capability,resource checks; H=0 не исполняется. Termination следует из bounded loops, correctness нет.

Mutation distribution: .35 replace compatible subtree, .25 loop interchange/fusion/indexed-fold transformation, .20 typed recombination ≤2parents, .10 insert/delete bounded guard, .10 literal/enum change; impossible edit→INVALID_CANDIDATE with cost charged. Это heuristic M без θ. θ-trained mode отдельный будущий experiment, все training/teacher costs учитываются. Внутренний DSL исполнится только в resource-limited interpreter/process без production credentials. Sandbox failure→STOP entire run, не negative fitness и продолжение.

## 2. State transition, surrogate и известные вероятности

В поколении порождается Nraw≤256 candidates, deduplicate canonical hashes, hard filter →pool P sizeN. Parent Select: uniform по occupied cells, затем uniform elite/step entries; failures не родители. Empty archive starts from immutable c0. Цена H и invalid attempts входит budget.

Фиксированный x(c)∈[-1,1]^32:1nodes,2depth,3loops,4max loop bound,5nestedloops,6IFcount,7arraywrites,8arrayreads,9comparisons,10max Tuple,11validfilter,12keyrangeguard,13overflowguard,14unknownbranch,15map,16fold,17filter,18indexed state,19repairmask,20constant count,21workspacebound,22stepbound,23inputpasses,24output passes,25parentcount,26editdistance,27generationage,28parentdevquality,29parentdevcost,30static novelty,31cell occupancy,32fidelity availability. Counts divided by declared caps/clipped; no hidden-test result in features. Bounded categorical features use fixed0/1; intercept appended x̃=(x,1)∈R33.

S_φ has three heads: p_correct=σ(w_cᵀx̃), Δquality=w_qᵀx̃, cost_capped=clip(w_costᵀx̃,0,Cdeepmax). Trainable99scalars. Regularized logistic/ridge with λφ=.01, bounded50gradient steps/generation, ηφ≤.01 candidate; no claim convex optimizer reaches optimum in50. Uncertainty u=clip(σ_res√(x̃ᵀ(λI+Σw_i x̃_ix̃_iᵀ)^−1x̃),0,1) for quality plus calibration error; covariance33×33 and residual state explicitly stored, not extra neural brain. This is model-dependent heuristic uncertainty; wrong linear model invalidates coverage interpretation.

Acquisition all components normalized train/dev-only:

\[
A_i=α\max(\widehat{Δq_i}-δ_q,0)+βu_i+γnov_i+δrare_i-λ\widehat c_i,
\quad (α,β,γ,δ,λ)=(1,1,.5,.5,.5).
\tag{E3}
\]

Novelty — минимальное нормированное расстояние структурных features доархива, не измеренная behavioral novelty. Rare_i=1/(1+occupancy предполагаемойячейки). После evaluation descriptor имеет 64 ячейки: family{nested-scan,indexed-fold,repair,other} × workspace{≤1KiB,≤64KiB,≤1MiB,≤16MiB} × dev robustness{[0,.5),[.5,.9),[.9,1),1}. До evaluation robustness неизвестна, используется prior только для acquisition; фактическое coverage не увеличивается. Hard evaluator cap:10^7 DSL instructions,16MiB workspace на candidate; timeout/censoring явны. Candidate с большим статическим bound отклоняется H.

Из feasible pool делаются b≤16IIDdraws с возвращением:

\[
π_i=ε/N+(1-ε)softmax(A_i/T),\quad ε=.1,T=1,\quad p_i=1-(1-π_i)^b.\tag{E4}
\]

Оценить уникальные выбранные программы один раз. До draws резервируется b Cdeepmax; нельзя остановить batch после выгодного результата и сохранитьстарые propensities. При недостаточном budget b уменьшается заранее. Empty pool→no evaluation. p_i≥1−(1−ε/N)^b>0.

Для fixedφ и наблюдаемых labels IPW risk Rhat=(1/N)ΣI_iℓ_i(φ)/p_i несмещён: E[I_i]=p_i и линейность ожидания. Независимость inclusion indicators между собой не нужна. Expected evaluated useful count=Σp_iθ_i для фиксированного пула; число новых достижений меньше, если результаты эквивалентны. Изменение sampling/early stopping требует пересчёта propensities.

Selection correction не восстанавливает missing labels. E возвращает correctness_within_fuel, completed_quality, spent_cost, timeout/crash, energy_available, descriptor, fidelity. Timeout даёт наблюдаемое нарушение контракта «выполнить влимите», но не известное unlimited quality. IPW обучает within-fuel correctness и capped spent cost; quality head использует только completed labels сявным censoring. Несмещённость дляполного uncensored quality не заявляется.

Отдельный uniform calibration pool получает 10%generation evaluation budget, с отдельными кандидатами/логами. Его labels не добавляются в estimator E4 и не являются promotion holdout. Если будущая версия объединит selections изодногопула, inclusion probability должна стать вероятностью объединения, а нестарым p_i. Brier/reliability оценивают correctness probability; predictive intervals требуют exchangeability, при adaptive distribution shift coverage проверяется заново.

Контрпример boundary-only selection: regionX имеет correctness≈.5, но useful quality0; regionY correctness≈.99 и полезные решения. Выбор только X может улучшить classifier и не найтиниодного полезного алгоритма. Exploration гарантирует лишь ненулевую вероятность: detection одного item после bdraws≥1−(1−ε/N)^b, чтооченьмало при largeN. Универсального ускорениянет.

## 3. Multi-fidelity и независимость evaluator

L0 — H/type/resources; L1 — exhaustive small-domain oracle и stress/fuel; L2 — большие независимые dev task distributions с host timing/memory; L3 — отдельно разрешённая device проверка немногих зрелых кандидатов. Каждый result указываетточный fidelity/inputset. Correctness на L1 не доказывает L2/Android. Hard counterexample позволяет отклонить candidate; heuristic low score может ошибочно отбросить хороший high-fidelity вариант, чтоотражаетсяв coverage.

Перенос IPW между fidelities требуетненулевой probability продвижения и правильных conditional propensities. Здесь такого extrapolationclaim нет. Dev результаты могутнаправлятьмутации; final holdout закрытдо freezefinalist/hash. Oracle не принимаетпредсказание candidate за label; validator,capabilitygate и reference не мутируют. Candidate nativecode не загружаетсяв privileged controller.

## 4. Ограниченный архив и полный цикл

64cells×(2elites+1step+1failure)=256entries. SerializedAST≤64KiB,metadata≤4KiB/entry: activearchive≤17MiB. Evidence≤256MiB,diagnostics≤64MiB,ancestry≤4096×128bytes=.5MiB. Explicit disk≤337.5MiB плюс immutabletasks/toolchain. Quotaexhaustion→stop либообъявленная eviction; бесконечнойистории нет. Tombstones для evictedparents входятвтотже ancestrycap.

Elite — hard-valid с measureddevresult. Pareto quality↑,robustness↑,cost↓; еслибольше 2, сохранить maxquality и mincost, tieshash. Еслиэтоодинкандидат, второй — следующийпо quality/cost/hash. Step — наиболее structurallynovel nonelite, lifetime≤8generations, correctness failure допустим только в этой квоте. Failure — воспроизводимый signature сприоритетом severity/hash. Это ограниченная аппроксимация frontier, не гарантия сохранения всех полезных ступеней.

Полныйпсевдокод спецификации, не executable implementation:

1. Заморозить generationconfig,budget,RNG,archive/surrogate versions.
2. Зарезервировать mutation/static/features/fit/IO, worst-case deep и calibration. Ничегоне помещается→STOP_BUDGET.
3. Породить boundedAST,учесть invalid attempts,deduplicate,H-filter.
4. Посчитать features/acquisition,E4draws; сохранить selected hashes/propensities.
5. Провести capability-freeevaluation; timeouts/censoring сохранитьявно.
6. Durablecommit evidence/cost доизмененияархива; commiterror→STOP.
7. Deterministic QD update; fitφтолькопоразрешённым devlabels; separate calibration.
8. На preregistered checkpoint заморозить finalists; независимый test на freshdata.
9. Экспортировать reviewableartifacts; no deployment/repochange/autopromotion. Изменениеθ — отдельный frozenexperiment.

Максимум 128generations; innerloops/fuelbounded. При trustedinterpreter/progress процессзаканчивается, успехне гарантируется. Promotion требует formalreview,hostparity,fullUNOquality/norm/resourcechecks,devicePASS и ownerapproval; результат newv/ν. При capabilityisolation mutabletransition не имеетпутизаписи G_const, поэтому индукция поколений сохраняет границу. Arbitrary nativecode в privileged process нарушаетпредпосылку.

## 5. Три поколения структурной регенерации

Контракт: records r_i=(key,seq,value,valid), n≤4096,m≤256. key вне[0,m) отклоняется; valid задаёт immutable validator. Длякаждогоключа вернуть value записи с max(seq,index) среди valid, иначе UNKNOWN. Это формальная задача алгоритма, не утверждение фактов физического мира.

|Generation|AST-структура|Изменение и вывод|
|---|---|---|
|G0,c0|FOR key: scan records; filter key/valid; max Tuple|O(mn+m), immutable correct baseline|
|G1,c1|initialize; one record loop; if valid assign output[key]|O(n+m), но теряет maxseq и ошибается при permutation|
|G1,c1b|one loop; compare tuple then assign|сохраняет max, теряет valid guard|
|G2,c2|initialize UNKNOWN; one loop; inrange AND valid AND greater Tuple→assign|структурная рекомбинация guard+indexed fold+max; O(n+m)|
|G3,c3|D=damaged OR no current certificate; c2 onD; merge certified complement|добавленреальный repairbranch; certificates привязанык same records digest/validator/epoch|

Ручные fixtures (не executedrun):

- A=[(0,1,4,T),(0,2,7,T),(1,1,3,T)]→[7,3]; все c0/c1/c1b/c2 правильны.
- B=[(0,2,7,T),(0,1,4,T)]→[7,UNKNOWN]; c1 ошибается ивозвращает 4.
- C=[(0,1,4,T),(0,9,99,F)]→[4,UNKNOWN]; c1b ошибается ивозвращает 99.
- D=[(0,2,5,T),(0,2,6,T)]→[6,UNKNOWN], tie по index.
- E: authenticintact4/seq1, current record7/seq2; c3 обязанрасширить D. Authenticityalone неподтверждаеттекущее 4.

Доказательство c2: после i итераций best[key]равен max валидногопрефикса 1…i. База UNKNOWN; invalid не меняетмножество, valid добавляетодин tuple иберёт max. При i=n полныйконтрактвыполнен. c3 на D корректенпо c2,надополнении—потекущему certificate. Если raw reference недостаточен, UNKNOWN. Denseoutput требуетΩ(m)writes дажеесли|D|мал; sparsepatch былбыдругим ABI.

Features c0→c1: nestedloops1→0,indexed0→1,max1→0; c1bvalid0; c2valid1/max1; c3repairmask1. Ручные labelsB/C даютдверазныерегрессии, исправленные рекомбинацией. Surrogate scores невыдуманы. Архивсодержит c0baseline,c2elite,c1step и Bfailure врамкахквот; c1 можетбыть evicted. При n1000,m128: c0 имеет 128000keytests, c2—1000recordvisits+≤1000tuple comparisons+128init. Это primitive counts, не 128×walltime speedup и не доказательство, чтопоискнайдёт c2.

## 6. Экономика и пределы ускорения

\[
C_{total}=\sum_{1}^{Nraw}(C_{mut}+C_H+C_{feat}+C_S)+\sum_{i\in selected}C_{deep,i}
+\sum_{1}^{Jdevice}C_{device}+C_{fit}+C_{QD}+C_{oracle}+C_{sandbox}+C_{IO}.\tag{E5}
\]

E5 применяется покомпонентно только к аддитивному вектору (CPU-seconds, joules, IO bytes). RAM и disk являются отдельными capacity constraints: peak=max по времени суммы одновременно живых allocations/files, а не суммой пиков последовательных evaluations. Costs разных машин сопоставляются с объявленной currency/energy conversion. Для fixedpool fullcost=Na+ND, selectedcost=Na+KD+F+O. Экономия положительна тогда и только тогда, когда(N−K)D>F+O; usefulyield всё ещё зависит от пропущенных решений.

Условныйпример: N1000,a1,D1000,K50,F+O20000→full1,001,000,selected71,000,ratio14.10. Если F+O1,000,000,selected1,051,000 — хуже baseline. Это hypothetical units, не измерения. Идеальный uppercost speedup≤(Na+ND)/(Na+K Dmin) при F,O≥0; quality lowerbound нет. Netvalue=independently Useful Distinct/Ctotal. Дополнительноучесть review/port/deviceintegration иамортизацию search назаданномчислезадач/устройств. Off-devicecost неравеннулю.

## 7. Equal-cost falsification и статистика

A=random mutation+singleelite; B=samegrammar+MAP-Elites; C=B+trained surrogate+E4; D1=C с frozenφ; D2=C без novelty; optionalD3=C без QD. Одинаковые taskfamilies,oracle,total resource cap и paired initial seeds. Число оценённых кандидатов может различаться; fit для C небесплатен.

Primaryutility U=min(Kout,N_useful_distinct)/Kout,Kout16. Одна independent unit — заранеефиксированный bundle16contracts/taskfamilies собщим budget. Useful achievement=(contract Id,quality/costtier), где candidate независимопрошёл correctness, улучшил quality≥.01 ивыполнил costcap. Эквивалентные outputs втойжет ier не даютвтороедостижение. Distinctness проверяется declared finite battery/tieroracle, не универсальным program-equivalenceverifier.

Для paired independent units D_i=U_C−U_AorB∈[-1,1]. Если seeds зависимывнутри taskfamily, independent unit—clustermean. PrimaryclaimC>AANDC>B. α_each=.025,β_each=.1,Δ=.05,nullδ0:

\[
LCB=\bar D-\sqrt{2\log(1/α)/n},\quad
n\ge\frac{2(\sqrt{\log(1/α)}+\sqrt{\log(1/β)})^2}{(Δ-δ)^2}=9456.275\ldots.\tag{E6}
\]

Для null δ=0 нужны9457 paired independent units для joint power≥.8. Нормативный practical gate ниже имеет δ=.02 и требует26268 таких units при true Δ=.05 и тех же α/β; это не число мутаций. Pilot30families оценивает variance/cost, недоказываетΔ. Меньший parametric/sequentialdesign требует предварительных обоснованных assumptions; если budget недостаточен, INCONCLUSIVE. Нельзяподбирать test после обнаружения выигрыша.

Для adaptivefinalist нужен fresh holdout. Alpha spendingα_j=.05/[j(j+1)]контролирует ошибку только при условно валидных tests/freshdata. All-zero+single-bitqueries раскрывают labels переиспользуемого holdout; alpha-spending самэтонелечит. Dev/calibration неявляются promotion holdout.

Falsification: UCB(Δ)≤δ_practical=.02 при fixedcap отвергает практически значимый выигрыш в этом domain. LCB>δ_practical дляобоих A/B и hardgates поддерживает ограниченный claim. Пересечение interval с threshold→INCONCLUSIVE. Trustviolation/oracleexploit→STOP; costcap→STOP. Трипредварительных futilitycheckpoints используют dev либо fresh heldout с alphaallocation. В report входятвсегруппы,coverage,crashes,censoring,fitcost и отрицательные результаты. NCRexperiment вэтойработенезапускался.

## Поправки независимого аудита R1: стоимость и practically significant power

E5 суммирует только **аддитивные** величины: CPU-seconds, joules и bytes written/read. RAM peak = max_t(sum of live concurrent allocations at t); disk peak = max_t(sum of live files at t). Их нельзя суммировать по последовательным evaluations. Wall time — makespan, а не сумма CPU-seconds при параллелизме. Archive/state allocations06 включаются в live totals, резервы evaluator проверяются до запуска. Cost break-even относится к одной объявленной аддитивной единице/валюте.

9457units вE6 — корректный bound для обнаружения **положительного**Δ=.05 противnullδ0. Финальный практическийgate требуетLCB>.02. Для80%jointpower этогоgate приtrueΔ=.05 нужно подставитьΔ−δ=.03: **n≥26268** paired independent units наcomparison. Число9457 не даёт обещанной мощности дляпорога.02. Pilot/sequential альтернативы не наследуютэтугарантиюбезсобственногодоказательства. Оба числа сохраняются сразнымиnull, а невыдаётсяудобное меньшеечислозапрактическийdesign.
