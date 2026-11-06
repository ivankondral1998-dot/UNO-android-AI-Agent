# ASTRA 11 — точный будущий порядок реализации и оракулы

**Сейчас не исполнять.** Документ не разрешает новое ядро, production training, APK, CI, GitHub Actions, push/merge или изменение репозиториев. Он задаёт следующий этап после закрытия G0–G4 и явного разрешения владельца. В этой работе выполнялись только чтение, документирование и независимая арифметика.

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

Единый worker содержит общий F и Θ для всех modalities; controller и IO — системные границы, не автономные reasoning agents. Никаких BrainPort/Bridge/cloud dependencies добавлять нельзя.

## 2. Строгая последовательность стадий

1. **S0 / freeze requirements.** Принять конечный task battery/q/r/caps из 07 или документированно изменить до test. Получить права наданные и exactdevice SKU. Outputs: task_contract,dataset_rights,device_inventory. Gate: ни один обязательный функциональный класс не исключён молча.
2. **S1 / limited calibration.** После отдельного разрешения измерить shapes/DSP/IPC/storage primitives из 05 безорганизма и безпроизводственныхвесов. Inputs: cap/formulas; outputs: primitive_cost_table withintervals,peakPSS,thermal/isolation/readback viability. Gate: имеется хотябы одна вычислительно feasible full-function candidate; иначе формальный blocker «feasible set empty».
3. **S2 / constructor ABI.** Зафиксировать W2/alternative decision,tokenizeralgorithm,DSPnormalizationprocedure,serialization,toolchain hashes. Constructor обязан перечислитьвсе 198slow tensors для d1024B2,fastP отдельно. Gate: manifests cross-reconcile withPcount/MAC/storage; knownexampleoffsets roundtrip exactly.
4. **S3 / reference only after authorization.** Реализовать 01–04puremath primitives с mathematicaloracles ниже. No privileged APIs. Gate: exactlogic+FP64referenceconsistency; gradient checks awayfromnondifferentiableboundaries; everytensor hasnonzero relevant gradient on avalid labelledbatch (zero dueto mathematical symmetry investigated, notfake coverage).
5. **S4 / full new-weight training.** Run03T0–T4 withinapproveddata/hardwarecap; recordalltrialsandnegative results. Gate: train/dev finite, no leakage, learningcurves; lockedtestonceafterfinalfreeze. Smallclassification не заменяет 12strata07.
6. **S5 / export and host parity.** Actual decoded normcertificate, perprimitive FP32/FP16/INT8bounds, argmaxmargins, maskedskipinstrumentation. Gate: invariants plus qualitynoninferiorityonfreshtest; bytes matchABI. INT8failure→reproject/retrainorFP16iffeasible, nofakepass.
7. **S6 / trusted controller.** Boundary/replay/STOP/crash/faultinjection usingtestOSadaptersandthenA52. Gate: no unauthorizeddispatch/no stalelearn/logicalstatevalid; physicalexactly-once notclaimed. Workerattackmessages mustnotbypassgate.
8. **S7 / integrated Android.** End-to-end RUvoice/text/screen/plans/TTS/memory/P tasks,offline,heat/idle/processkill. Gate: allqualityandresources thresholds+licenses+securityreview; uncertaintyreported.
9. **S8 / separate NCR-EVO.** Run06 A/B/C/D matchedtotalcostonlyifauthorized; newcandidatepromotionreturnsS2/S5/S6/S7and independentreview, notautomaticrelease.
10. **S9 / owner release.** Review full evidence/SBOM/reproduciblelocalbuild/manualrollout. Sign/install onlyafterpermission; noGitHubActions.

## 3. Mathematical and engineering oracles

Исходные O1–O14 сохраняются в неизменённом корпусе `sources/02_ORIGINAL_WORK_V1_1/09_CODEX_IMPLEMENTATION_CONTRACT_LATER.md`. O4 относится к своим ε=.01,η=.2 и остаётся вернымfixture; defaultsB2ε1,η.01другие. Новые oracle не запускались, это точные specification tests.

|ID|Вход / процедура|Ожидаемый результат|
|---|---|---|
|B01 tensor sum|суммировать 198shape products d1024|55,451,639; Pfast131,072 отдельно|
|B02 causal clock|queueddeadlineτ+1,externalarrivaltimeτ+2|deadline обработан первым; afterdeadline receiptstale|
|B03 same timestamp|STOP,READBACK одинаковоеτ|STOPwins; P unchanged|
|B04 snapshot tick|COMPUTING usesMversion3,receiptcommitsM4beforetick2|tick2stillreads3; oldworkcookiecannotpublishaftergoalchange|
|B05 args trace|sameverb differentcanonicalargs|trace frozen **after** encodingeachargs; noassertionhnecessarilydifferent|
|B06 censoring|100eligibleattempts,10knownTRUE,90unknown|observabilitytarget10ones90zeros; outcome10ones,90masked; no90FALSElabels|
|B07 CTC order|path[a,blank,a] /[a,a]|aa /a respectively|
|B08 framecount|N=0,1,160,161,160000samples|NO_AUDIO;F1,1,2,1000|
|B09 TTS feedback|257magnitudes→fixedmeltransform|exact80values,W_audio inputdimension80|
|B10 normalizedOLA|waveform,STFT→ISTFTwithoutmagnitudealteration|reconstructvalidsupportwithin derivedFFTerror; crop/paddingexplicit|
|B11 P default|h=1,p=l0=0,y1,ε1,η.01,λ.001|q=.5,p′=.0025; rowcapnotactive|
|B12 no-label update|B11withUNKNOWN/STOP/replay|exactP unchanged|
|B13 P counterexample|h1,oldy0,newy1|newBCEdecreases,oldBCEincreases; neverzeroforgettingPASS|
|B14 norm export|decoded Arow-L1=1.02,B=.90|product.918; violatesγdeploy.9→reject even thoughFP32certificatepassed|
|B15 quant argmax|topgap≤2ε_l|no guaranteed parityclaim; report/measure disagreement|
|B16 cached recurrence|samez,Θ,mask; comparecachedCzvsuncached|sameidealmathematics; boundedfloatingdifference; MAC79,691,776atd1024K8|
|B17 sparse execution|q=nb/4|inactiveA/C/Bkernel invocationcount0, notjustzerofinaloutputs|
|B18 bounded queues|1024headers+newordinaryinput|BACKPRESSURE; STOP latchstillprocessed|
|B19 durable crash|crashafterPREPAREDandafterOSsend|bothrecoverMAY_HAVE_EXECUTEDwithoutsilentnonidempotentretry|
|B20 auth vsfreshness|oldauthentic snapshot currentνnew|oldticketrejected; oldknowledgefreshnessnotcertified|
|B21 reference expiry|payloadslotreusedwithnewgeneration|oldMrefunavailable,notnewrecordbyaccident|
|B22 IPW|N2,π(.25,.75),b2|p(7/16,15/16), fixedlossIPWexpectationequalsmean|
|B23 adaptiveholdout|allzero+singlebitlabelqueries|canreconstructlabels;alphaspendingaloneFAIL|
|B24 repair|c3authentic4butcurrentmax7|expanddamagedset/recompute7;neverpreserve4ascurrentcorrect|
|B25 energydenominator|issued10,verifiedsuccess0,totalJ3|utilitysuccess0;energy/success+∞convention|
|B26 math counts old/new|M01…M44|all44IDsandclaimsretained;falseuniversalsremainFAIL|

Numerical comparison: exactlogicalids/statuses/grammarcapserrorsmustmatchbitwise. Real primitives comparetoFP64reference usingforward-errorboundforselecteddtype/accumulatorplusdeclaredlibmerror. FP16 taylor/tanh approximationsrequiremeasured/certifiedmaxerror overboundedinputrange; tolerance chosenbeforetests. Do notuseuniform1e-3withoutconditioninganalysis. Stochasticselectorparity usesidenticalPRNG algorithm/seed andspecifiedcategoricalinverseCDFties; unlessrandomenginefrozenreproducibilityonlydistributional. PRNGexactalgorithmselectedinABIledgerbelow.

## 4. Traceability: требование → математика → данные → артефакт → gate

|Requirement|Equations/tensors|Data|Artifact|Gate/oracle|
|---|---|---|---|---|
|Unifiedmultimodalstate|S1,S4,S5,Eτ,F|RUtext/audio/UI/sensorsequences|architecture+tensor+Dsp|B01,B07–10,12strata|
|Conditionalcompute|S6,W_M,w_halt,w_wake|quality/costoraclecatalog|schedule/trainingmanifest|B17,resource/coveragebounds|
|Action/outcome|S7,W_a,W_p,W_R,P|demonstrations+completeattempts/readbacks|schema/trace/evidenceABI|B05,B06,B11–13|
|Memory/goals|S4,Wqkv/r,U_g,P1|write-querypairs+DSLintentlabels|M/Q/Pstateformats|B04,B21,retentiontest|
|Authority/STOP|S2,S3,gatephases|faultinjection/nativeAPIbehavior|controllercapabilitymanifest|B02,B03,B19,B20|
|Resources|R5,R6,L6,L7|A52primitive/thermal/power|costtables/PSS/trainingbudget|devicefull-pathgate|
|Regeneration|T8,c2/c3|independentrecords/certificates|repaircontract/testfixtures|B24|
|NCR-EVOvalue|E3–E6,φ99|independentevaluatorA/B/C/D|labmanifest+results|B22,B23,equal-costCI|
|Commercialoffline|D09/D10|license/SBOM/API/networkevidence|signedlocalbuild/evidencebundle|manualownerrelease|

No futuredeveloper may replace a missing datum by an architectural guess: missing input→BLOCKED with symbol/method12. Modifying a proven assumption triggersnewversion andrereview. Implementationmaychooseefficientkernels onlyifshape/numeric/skip/capabilitycontracts preserved andcostrecalibrated.
