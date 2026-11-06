# ASTRA 08 — доказательства, контрпримеры и найденные исправимые дефекты

Это авторский математический проход. Независимые blind/crosscheck/final reports находятся в audit/ и ASTRA_10. Доказательство в идеальной модели не является выполненной проверкой Android или обученной модели.

## Т 1. Измеримость, тотальность и конечное обслуживание

Область: bounded finite records, fixed model manifest, finite queues, external measurable race kernel с ближайшим таймером; trusted APIs возвращают typed result или protocol timeout. Каждый parser либо создаёт допустимый sum-type, либо INVALID; каждый phase/tag имеет producer/transition/default; allocation предшествует проверка cap. Все linear maps имеют формы W2; softmaxempty→abstain/zero read, NaN→invalid, normalizers positive. Finite composition/branching этих измеримых функций даёт measurableδ; pushforward probability kernel даёт вероятность 1. Протокольная конечность при scheduler progress следует из bounded ranks+deadlines (01). **Не следует** физическое завершение OS effects и hard wall-time.

Контрпример B1 clock: queued deadline atτ+1, произвольный K_ext возвращаетΔ10, action-completionatτ+2. Система может ошибочно обработать completion до deadline илизаднимчисломперескочить timer. RaceconditionΔ≤d_R устраняетэтотразрыв. Наличие defaultINVALID самопосебенезадаёт producers и time.

## Т 2. Ограниченность и fixed-input contraction

База s,g∈cube, P rows≤pmax. tanh→cube; h0=ρs+(1−ρ)z и active update=(1−α)h+αF — выпуклые комбинации; inactive сохраняет boundedvalue. Индукция по k,t сохраняет h,s,g; sigmoidβ∈[0,1]; memorytanhfinite; rowprojection сохраняет P. Finiteprecision требует finitecheck+finalclip для roundoff, иначе idealbound самне codeproof.

Для fixed z каждаявествь имеет Lipschitz≤||B||∞||A||∞≤.9; averaging ветвей не увеличиваетмаксимум; wholeFγ≤.9. Fullstepc=1−α(1−γ)=.95. Banachfixedpointunique в completecube; error≤c^kE0. Sparsecommonmaskstepnonexpansive; есликаждый blockupdated за F_cov шагов, его error послеобновления≤cE_start исохраняетграницудоконца sweep; все blocks тогда≤cE_start. Это validfair-sweep proof, но B2K8sampling необеспечивает fairness.

Counterexamples: F=0,mask(1,0),h=(1,1)→(0,1)forever; residual h+tanh(−10h) имеет 2cycle±a,где 2a=tanh10a,a∈(0,.5). Existencebyintermediatevaluetheorem: derivativeat0positive, f(.5)<0. Thusclipbounded≠convergence. Changingz,mask,Θinvalidatesfixedinputtheorem. W4explicitlyshowseventLipschitz можетбыть>1. Globalenvironmentcanalternateforcedobservationsforever; fullagentconvergenceuniversallyfalse.

## Т 3. Ошибка квантования и finite precision

Nearestscalarroundingstep s gives|e|≤s/2, row-L1error≤ns/2. Inducednormtriangle gives decodednorm≤originalnorm+rowerror; productbound02. Matrix-vectoroutputerror≤rowerror·||x||∞. Nonlinear1-Lipschitz propagates; fullfixedmap noisyiterationE_{k+1}≤cE_k+ε →E_K≤c^KE0+ε(1−c^K)/(1−c). Для sparsecoverage F_covnoiseboundcE+F_covε. Argmax unchanged only iftopgap>2maxlogiterror. Sigmoid saturatingtwodifferentlogitsboth1.0demonstrateswhycomparelogitsnotprobabilities. Certifyingdecodednormdoesnotcertifysemanticquality.

## Т 4. Training derivatives and online convexity

L4followschainruleouterproducts; shapes [b,χb][χb,d]→[b,d]. TiedE gradientsaddbecauseparameteridentical. L5follows finite sum ∂ΣπL=Σπ∂L+ΣLπ∂logπ. Forhistory-baseline b independentofcurrentdecision, Σb∂π=b∂1=0. ItmustincludeΘthroughz/h, notonlyselectorweights. Scalarcounterexample z_θ=θ,B~Bernoulliσθ,L=B: pathwise∂L0but∂EL=σθ(1−σθ)>0. STEquantizationandTBPTTexplicitlynotexactfullgradient.

P2proof04: HessianPSD, spectralnorm≤.25+λ, projectedgradientdescentunderη≤1/L. Cauchyandprojectionnonexpansiongiveboundedinterference; summeddistanceinequalitygivesOGD P3. Noimplicationtolearningalltasks. Oppositelabelsamestatecontradictszeroforgetting. Action-conditionedh_a fixesmissingargsbutdoesnotguaranteefeatureinjectivityorcounterfactualidentification.

## Т 5. Ресурсные invariants

Ifbudget B≥0, beforeeachprimitivecertifiedcost c_i+reserve≤remaining, debitc_i, thenbyinductionΣc_i+reserve≤B. Everypathincludesselector/heads/IO/DSPasappropriateseparateunits. Finitequeuesgiveboundedallocatedstorage**ifallreferencedpayloadsalsocapped**. QuotasdonotprovequeuewaitorphysicalPSSwithoutallocator/OSbounds. TwoequalMACprogramscanmoveverydifferentbytesandhavearbitrarydifferentidlewait; thereforeMACdoesnotdeterminejoules. SparsemaskafterdensecomputehasnodenseMACsaving; B2requireskernelomission.

Resourcecounterexampletrain: d1024K8audio100fps→14.21GmatrixMAC/s, not138MMAC“per task”. Per-tokenfullvocab33.55MMAC additional. Omittingthe100framesmultiplierunderestimatesbytwoordersofmagnitude. Devicecoefficientsmustclosefeasibleconstraints.

## Т 6. Authority, replay, crashes

A_cap: mutableworkerhasnocapabilitywriteorprivilegeddispatch, G_constimmutable. AllmutabletransitionspreserveTexcepttypeduntrustedproposal; onlytrustedgatebranchcreatesOSrequestaftercurrentguards. InductionprovesnoauthorityescalationforarbitraryΘ/P. LinearizedSTOPbeforegatepreventsrequest; afterrequestcannotundophysicalsideeffect. Noassumptionoflearnedriskaccuracyneeded.

A_tx: usedticket+Pversion+receipt+Mrefatomic. A fresh uniqueν/e andmodel/goal/consent/digestchecksmeanoldreceiptneverreachesupdate; duplicateusedfailsguard. InP128 uniquenessconditionalonnoCSPRNGcollision, withexplicitbirthdaybound05. ExactA_genCOUNTERtheoremrequiresactualmonotonicanchor, notclaimedA52fact. DurablePREPAREDoutboxcoverscrashwindow: remoteeffectunknowncannotberetriednonidempotently. Noall-systemexactly-oncetheorem.

PR3constructivecounterexamplepreserved: snapshotepoch0serial0→proposal/ticket→STOPepoch1→restoreold0→sameproposalidentity→oldboundary_pendingticketcanlearn. Thisisread-sourcecounterexample, notnewexecutedtest. B2nonceoutsidemodelsnapshotandactive-onlyticketsfixthatlogicalclassunderassumptions. PlainSHA permitsreplace+recompute;authenticatedoldrecordpermitsrollbackunlessfreshnessanchor. Authentication≠correctnesscertificate.

## Т 7. Endpoint/censoring/causality

Consider100attempts:10successfulreadbacksvisible,90failedattemptsproduceunknown. Trainingonlyvisiblelabels estimatesPr(Y=1|R=1)=1, whileoverallphysicalsuccess=.1. Otherworldwith90unobservedsuccessesproducesidenticalobservedtrainingdataandphysicalsuccess1. ThusqYcannotidentifyall-attemptsuccesswithoutmissingnessassumption. B2learnsqR=.1andqY=1,product.1predictsverifiedTRUEfrequency, well-definedobservableevent. ForanyfeaturesH:Pr(R=1,Y=1|H)=Pr(R=1|H)Pr(Y=1|R=1,H), noMARassumptionneededforidentity. Learning/calibrationstillrequiresdata/positivity.

Receipt TRUEdoesnotidentifycausaldo-effect: humanandUNOmaybothsetvolume; identicalbefore/afterunder“UNOworked”and“humanworked”. Snapshotpredicateonlyattestsdefinedsampletime. Toattestcontinuousconditionforalltimeintervalneedscontinuousreliableobservation ormodelassumption; twoendpointsaloneinsufficient. AbsenceofreceiptneverlogicalFALSE.

## Т 8. Regeneration and finite information

FullerasuremapsdifferentfunctionsF0,F1tosameavailabledata. Anyrepairoutputcannotbeexactboth;randomizedcannotprobability1both. Finiteb-bitstatehas≤2^bhistories; morepairwisedistinguishablerequiredhistoriesproducecollision. Theseproveimpossibilityofuniversalarbitrarymemory/regeneration, notanyparticularminimalneuralparametercount. c2repaircontracthasprefix-maxinductiveproof06; c3addscurrent-contextcorrectnesspremise. Authenticstalevalue4whencurrentmax7isexplicitcounterexampletoweakintactpremise.

## Т 9. NCR-EVO statistics and costs

E4inclusionprobability:probabilityneverdrawi=(1−π_i)^b; p_i=1−that. E[I_iℓ_i/p_i]=ℓ_i forfixedφandobservedlabel. Adaptivefittedminimizer,clippedweights,censoredlabels,andcross-fidelityextrapolationdonotinheritunbiasedness. Uniformexplorationdoesnotguaranteevaluablemutationwithinfinitebudget.

E6fromHoeffdingrange2:Pr(mean−μ≤−r)≤exp(−nr²/2). Nullthresholdradiusαplusalternativetailradiusβ≤Δ−δ yieldsformula. Two comparisons requireα/βallocationforjointclaim; n8138only80%each, not80%joint;9457givesunionbound80%jointunderindependentunitswithineachcomparison. Sameholdoutadaptationinvalidatesconditionaltestvalidity;alphaspendingdoesnotrepairleakage. Costbreak-even(N−K)D>F+Onecessaryforeconomicsavinginfixedpool, notsufficientforusefulyield.

## Новые дефекты B1 и закрывающие изменения B2

|ID|Дефект / контрпример|Исправление и предел|
|---|---|---|
|C01|arbitrarytimeadvance skips alreadyduedeadline|race-kernel01; schedulerfairnessstillassumption|
|C02|predictionindexedverbuseshbeforeargs; twoargs differinsuccess|canonicalproposal re-encoding,freezeh_a;notinjectivityproof|
|C03|verified-onlysamplecanhave100%conditionalvs10%overall|q_Rnewhead,q_Yconditional;productonlyverifiedTRUE|
|C04|trainingcatalogzero/single/full differsruntimeTopK|onesampled prefixlawtrain/runtime;argmaxrequiresnewgate|
|C05|learnedmemoryqueryignoredcurrentinput|queryz0 afterinput projection,noextraweights|
|C06|TTS257outputfeeding80inputundefined,framingambiguous|fixedmel feedback,causalSTFT,GL/crop05|
|C07|clearingpendinglosesunresolvedphysicaldispatchrecord|durablePREPARED/reconciliation04/05|
|C08|hardware antirollbackassumedbutunavailableevidence|P128probabilisticprofile;exactCOUNTERnotclaimed|
|C09|goal/payload/index/FP32trace/copy-on-writeworkspaceomitted|explicitresourceledger;fullPSSstillrequiresbackend|
|C10|contractionofinnerFmisreadaslong-horizonagentproperty|W4,eventboundandcapacitycounterexample;H2/FNC2alternatives|
|C11|goalchildsemanticrefinementundefinedinNL|typedcapabilityenvelopevsfinalpredicate;humansemanticconfirmation|
|C12|allweightsobjectivewithoutmemory-writegradient|pairedwrite-queryunroll,detachboundariesandbiasdeclared|

Ни одна строка не оправдывает удаление исходных M14/M16/M18/M25/M27/M32/M36/M43 FAIL. Они ложные универсальные/исторические утверждения. M08 остаётся FAIL идентификации минимального достаточного размера. Завершение исправимой спецификации не делает эти утверждения истинными.
