# ASTRA 06 — завершённая модель лабораторного NCR-EVO

Полный оригинальный brief (21 841 bytes, SHA25660bb31db6c663b4c78ea3182c1593b94ceb2b3259f690edc6ccc1792b28c6547) прочитан. Исторический потребитель Jarvis заменён в текущем задании на UNO; Jarvis не изменяется. Ниже реальное проектирование эволюции алгоритмов, но примеры вручную, не журнал запущенного поиска.

## 1. Архитектура и типы

Лабораторное состояние Z_n=(G_const,g_n,A_n,φ_n,θ_n,D_n,B_n,RNG_n). G_const — grammar typing, reference oracle, capability policy, resource caps и promotion gate; они immutable. g_n — mutable structural algorithm description. Θ — neural weights UNO, θ — mutator (может отсутствовать), φ — cheap selector; три разных пространства. Runtime APK не имеет доступа к executable archive и не запускает лабораторию постоянно.

Минимальный обоснованный состав: typed grammar-guided mutation+малый QD archive+независимый evaluator; surrogate добавляется как проверяемая абляция, не обязательная истина. GP даёт structural mutation; QD сохраняет ниши/ступени; active sampling распределяет expensive budget; multi-fidelity отсекает очевидные дефекты. Отдельный Bayesian optimizer/large LLM не нужен для определения метода. Biological regeneration — метафора восстановления функции по достаточному reference, не источник новых фактов.

Candidate c=(canonicalAST,hash,parents≤2,grammarVersion,resourceCertificate). Pure bounded DSL: Bool,Int32 с checked arithmetic,Enum,Option<Record>,fixed arrays; expressions literals/fields/equality/less/and/or/maxTuple; statements bounded FOR over input length≤Nmax, IF, ASSIGN array[i], FOLD, FILTER, MAP; вызовы только immutable total primitives. AST≤1024nodes,depth≤32, loops bounds≤4096; no recursion, dynamic allocation, filesystem,network,Android API,native/eval. Resource type system считает worst-case steps multiplicatively для nested loops, memory как maximum live fixed arrays; overflow arithmetic→INVALID_OUTPUT. H=1 требует parser,type,capability,resource checks; H=0 не исполняется. Termination следует из bounded loops, correctness нет.

Mutation distribution: .35 replace compatible subtree, .25 loop interchange/fusion/indexed-fold transformation, .20 typed recombination ≤2parents, .10 insert/delete bounded guard, .10 literal/enum change; impossible edit→INVALID_CANDIDATE with cost charged. Это heuristic M без θ. θ-trained mode отдельный будущий experiment, все training/teacher costs учитываются. Внутренний DSL исполнится только в resource-limited interpreter/process без production credentials. Sandbox failure→STOP entire run, не negative fitness и продолжение.

## 2. State transition, surrogate и известные вероятности

В поколении порождается Nraw≤256 candidates, deduplicate canonical hashes, hard filter →pool P sizeN. ParentSelect: uniform по occupied cells, затем uniform elite/step entries; failures не родители. Empty archive starts from immutable c0. Цена H и invalid attempts входит budget.

Фиксированный x(c)∈[-1,1]^32:1nodes,2depth,3loops,4maxloopbound,5nestedloops,6IFcount,7arraywrites,8arrayreads,9comparisons,10maxTuple,11validfilter,12keyrangeguard,13overflowguard,14unknownbranch,15map,16fold,17filter,18indexedstate,19repairmask,20constantcount,21workspacebound,22stepbound,23inputpasses,24outputpasses,25parentcount,26editdistance,27generationage,28parentdevquality,29parentdevcost,30staticnovelty,31celloccupancy,32fidelityavailability. Counts divided by declared caps/clipped; no hidden-test result in features. Bounded categorical features use fixed0/1; intercept appended x̃=(x,1)∈R33.

S_φ has three heads: p_correct=σ(w_cᵀx̃), Δquality=w_qᵀx̃, cost_capped=clip(w_costᵀx̃,0,Cdeepmax). Trainable99scalars. Regularized logistic/ridge with λφ=.01, bounded50gradient steps/generation, ηφ≤.01 candidate; no claim convex optimizer reaches optimum in50. Uncertainty u=clip(σ_res√(x̃ᵀ(λI+Σw_i x̃_ix̃_iᵀ)^−1x̃),0,1) for quality plus calibration error; covariance33×33 and residual state explicitly stored, not extra neural brain. This is model-dependent heuristic uncertainty; wrong linear model invalidates coverage interpretation.

Acquisition all components normalized train/dev-only:

\[
A_i=α\max(\widehat{Δq_i}-δ_q,0)+βu_i+γnov_i+δrare_i-λ\widehat c_i,
\quad (α,β,γ,δ,λ)=(1,1,.5,.5,.5).
\tag{E3}
\]

Novelty=minimum normalized structural feature distance to archive; **not measured behavioral novelty** until E. Rare_i=1/(1+celloccupancy predicted by static descriptor). Descriptor initially uses structural family×workspaceclass×devrobustness, 4×4×4=64cells; robustness bin only afterdevmeasurement. Before E use unknown bin/estimatedprior foracquisition, never manufacture archive coverage.

Sample b≤16 iid draws with replacement:

\[
π_i=ε/N+(1-ε)softmax(A_i/T),\quad ε=.1,T=1,\quad p_i=1-(1-π_i)^b.
\tag{E4}
\]

Evaluate distinct selected programs once. Reserve b Cdeepmax **before** draws; do not stop midway on favorable results. If budget insufficient reduce b before sampling; fixed b is part of propensity log. Emptypool→no evaluation. p_i>0; minimum inclusion≥1−(1−ε/N)^b. Discreteness/hashduplicates don't change this finite-pool conditional formula.

For fixed φ lossℓ_i with all specified labels observed, \\(\hat R=N^{-1}\sum I_iℓ_i(φ)/p_i\\) unbiased: E[I_i]=p_i, linearity; no need pairwise independentI. For fixed k useful programs and independent pool proposals, expected evaluated useful distinct=Σ p_iθ_i, but diverse successes not this sum when outputs equivalent. If uncertainty/cost used to early-abort beyond budget protocol, p_i must be recomputed; cannot keep E4.

Selection correction **does not repair missing labels**. E publishes tuple(correct_within_fuel,quality_if_completed,spent_cost,timeout,crash,energy_available,descriptor,fidelity). Timeout has observable within-fuel failure, but unknown completed quality. Train correctness_within_fuel/capped_spent_cost with IPW, quality only completed with censor flag; no unbiased full quality risk claimed without missingness model. Separate uniform audit/calibration pool (10%generation evaluation budget) samples candidates independently; its cost included, labels never promotion holdout. Reliability bins +Brier measurep_correct; residual interval calibration only under stated exchangeability, adaptive generation shift requires recalibration and coverage report.

Boundary-only failure: regionX has correctp=.5 but usefulquality0; regionYp=.99 and usefulpositive. SelectingonlyX improvesclassificationentropy but discoversno usefulalgorithm. Likewise surrogate confidently wrong onY can decreaseyield; explorationensuresnonzeroprobability but notpracticaldiscovery. If usefulitem probabilityπ≥ε/N, afterb independent draws detection≥1−(1−ε/N)^b, tinyforlargeN. No10^6 speedup theorem.

## 3. Multi-fidelity without false promotion

L0 parse/type/resource H; L1 exhaustive small-domain reference+stress/fuel; L2 larger independent devtask distributions with host timing/memory; L3 separately authorized device benchmark of limited mature candidates. Low fidelity never proves highfidelity quality/energy. Each E reports whichinputs/fidelityran; equality of outputonL1doesnotproveL2. L1mayfilteronly violated **hard** counterexample (correct rejection); when filteringheuristic lowscore, failedtestcoverage retained andriskofdiscardinggoodL2reported. No IPW extrapolation across fidelities without nonzero highfidelity sampling and correct conditional inclusion probabilities.

Reference/oracle process cannot read model predictions as labels. Devtestresults may guidefuturemutations; finalholdout mustremaininaccessible untilfinalist/artifacthashfrozen. Generator output isnever loadedasnativecodeincontroller. The lab’s immutable validator and OS permission gate are notmutationspaces.

## 4. Bounded archive and full cycle

64cells×(2elites+1step+1failure)=256entries; AST≤64KiBcanonicalserialized, metadata≤4KiB each; activearchive≤17MiB. Evidence/taskpayload store≤256MiB, diagnostics≤64MiB, ancestry index≤4096nodes×128bytes=.5MiB. Total explicitdisk≤337.5MiB plus immutable taskdata/toolchain; onquota exhaustion stop or documentedeviction, neverclaimfullhistorypreserved. Storehashesofevictedancestorswithtombstones, notunboundedparentgraphs.

Elite: hard-valid candidates with measured dev result; Paretoquality↑,robustness↑,cost↓; if>2keepmaxquality andmincost, tieshash. Step: greatest structuralnovelty nonelite, tieshash, lifetime≤8generations; fails correctnessallowed onlystep andneverpromotion. Failure: earliest reproducible distinctfailure signature percell, replacedonlynewfixturewithpriority by severity/hash. This is an approximation, not allParetofront or guarantee savefutureusefulstep.

Full specification pseudocode (не executable implementation):

1. Freeze generation config, remaining vectorbudget, RNG, archive/surrogate versions.
2. Reserve mutations/static/features/fit/IO+worst-case bdeep+calibration costs; ifnone fit→STOP_BUDGET.
3. Produce bounded typed candidates, account allattempts, dedup, H-filter.
4. Compute x,S,acquisition, E4 draws; freeze selectedhashes andpropensities.
5. Capability-free evaluator runs bounded fidelities; timeouts/censoring explicit.
6. Commit result/evidence/cost before updating archive; failed durablecommit→STOP, no ghostsuccess.
7. Deterministic QD update; fitφ using onlypermitted devlabels; independent uniformcalibration.
8. At preregistered checkpoint freeze finalist set; independent finaltestonce onfresh tasks.
9. Export reviewable artifacts; no deployment/commit/permission changes. All updates toθ separatefrozenexperiment.

Everygenerationdecreasesnonnegative fuel/time reservation or consumesoneofmax128generations; allinnerloopsbounded. This proveslogicalterminationundertrustedinterpreter/progress, notsuccess. Promotion requires independent formal review+hostparity+fullUNOquality/norm/resources+devicePASS+ownerapproval; yields newmanifest/v/ν. Mutation cannotchangeG_const undercapabilityisolation induction; thisassumption fails witharbitrarynativecodeinprivilegedprocess.

## 5. Три поколения структурной регенерации — проверяемая трасса

Контракт: input records r_i=(key,seq,value,valid), key∈{0,…,m−1}, n≤4096,m≤256. valid determinedbyimmutablevalidator;seqInt32, tieindexi. For eachkey output valueofvalidrecord withmax(seq,i), elseUNKNOWN. Logicalvalue не claimphysicalworld.

|Поколение|AST-структура|Материальная мутация и факт|
|---|---|---|
|G0 c0|FORkey: FOLDrecords(filterkey∧valid,maxTuple)|O(mn+m), exactdefinition; immutablebaseline|
|G1 c1|INIToutput; FORrecord IFvalid THENoutput[key]=value|замена nestedscan на indexedfold; O(n+m), **ошибка** если seq не ordered|
|G1 c1b|INITbest; FORrecord IFtuple>best THENassign|сохранил max, потерял validguard; corruptedrecord можетпобедить|
|G2 c2|INITbestUNKNOWN; FORrecord IFinrange∧valid∧(UNKNOWN∨tuple>best) THENassign|рекомбинация indexedfold+valid+max; O(n+m), correctnessproofbelow|
|G3 c3|constructDfromdamaged∨missingcurrentcertificate; foldc2onlyD; mergecertifiedintact|realrepairbranch; equalitycontractdependsonthe**same**recordsdigest,validatorversion,targetepoch|

Trace fixture keys0,1:

- A=[(0,1,4,T),(0,2,7,T),(1,1,3,T)]→[7,3]. c0,c1,c1b,c2correct.
- B=[(0,2,7,T),(0,1,4,T)]→[7,UNKNOWN]. c1wrong4; c2correct.
- C=[(0,1,4,T),(0,9,99,F)]→[4,UNKNOWN]. c1bwrong99; c2correct.
- D=[(0,2,5,T),(0,2,6,T)]→[6,UNKNOWN] viaindex-tie.
- E: intactauthenticated4/seq1, Dinitialempty, currentrecordscontainseq2/value7. c3 **must** enlargeD; authenticationonly giveswrong4.

c2 induction: afteriiterationsbest[key]=maxvalidtupleamongprefix1…i; baseUNKNOWN; invaliddoesnotchangecandidates; validnewrecord updatesmaxiflarger. At i=n fullcontract, includingduplicates/equal seq/outofrange rejection. c3 proof: onD c2; oncomplement certificateasserts sameF(records) value, so unioncorrect. Ifrawreferenceinsufficient→UNKNOWN; algorithmdoesnotinventlostvalues. DenseoutputhasΩ(m)writecosteven|D|small; sparsepatchinterfacewouldbeanotherABI.

Cheapfeaturechanges: c0nestedloops1,indexed0; c1nested0,indexed1,max0; c1bvalid0,max1; c2valid1,max1; c3repairmask1. ManuallabelsB,Cexposecomplementaryerrors, enablingstatedrecombination. No numeric surrogate predictions fabricated. Archiveretainsc0baseline,c2efficientelite,c1stepwithinquota,failurefixtureB; afterexpiryc1canbeevicted. n1000,m128: c0 128000keytests+counters, c2 1000recordvisits+≤1000tuplecompares+128init; notclaimed128×walltimeandnotproofsearchwilldiscoverc2.

## 6. Экономика и пределы ускорения

\[
C_{total}=\sum_{1}^{Nraw}(C_{mut}+C_H+C_{feat}+C_S)+\sum_{i\in selected}C_{deep,i}
+\sum_{1}^{Jdevice}C_{device}+C_{fit}+C_{QD}+C_{oracle}+C_{sandbox}+C_{IO}.
\tag{E5}
\]

VectorCPU-seconds,joules,disk,peakRAM; costsfromdifferentmachinesnotblindlyaddedwithoutdeclaredcurrency/energyconversion. Forfixedpool fullcost=Na+ND, selectedcost=Na+KD+F+O; grosssaved=(N−K)D−F−O. Positiveeconomiccostsavingiff(N−K)D>F+O; **usefulyield** stilldependsmissedsolutions. WithNa1000,D1000,N1000,K50,F+O20000 units: full1,001,000,selected71,000,ratio14.10; ifF+O1,000,000selected1,051,000 worse. These hypotheticalunitsnotmeasurements.

Absoluteideal uppercostspeedup≤(Na+ND)/(Na+K Dmin) ifF,O≥0 andselecteddeepcost≥Dmin; noqualityguarantee, noarbitraryuniversal lowerbound. Actualnetvalue=
useful_new_independent_results/Ctotal; duplicates/semantic-equivalentprogramsdon'tcounttwice. Includeport/review/deviceintegrationcostandamortizationhorizonH beforeclaimingbenefittoUNO. NCRsearchisnotchargedaszerobecauseoff-device.

## 7. Equal-cost falsification and valid statistics

A randommutations+singleelite; B samegrammar+MAP-Elites; C B+trainedsurrogate+E4; D1 C frozenφ; D2 C nonovelty; optionalD3 C noQD. Same taskfamilies, evaluator, mutationbudget accounting, **equal total resource cap**, seedpairedinitialconditions. Kdiffersnaturally; do notgiveCfreefit. Freeze primaryutility (U=\min(Kout,N_{independentlyUsefulDistinct})/Kout\), Kout=16≤archivecap; correctness+minimumqualityimprovementδq=.01+costfeasibility defineusefulonindependenttest. Distinctness usescanonicalalgorithmfamily/referencebehaviorequivalenceondeclaredfinitebattery, notgeneralprogram-equivalenceoracle.

Eachindependenttask-family/seedbundle gives D_i=U_C−U_AorB∈[-1,1]. Ifseedswithinsharedtaskfamilydependent, clustermeanistheunit. PrimaryclaimC>AANDC>B. Forα_each=.025,β_each=.1, Δ=.05 vsnullδ=0:

\[
LCB=\bar D-\sqrt{2\log(1/α)/n},\quad
n≥\frac{2(\sqrt{\log(1/α)}+\sqrt{\log(1/β)})²}{(Δ-δ)²}=9456.275\ldots,
\tag{E6}
\]

thus9457pairedindependentunitsgiveconservativedistribution-freejointpower≥.8byunionbound. Not9457mutations; costcanmakethisdesigninfeasible. Pilot30independentfamiliesestimatesvariance/costbutdoesnotproveΔ; preregistersmallerparametric/bootstrapdesignonlywithjustifiedassumptions,orreportINCONCLUSIVEwhenbudgetinsufficient. Cannotchooseatestafterseeingadvantage.

Fresh finalholdoutperadaptivefinalist; spendingα_j=.05/[j(j+1)] controlsfamilyerroronlywithconditionalvalidtestsandfreshdata. Reusingrevealedlabels/scorescanreconstructholdout (allzero+singlebitqueries), soalpha-spendingaloneinvalid. Calibration/devnotpromotionholdout.

Falsification: ifUCB(Δ)≤δ_practical=.02 atfixedcap, rejectworthwhileadvantageonthatdomain; ifLCB>δ_practical forbothA/Bandallhardgatespass, supportsboundedclaim; intervalcrossing→INCONCLUSIVE. Trustviolation/oracleexploit→immediateSTOP; costcap→stop; noimprovementat3preregisteredcheckpointsusesfreshheldout+spentalphaorfutilitydevonly (finalclaimunchanged). Outcomesmustreportallgroups,coverage,crashes,censoring,fitenergyandnegative results. NoactualNCRexperimentruninthiswork.
